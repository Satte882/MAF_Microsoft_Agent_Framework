import importlib.metadata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maf_lab.config import Settings
from maf_lab.domain import (
    DecisionAction,
    EngineEvent,
    EngineOutcome,
    HumanDecision,
    InvoiceCaseCreate,
    RiskAssessment,
    RunRecord,
    RunStatus,
)

try:
    from agent_framework import (
        Agent,
        Executor,
        FileCheckpointStorage,
        Workflow,
        WorkflowBuilder,
        WorkflowContext,
        handler,
        response_handler,
    )
    from agent_framework.openai import OpenAIChatClient

    MAF_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only before dependencies are installed
    MAF_AVAILABLE = False
    Agent = Executor = FileCheckpointStorage = Workflow = WorkflowBuilder = WorkflowContext = object  # type: ignore
    OpenAIChatClient = object  # type: ignore

    def handler(function: Any) -> Any:
        return function

    def response_handler(function: Any) -> Any:
        return function


def maf_version() -> str | None:
    if not MAF_AVAILABLE:
        return None
    try:
        return importlib.metadata.version("agent-framework-core")
    except importlib.metadata.PackageNotFoundError:
        return None


class MAFUnavailableError(RuntimeError):
    pass


@dataclass
class CaseEnvelope:
    run_id: str
    customer_name: str
    invoice_number: str
    amount_eur: float
    days_overdue: int
    context: str
    risk_level: str
    risk_reasons: list[str]
    deterministic_action: str


@dataclass
class DraftRequest:
    case: CaseEnvelope
    revision_guidance: str = ""
    previous_draft: str = ""
    iteration: int = 0


@dataclass
class DraftArtifact:
    case: CaseEnvelope
    text: str
    iteration: int


@dataclass
class HumanReviewRequest:
    run_id: str
    prompt: str
    draft: str
    iteration: int
    customer_name: str
    invoice_number: str
    amount_eur: float
    days_overdue: int
    context: str
    risk_level: str
    risk_reasons: list[str]
    deterministic_action: str


@dataclass
class FinalArtifact:
    status: str
    text: str
    iteration: int


if MAF_AVAILABLE:

    class CaseIntakeExecutor(Executor):
        def __init__(self) -> None:
            super().__init__(id="case_intake")

        @handler
        async def prepare(self, case: CaseEnvelope, ctx: WorkflowContext[DraftRequest]) -> None:
            ctx.set_state("run_id", case.run_id)
            await ctx.send_message(DraftRequest(case=case), target_id="drafter")


    class DraftExecutor(Executor):
        def __init__(self, settings: Settings, chat_client: Any | None = None) -> None:
            super().__init__(id="drafter")
            client_args: dict[str, Any] = {
                "api_key": settings.openai_api_key,
                "model": settings.openai_model,
            }
            if settings.openai_base_url:
                client_args["base_url"] = settings.openai_base_url
            client = chat_client or OpenAIChatClient(**client_args)
            self._agent = Agent(
                client=client,
                name="PaymentFlowAdvisor",
                instructions=(
                    "You are a cautious B2B accounts-receivable advisor for German SMEs. "
                    "Produce a concise internal recommendation, not legal advice. Never claim that "
                    "a message was sent. Explicitly preserve human approval before external action."
                ),
            )

        @handler
        async def draft(self, request: DraftRequest, ctx: WorkflowContext[DraftArtifact]) -> None:
            case = request.case
            prompt = (
                "Create an internal next-step recommendation for this overdue invoice.\n"
                f"Customer: {case.customer_name}\n"
                f"Invoice: {case.invoice_number}\n"
                f"Amount EUR: {case.amount_eur:.2f}\n"
                f"Days overdue: {case.days_overdue}\n"
                f"Context: {case.context or 'none'}\n"
                f"Deterministic risk level: {case.risk_level}\n"
                f"Risk reasons: {', '.join(case.risk_reasons)}\n"
                f"Mandatory control: {case.deterministic_action}\n"
            )
            if request.previous_draft:
                prompt += (
                    "\nRevise the previous draft using the human guidance.\n"
                    f"Previous draft: {request.previous_draft}\n"
                    f"Human guidance: {request.revision_guidance}\n"
                )
            result = await self._agent.run(prompt)
            await ctx.send_message(
                DraftArtifact(case=case, text=result.text, iteration=request.iteration + 1),
                target_id="human_review",
            )


    class HumanReviewGateway(Executor):
        def __init__(self) -> None:
            super().__init__(id="human_review")
            self._last_iteration = 0

        @handler
        async def request_review(self, artifact: DraftArtifact, ctx: WorkflowContext) -> None:
            self._last_iteration = artifact.iteration
            case = artifact.case
            await ctx.request_info(
                request_data=HumanReviewRequest(
                    run_id=case.run_id,
                    prompt="Approve, revise or reject the proposed action.",
                    draft=artifact.text,
                    iteration=artifact.iteration,
                    customer_name=case.customer_name,
                    invoice_number=case.invoice_number,
                    amount_eur=case.amount_eur,
                    days_overdue=case.days_overdue,
                    context=case.context,
                    risk_level=case.risk_level,
                    risk_reasons=case.risk_reasons,
                    deterministic_action=case.deterministic_action,
                ),
                response_type=str,
            )

        @response_handler
        async def process_review(
            self,
            original_request: HumanReviewRequest,
            feedback: str,
            ctx: WorkflowContext[DraftRequest, FinalArtifact],
        ) -> None:
            action, _, guidance = feedback.partition("|")
            action = action.strip().lower()
            guidance = guidance.strip()

            if action == DecisionAction.APPROVE.value:
                await ctx.yield_output(
                    FinalArtifact(
                        status=RunStatus.COMPLETED.value,
                        text=original_request.draft,
                        iteration=original_request.iteration,
                    )
                )
                return

            if action == DecisionAction.REJECT.value:
                await ctx.yield_output(
                    FinalArtifact(
                        status=RunStatus.REJECTED.value,
                        text=guidance or "The human reviewer rejected the proposed action.",
                        iteration=original_request.iteration,
                    )
                )
                return

            case = CaseEnvelope(
                run_id=original_request.run_id,
                customer_name=original_request.customer_name,
                invoice_number=original_request.invoice_number,
                amount_eur=original_request.amount_eur,
                days_overdue=original_request.days_overdue,
                context=original_request.context,
                risk_level=original_request.risk_level,
                risk_reasons=original_request.risk_reasons,
                deterministic_action=original_request.deterministic_action,
            )
            await ctx.send_message(
                DraftRequest(
                    case=case,
                    revision_guidance=guidance or "Make the recommendation more precise.",
                    previous_draft=original_request.draft,
                    iteration=original_request.iteration,
                ),
                target_id="drafter",
            )

        async def on_checkpoint_save(self) -> dict[str, Any]:
            return {"last_iteration": self._last_iteration}

        async def on_checkpoint_restore(self, state: dict[str, Any]) -> None:
            self._last_iteration = int(state.get("last_iteration", 0))


def _build_workflow(
    settings: Settings,
    checkpoint_path: Path,
    run_id: str,
    chat_client: Any | None = None,
) -> tuple[Any, Any]:
    if not MAF_AVAILABLE:
        raise MAFUnavailableError("Microsoft Agent Framework is not installed.")
    if not settings.provider_configured:
        raise MAFUnavailableError(
            "Real MAF mode requires OPENAI_API_KEY and OPENAI_MODEL. Use demo mode without credentials."
        )

    storage = FileCheckpointStorage(
        storage_path=checkpoint_path,
        allowed_checkpoint_types=[
            "maf_lab.maf_engine:CaseEnvelope",
            "maf_lab.maf_engine:DraftRequest",
            "maf_lab.maf_engine:DraftArtifact",
            "maf_lab.maf_engine:HumanReviewRequest",
            "maf_lab.maf_engine:FinalArtifact",
        ],
    )
    intake = CaseIntakeExecutor()
    drafter = DraftExecutor(settings, chat_client=chat_client)
    reviewer = HumanReviewGateway()
    workflow = (
        WorkflowBuilder(
            name=f"invoice-review-{run_id}",
            description="Invoice recommendation with checkpointed human approval.",
            max_iterations=8,
            start_executor=intake,
            checkpoint_storage=storage,
            output_from=[reviewer],
        )
        .add_edge(intake, drafter)
        .add_edge(drafter, reviewer)
        .add_edge(reviewer, drafter)
        .build()
    )
    return workflow, storage


class MicrosoftAgentFrameworkEngine:
    def __init__(self, settings: Settings, chat_client: Any | None = None) -> None:
        self.settings = settings
        self.chat_client = chat_client

    async def start(
        self,
        run_id: str,
        case: InvoiceCaseCreate,
        assessment: RiskAssessment,
    ) -> EngineOutcome:
        checkpoint_path = self.settings.checkpoint_root / run_id
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        workflow, storage = _build_workflow(self.settings, checkpoint_path, run_id, chat_client=self.chat_client)
        envelope = CaseEnvelope(
            run_id=run_id,
            customer_name=case.customer_name,
            invoice_number=case.invoice_number,
            amount_eur=case.amount_eur,
            days_overdue=case.days_overdue,
            context=case.context,
            risk_level=assessment.level,
            risk_reasons=assessment.reasons,
            deterministic_action=assessment.deterministic_action,
        )
        events, request_id, recommendation, output, status = await self._collect(
            workflow.run(message=envelope, stream=True)
        )
        checkpoint_id = await self._latest_checkpoint_id(storage, workflow.name)
        return EngineOutcome(
            status=status,
            recommendation=recommendation,
            output=output,
            checkpoint_id=checkpoint_id,
            request_id=request_id,
            checkpoint_path=str(checkpoint_path),
            events=events,
        )

    async def resume(self, run: RunRecord, decision: HumanDecision) -> EngineOutcome:
        if not run.checkpoint_id:
            raise MAFUnavailableError("The run has no checkpoint to resume from.")
        checkpoint_path = self.settings.checkpoint_root / run.id
        workflow, storage = _build_workflow(self.settings, checkpoint_path, run.id, chat_client=self.chat_client)

        restore_events, restored_request_id, restored_draft, restored_output, restored_status = await self._collect(
            workflow.run(checkpoint_id=run.checkpoint_id, stream=True)
        )
        request_id = restored_request_id or run.request_id
        if not request_id:
            raise RuntimeError("Checkpoint was restored but no pending human request was found.")

        feedback = f"{decision.action.value}|{decision.guidance}"
        response_events, next_request_id, next_draft, output, status = await self._collect(
            workflow.run(stream=True, responses={request_id: feedback})
        )
        checkpoint_id = await self._latest_checkpoint_id(storage, workflow.name)
        recommendation = next_draft or restored_draft or run.recommendation
        return EngineOutcome(
            status=status if output or next_request_id else restored_status,
            recommendation=recommendation,
            output=output or restored_output,
            checkpoint_id=checkpoint_id,
            request_id=next_request_id,
            checkpoint_path=str(checkpoint_path),
            events=restore_events + response_events,
        )

    @staticmethod
    async def _latest_checkpoint_id(storage: Any, workflow_name: str) -> str | None:
        checkpoints = await storage.list_checkpoints(workflow_name=workflow_name)
        if not checkpoints:
            return None
        latest = sorted(checkpoints, key=lambda checkpoint: checkpoint.timestamp)[-1]
        return latest.checkpoint_id

    @staticmethod
    async def _collect(event_stream: Any) -> tuple[list[EngineEvent], str | None, str | None, str | None, RunStatus]:
        events: list[EngineEvent] = []
        request_id: str | None = None
        recommendation: str | None = None
        output: str | None = None
        status = RunStatus.RUNNING

        async for event in event_stream:
            event_type = str(getattr(event, "type", "unknown"))
            data = getattr(event, "data", None)
            source = str(getattr(event, "executor_id", None) or getattr(event, "source", None) or "maf_runtime")
            payload: dict[str, Any] = {}
            summary = event_type

            if event_type == "request_info":
                request_id = str(getattr(event, "request_id", "")) or None
                recommendation = getattr(data, "draft", None)
                status = RunStatus.AWAITING_HUMAN
                summary = "MAF emitted a persistent human-information request."
                payload = {"request_id": request_id, "iteration": getattr(data, "iteration", None)}
            elif event_type == "output":
                output = getattr(data, "text", None) or str(data)
                final_status = getattr(data, "status", RunStatus.COMPLETED.value)
                status = RunStatus(final_status)
                summary = "MAF emitted the final workflow output."
                payload = {"iteration": getattr(data, "iteration", None)}
            elif event_type == "status":
                summary = str(event)
            else:
                summary = f"MAF workflow event: {event_type}"

            events.append(
                EngineEvent(
                    phase="maf_runtime",
                    event_type=event_type,
                    source=source,
                    summary=summary,
                    payload=payload,
                )
            )

        return events, request_id, recommendation, output, status
