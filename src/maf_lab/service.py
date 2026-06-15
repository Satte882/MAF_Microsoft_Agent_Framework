from __future__ import annotations

import uuid

from maf_lab.config import Settings
from maf_lab.demo_engine import DemoWorkflowEngine
from maf_lab.domain import (
    ConceptCard,
    HumanDecision,
    InvoiceCaseCreate,
    RunDetail,
    RunMode,
    RunRecord,
    RunStatus,
    SystemInfo,
)
from maf_lab.maf_engine import (
    MAF_AVAILABLE,
    MAFUnavailableError,
    MicrosoftAgentFrameworkEngine,
    maf_version,
)
from maf_lab.policy import assess_risk
from maf_lab.repository import SQLiteRepository


CONCEPTS = [
    ConceptCard(
        id="executor",
        title="Executor",
        layer="Deterministic workflow",
        explanation="A typed processing step. Use it for rules, validation, routing and integration code that must behave predictably.",
        visible_in_platform="Intake, risk policy and human-review gateway appear as separate event sources.",
    ),
    ConceptCard(
        id="agent",
        title="Agent",
        layer="Model-driven reasoning",
        explanation="An agent uses a model for tasks that require interpretation or generation. It should not own irreversible business state.",
        visible_in_platform="Real MAF mode calls PaymentFlowAdvisor only for the recommendation draft.",
    ),
    ConceptCard(
        id="workflow",
        title="Workflow graph",
        layer="Orchestration",
        explanation="Edges define which typed messages may move between executors. The graph remains explicit even when an agent is involved.",
        visible_in_platform="CaseIntake → Drafter → HumanReview, with a revision loop back to Drafter.",
    ),
    ConceptCard(
        id="checkpoint",
        title="Checkpoint",
        layer="Durability",
        explanation="A checkpoint captures workflow state between supersteps so a new process can restore and continue a paused run.",
        visible_in_platform="Each pending human review records the checkpoint ID and storage location.",
    ),
    ConceptCard(
        id="hitl",
        title="Human-in-the-loop",
        layer="Control",
        explanation="request_info pauses execution and persists the unresolved decision. A later response resumes the graph.",
        visible_in_platform="Approve, revise and reject buttons send an explicit human response.",
    ),
    ConceptCard(
        id="event-log",
        title="Application event log",
        layer="Audit",
        explanation="Framework telemetry and business audit are different concerns. This lab stores an application event trail in SQLite.",
        visible_in_platform="The event timeline shows policy, model, checkpoint and human actions separately.",
    ),
]


class RunService:
    def __init__(self, settings: Settings, repository: SQLiteRepository) -> None:
        self.settings = settings
        self.repository = repository
        self.demo_engine = DemoWorkflowEngine()
        self.maf_engine = MicrosoftAgentFrameworkEngine(settings)

    async def create_run(self, case: InvoiceCaseCreate) -> RunDetail:
        run_id = str(uuid.uuid4())
        assessment = assess_risk(case)
        self.repository.create_run(run_id, case, assessment)
        self.repository.add_event(
            run_id,
            phase="application",
            event_type="run_created",
            source="RunService",
            summary="Neuer Lernlauf angelegt.",
            payload={"mode": case.mode.value},
        )
        self.repository.update_run(run_id, status=RunStatus.RUNNING)

        engine = self.maf_engine if case.mode is RunMode.MAF else self.demo_engine
        try:
            outcome = await engine.start(run_id, case, assessment)
            self._apply_outcome(run_id, outcome)
        except Exception as exc:
            self._record_failure(run_id, exc)
        return self.repository.get_run_detail(run_id)

    async def decide(self, run_id: str, decision: HumanDecision) -> RunDetail:
        run = self.repository.get_run(run_id)
        if run.status is not RunStatus.AWAITING_HUMAN:
            raise ValueError(f"Run {run_id} is not awaiting a human decision.")

        self.repository.add_event(
            run_id,
            phase="application",
            event_type="human_decision_received",
            source="RunService",
            summary=f"Menschliche Entscheidung '{decision.action.value}' empfangen.",
            payload=decision.model_dump(mode="json"),
        )
        self.repository.update_run(run_id, status=RunStatus.RUNNING)
        engine = self.maf_engine if run.mode is RunMode.MAF else self.demo_engine
        try:
            outcome = await engine.resume(run, decision)
            self._apply_outcome(run_id, outcome)
        except Exception as exc:
            self._record_failure(run_id, exc)
        return self.repository.get_run_detail(run_id)

    def list_runs(self) -> list[RunRecord]:
        return self.repository.list_runs()

    def get_run(self, run_id: str) -> RunDetail:
        return self.repository.get_run_detail(run_id)

    def concepts(self) -> list[ConceptCard]:
        return CONCEPTS

    def system_info(self) -> SystemInfo:
        return SystemInfo(
            application="MAF Learning Platform",
            version="0.1.0",
            maf_installed=MAF_AVAILABLE,
            maf_version=maf_version(),
            provider_configured=self.settings.provider_configured,
            provider_model=self.settings.openai_model,
            provider_base_url=self.settings.openai_base_url,
            database_path=str(self.settings.database_path.resolve()),
            checkpoint_root=str(self.settings.checkpoint_root.resolve()),
            supported_modes=[mode.value for mode in RunMode],
        )

    def _apply_outcome(self, run_id: str, outcome: object) -> None:
        fields = {
            "status": outcome.status,
            "recommendation": outcome.recommendation,
            "output": outcome.output,
            "checkpoint_id": outcome.checkpoint_id,
            "request_id": outcome.request_id,
            "error": None,
        }
        self.repository.update_run(run_id, **fields)
        for event in outcome.events:
            self.repository.add_event(
                run_id,
                phase=event.phase,
                event_type=event.event_type,
                source=event.source,
                summary=event.summary,
                payload=event.payload,
            )
        if outcome.checkpoint_id and outcome.checkpoint_path:
            self.repository.add_checkpoint(
                run_id,
                checkpoint_id=outcome.checkpoint_id,
                status=outcome.status.value,
                storage_path=outcome.checkpoint_path,
            )

    def _record_failure(self, run_id: str, exc: Exception) -> None:
        message = str(exc)
        category = "configuration" if isinstance(exc, MAFUnavailableError) else "runtime"
        self.repository.update_run(run_id, status=RunStatus.FAILED, error=message)
        self.repository.add_event(
            run_id,
            phase="error",
            event_type="run_failed",
            source=type(exc).__name__,
            summary=message,
            payload={"category": category},
        )
