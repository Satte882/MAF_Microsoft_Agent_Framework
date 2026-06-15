from __future__ import annotations

import uuid

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


class DemoWorkflowEngine:
    """Deterministic simulator of the same lifecycle as the real MAF workflow.

    It deliberately mirrors executors, messages, checkpoints and human review so the
    UI remains usable without an API key. It is not presented as a real LLM run.
    """

    async def start(
        self,
        run_id: str,
        case: InvoiceCaseCreate,
        assessment: RiskAssessment,
    ) -> EngineOutcome:
        checkpoint_id = f"demo-cp-{uuid.uuid4()}"
        request_id = f"demo-request-{uuid.uuid4()}"
        recommendation = self._draft(case, assessment)
        return EngineOutcome(
            status=RunStatus.AWAITING_HUMAN,
            recommendation=recommendation,
            checkpoint_id=checkpoint_id,
            request_id=request_id,
            checkpoint_path=f"sqlite://runs/{run_id}",
            events=[
                EngineEvent(
                    phase="intake",
                    event_type="message",
                    source="CaseIntakeExecutor",
                    summary="Eingabedaten normalisiert und als typisierte Nachricht weitergegeben.",
                    payload={"invoice_number": case.invoice_number},
                ),
                EngineEvent(
                    phase="policy",
                    event_type="deterministic_decision",
                    source="RiskPolicy",
                    summary=f"Risikostufe {assessment.level} deterministisch ermittelt.",
                    payload=assessment.model_dump(),
                ),
                EngineEvent(
                    phase="draft",
                    event_type="simulated_agent_output",
                    source="DemoDraftExecutor",
                    summary="Deterministischer Lernentwurf erzeugt; kein Sprachmodell wurde aufgerufen.",
                    payload={"recommendation": recommendation},
                ),
                EngineEvent(
                    phase="review",
                    event_type="request_info",
                    source="HumanReviewGateway",
                    summary="Workflow wartet auf Freigabe, Überarbeitung oder Ablehnung.",
                    payload={"request_id": request_id},
                ),
                EngineEvent(
                    phase="checkpoint",
                    event_type="checkpoint_saved",
                    source="DemoCheckpointStore",
                    summary="Lern-Checkpoint für die spätere Fortsetzung gespeichert.",
                    payload={"checkpoint_id": checkpoint_id},
                ),
            ],
        )

    async def resume(self, run: RunRecord, decision: HumanDecision) -> EngineOutcome:
        if decision.action is DecisionAction.APPROVE:
            return EngineOutcome(
                status=RunStatus.COMPLETED,
                recommendation=run.recommendation,
                output=run.recommendation,
                events=[
                    EngineEvent(
                        phase="resume",
                        event_type="checkpoint_restored",
                        source="DemoCheckpointStore",
                        summary="Workflowzustand aus dem Lern-Checkpoint rekonstruiert.",
                        payload={"checkpoint_id": run.checkpoint_id},
                    ),
                    EngineEvent(
                        phase="review",
                        event_type="human_response",
                        source="HumanReviewGateway",
                        summary="Entwurf freigegeben.",
                        payload={"action": decision.action.value},
                    ),
                    EngineEvent(
                        phase="complete",
                        event_type="output",
                        source="HumanReviewGateway",
                        summary="Workflow abgeschlossen und Ergebnis veröffentlicht.",
                    ),
                ],
            )

        if decision.action is DecisionAction.REJECT:
            return EngineOutcome(
                status=RunStatus.REJECTED,
                recommendation=run.recommendation,
                output=decision.guidance or "Vorgang wurde abgelehnt.",
                events=[
                    EngineEvent(
                        phase="resume",
                        event_type="checkpoint_restored",
                        source="DemoCheckpointStore",
                        summary="Workflowzustand aus dem Lern-Checkpoint rekonstruiert.",
                        payload={"checkpoint_id": run.checkpoint_id},
                    ),
                    EngineEvent(
                        phase="review",
                        event_type="human_response",
                        source="HumanReviewGateway",
                        summary="Entwurf abgelehnt; Workflow kontrolliert beendet.",
                        payload={"guidance": decision.guidance},
                    ),
                ],
            )

        revised = (
            f"{run.recommendation}\n\nÜberarbeitungshinweis berücksichtigt: "
            f"{decision.guidance or 'Formulierung sachlicher und kürzer halten.'}"
        )
        checkpoint_id = f"demo-cp-{uuid.uuid4()}"
        request_id = f"demo-request-{uuid.uuid4()}"
        return EngineOutcome(
            status=RunStatus.AWAITING_HUMAN,
            recommendation=revised,
            checkpoint_id=checkpoint_id,
            request_id=request_id,
            checkpoint_path=f"sqlite://runs/{run.id}",
            events=[
                EngineEvent(
                    phase="resume",
                    event_type="checkpoint_restored",
                    source="DemoCheckpointStore",
                    summary="Workflowzustand aus dem Lern-Checkpoint rekonstruiert.",
                    payload={"checkpoint_id": run.checkpoint_id},
                ),
                EngineEvent(
                    phase="review",
                    event_type="human_response",
                    source="HumanReviewGateway",
                    summary="Überarbeitung angefordert und als neue Nachricht an den Drafter gesendet.",
                    payload={"guidance": decision.guidance},
                ),
                EngineEvent(
                    phase="draft",
                    event_type="simulated_agent_output",
                    source="DemoDraftExecutor",
                    summary="Überarbeiteter Lernentwurf erzeugt.",
                    payload={"recommendation": revised},
                ),
                EngineEvent(
                    phase="checkpoint",
                    event_type="checkpoint_saved",
                    source="DemoCheckpointStore",
                    summary="Neuer Lern-Checkpoint gespeichert.",
                    payload={"checkpoint_id": checkpoint_id},
                ),
            ],
        )

    @staticmethod
    def _draft(case: InvoiceCaseCreate, assessment: RiskAssessment) -> str:
        tone = {
            "low": "freundliche Zahlungserinnerung",
            "medium": "sachliche Zahlungserinnerung mit klarer Frist",
            "high": "interner Prüfvermerk; noch keine automatische Außenkommunikation",
        }[assessment.level]
        amount = f"{case.amount_eur:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return (
            f"Empfehlung für Rechnung {case.invoice_number} an {case.customer_name}: {tone}. "
            f"Offener Betrag: {amount} EUR, überfällig seit {case.days_overdue} Tagen. "
            f"Nächster kontrollierter Schritt: {assessment.deterministic_action}"
        )
