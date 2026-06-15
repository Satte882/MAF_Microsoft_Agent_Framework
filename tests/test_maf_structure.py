import asyncio
import time
from pathlib import Path

import httpx
from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI

from maf_lab.config import Settings
from maf_lab.domain import HumanDecision, InvoiceCaseCreate, RunRecord, RunStatus, utc_now_iso
from maf_lab.maf_engine import MAF_AVAILABLE, MicrosoftAgentFrameworkEngine, _build_workflow
from maf_lab.policy import assess_risk


def test_real_maf_workflow_graph_builds_without_network(tmp_path: Path) -> None:
    assert MAF_AVAILABLE is True
    settings = Settings(
        data_dir=tmp_path,
        openai_api_key="structural-test-key",
        openai_model="gpt-5.4-nano",
    )
    settings.ensure_directories()
    workflow, _ = _build_workflow(
        settings,
        settings.checkpoint_root / "structural-run",
        "structural-run",
    )
    assert workflow.name == "invoice-review-structural-run"


def test_real_maf_checkpoint_and_resume_with_mock_provider(tmp_path: Path) -> None:
    async def scenario() -> None:
        async def mock_handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "id": "resp_test",
                    "object": "response",
                    "created_at": time.time(),
                    "model": "mock-model",
                    "output": [
                        {
                            "id": "msg_test",
                            "type": "message",
                            "status": "completed",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "Mock recommendation",
                                    "annotations": [],
                                }
                            ],
                        }
                    ],
                    "parallel_tool_calls": True,
                    "tool_choice": "auto",
                    "tools": [],
                    "status": "completed",
                },
            )

        http_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        try:
            async_openai = AsyncOpenAI(
                api_key="test-key",
                base_url="http://mock.local/v1",
                http_client=http_client,
            )
            chat_client = OpenAIChatClient(async_client=async_openai, model="mock-model")
            settings = Settings(
                data_dir=tmp_path,
                openai_api_key="test-key",
                openai_model="mock-model",
            )
            settings.ensure_directories()
            engine = MicrosoftAgentFrameworkEngine(settings, chat_client=chat_client)
            case = InvoiceCaseCreate(
                customer_name="Muster SHK GmbH",
                invoice_number="RE-MAF-1",
                amount_eur=2300,
                days_overdue=28,
                context="Bereits erinnert",
                mode="maf",
            )
            assessment = assess_risk(case)
            started = await engine.start("maf-run-1", case, assessment)
            assert started.status is RunStatus.AWAITING_HUMAN
            assert started.recommendation == "Mock recommendation"
            assert started.checkpoint_id
            assert started.request_id

            now = utc_now_iso()
            persisted_run = RunRecord(
                id="maf-run-1",
                created_at=now,
                updated_at=now,
                mode="maf",
                status=RunStatus.AWAITING_HUMAN,
                customer_name=case.customer_name,
                invoice_number=case.invoice_number,
                amount_eur=case.amount_eur,
                days_overdue=case.days_overdue,
                context=case.context,
                risk_level=assessment.level,
                risk_reasons=assessment.reasons,
                deterministic_action=assessment.deterministic_action,
                recommendation=started.recommendation,
                checkpoint_id=started.checkpoint_id,
                request_id=started.request_id,
            )
            resumed = await engine.resume(
                persisted_run,
                HumanDecision(action="approve", guidance=""),
            )
            assert resumed.status is RunStatus.COMPLETED
            assert resumed.output == "Mock recommendation"
        finally:
            await http_client.aclose()

    asyncio.run(scenario())
