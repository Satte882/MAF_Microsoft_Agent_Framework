from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from maf_lab.domain import (
    CheckpointSnapshot,
    InvoiceCaseCreate,
    RiskAssessment,
    RunDetail,
    RunMode,
    RunRecord,
    RunStatus,
    WorkflowEvent,
    utc_now_iso,
)


class SQLiteRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    invoice_number TEXT NOT NULL,
                    amount_eur REAL NOT NULL,
                    days_overdue INTEGER NOT NULL,
                    context TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_reasons_json TEXT NOT NULL,
                    deterministic_action TEXT NOT NULL,
                    recommendation TEXT,
                    output TEXT,
                    checkpoint_id TEXT,
                    request_id TEXT,
                    error TEXT
                );

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    storage_path TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id, id);
                CREATE INDEX IF NOT EXISTS idx_checkpoints_run_id ON checkpoints(run_id, id);
                """
            )

    def create_run(
        self,
        run_id: str,
        case: InvoiceCaseCreate,
        assessment: RiskAssessment,
    ) -> RunRecord:
        now = utc_now_iso()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO runs (
                    id, created_at, updated_at, mode, status, customer_name,
                    invoice_number, amount_eur, days_overdue, context,
                    risk_level, risk_reasons_json, deterministic_action
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    now,
                    now,
                    case.mode.value,
                    RunStatus.CREATED.value,
                    case.customer_name,
                    case.invoice_number,
                    case.amount_eur,
                    case.days_overdue,
                    case.context,
                    assessment.level,
                    json.dumps(assessment.reasons, ensure_ascii=False),
                    assessment.deterministic_action,
                ),
            )
        return self.get_run(run_id)

    def update_run(self, run_id: str, **fields: Any) -> RunRecord:
        allowed = {
            "status",
            "recommendation",
            "output",
            "checkpoint_id",
            "request_id",
            "error",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Unsupported run fields: {sorted(unknown)}")
        if not fields:
            return self.get_run(run_id)

        normalized: dict[str, Any] = {}
        for key, value in fields.items():
            normalized[key] = value.value if isinstance(value, (RunStatus, RunMode)) else value
        normalized["updated_at"] = utc_now_iso()

        assignments = ", ".join(f"{key} = ?" for key in normalized)
        values = list(normalized.values()) + [run_id]
        with self._connection() as connection:
            cursor = connection.execute(f"UPDATE runs SET {assignments} WHERE id = ?", values)
            if cursor.rowcount == 0:
                raise KeyError(run_id)
        return self.get_run(run_id)

    def add_event(
        self,
        run_id: str,
        phase: str,
        event_type: str,
        source: str,
        summary: str,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowEvent:
        now = utc_now_iso()
        payload = payload or {}
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO events (
                    run_id, created_at, phase, event_type, source, summary, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, now, phase, event_type, source, summary, json.dumps(payload, ensure_ascii=False)),
            )
            event_id = int(cursor.lastrowid)
        return WorkflowEvent(
            id=event_id,
            run_id=run_id,
            created_at=now,
            phase=phase,
            event_type=event_type,
            source=source,
            summary=summary,
            payload=payload,
        )

    def add_checkpoint(
        self,
        run_id: str,
        checkpoint_id: str,
        status: str,
        storage_path: str,
    ) -> CheckpointSnapshot:
        now = utc_now_iso()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO checkpoints (run_id, created_at, checkpoint_id, status, storage_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, now, checkpoint_id, status, storage_path),
            )
            checkpoint_row_id = int(cursor.lastrowid)
        return CheckpointSnapshot(
            id=checkpoint_row_id,
            run_id=run_id,
            created_at=now,
            checkpoint_id=checkpoint_id,
            status=status,
            storage_path=storage_path,
        )

    def get_run(self, run_id: str) -> RunRecord:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return self._row_to_run(row)

    def get_run_detail(self, run_id: str) -> RunDetail:
        run = self.get_run(run_id)
        with self._connection() as connection:
            event_rows = connection.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY id ASC", (run_id,)
            ).fetchall()
            checkpoint_rows = connection.execute(
                "SELECT * FROM checkpoints WHERE run_id = ? ORDER BY id ASC", (run_id,)
            ).fetchall()
        events = [
            WorkflowEvent(
                id=row["id"],
                run_id=row["run_id"],
                created_at=row["created_at"],
                phase=row["phase"],
                event_type=row["event_type"],
                source=row["source"],
                summary=row["summary"],
                payload=json.loads(row["payload_json"]),
            )
            for row in event_rows
        ]
        checkpoints = [
            CheckpointSnapshot(
                id=row["id"],
                run_id=row["run_id"],
                created_at=row["created_at"],
                checkpoint_id=row["checkpoint_id"],
                status=row["status"],
                storage_path=row["storage_path"],
            )
            for row in checkpoint_rows
        ]
        return RunDetail(**run.model_dump(), events=events, checkpoints=checkpoints)

    def list_runs(self, limit: int = 50) -> list[RunRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_run(row) for row in rows]

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            id=row["id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            mode=RunMode(row["mode"]),
            status=RunStatus(row["status"]),
            customer_name=row["customer_name"],
            invoice_number=row["invoice_number"],
            amount_eur=row["amount_eur"],
            days_overdue=row["days_overdue"],
            context=row["context"],
            risk_level=row["risk_level"],
            risk_reasons=json.loads(row["risk_reasons_json"]),
            deterministic_action=row["deterministic_action"],
            recommendation=row["recommendation"],
            output=row["output"],
            checkpoint_id=row["checkpoint_id"],
            request_id=row["request_id"],
            error=row["error"],
        )
