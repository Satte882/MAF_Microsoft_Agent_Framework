from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunMode(StrEnum):
    DEMO = "demo"
    MAF = "maf"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class DecisionAction(StrEnum):
    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"


class InvoiceCaseCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=120)
    invoice_number: str = Field(min_length=1, max_length=80)
    amount_eur: float = Field(gt=0, le=10_000_000)
    days_overdue: int = Field(ge=0, le=3650)
    context: str = Field(default="", max_length=2000)
    mode: RunMode = RunMode.DEMO

    @field_validator("customer_name", "invoice_number", "context")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return " ".join(value.split())


class HumanDecision(BaseModel):
    action: DecisionAction
    guidance: str = Field(default="", max_length=2000)

    @field_validator("guidance")
    @classmethod
    def strip_guidance(cls, value: str) -> str:
        return " ".join(value.split())


class RiskAssessment(BaseModel):
    level: str
    reasons: list[str]
    deterministic_action: str


class WorkflowEvent(BaseModel):
    id: int | None = None
    run_id: str
    created_at: str
    phase: str
    event_type: str
    source: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class CheckpointSnapshot(BaseModel):
    id: int | None = None
    run_id: str
    created_at: str
    checkpoint_id: str
    status: str
    storage_path: str


class RunRecord(BaseModel):
    id: str
    created_at: str
    updated_at: str
    mode: RunMode
    status: RunStatus
    customer_name: str
    invoice_number: str
    amount_eur: float
    days_overdue: int
    context: str
    risk_level: str
    risk_reasons: list[str] = Field(default_factory=list)
    deterministic_action: str
    recommendation: str | None = None
    output: str | None = None
    checkpoint_id: str | None = None
    request_id: str | None = None
    error: str | None = None


class RunDetail(RunRecord):
    events: list[WorkflowEvent] = Field(default_factory=list)
    checkpoints: list[CheckpointSnapshot] = Field(default_factory=list)


class EngineEvent(BaseModel):
    phase: str
    event_type: str
    source: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class EngineOutcome(BaseModel):
    status: RunStatus
    recommendation: str | None = None
    output: str | None = None
    checkpoint_id: str | None = None
    request_id: str | None = None
    checkpoint_path: str | None = None
    events: list[EngineEvent] = Field(default_factory=list)


class SystemInfo(BaseModel):
    application: str
    version: str
    maf_installed: bool
    maf_version: str | None
    provider_configured: bool
    provider_model: str
    provider_base_url: str | None
    database_path: str
    checkpoint_root: str
    supported_modes: list[str]


class ConceptCard(BaseModel):
    id: str
    title: str
    layer: str
    explanation: str
    visible_in_platform: str
