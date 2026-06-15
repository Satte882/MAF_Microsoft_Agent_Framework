from pathlib import Path

from fastapi.testclient import TestClient

from maf_lab.api import create_app
from maf_lab.config import Settings


def make_client(tmp_path: Path) -> TestClient:
    app = create_app(Settings(data_dir=tmp_path, openai_api_key=None))
    return TestClient(app)


def test_health_and_system_info(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        system = client.get("/api/system").json()
        assert system["provider_configured"] is False
        assert system["supported_modes"] == ["demo", "maf"]


def test_complete_demo_human_approval_flow(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/runs",
            json={
                "customer_name": "Muster SHK GmbH",
                "invoice_number": "RE-2026-1",
                "amount_eur": 2500,
                "days_overdue": 25,
                "context": "Bereits erinnert",
                "mode": "demo",
            },
        )
        assert response.status_code == 201
        run = response.json()
        assert run["status"] == "awaiting_human"
        assert run["checkpoint_id"].startswith("demo-cp-")
        assert any(event["event_type"] == "request_info" for event in run["events"])

        decision = client.post(
            f"/api/runs/{run['id']}/decision",
            json={"action": "approve", "guidance": ""},
        )
        assert decision.status_code == 200
        completed = decision.json()
        assert completed["status"] == "completed"
        assert completed["output"] == completed["recommendation"]
        assert len(completed["checkpoints"]) == 1


def test_revision_creates_new_checkpoint(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        run = client.post(
            "/api/runs",
            json={
                "customer_name": "Muster SHK GmbH",
                "invoice_number": "RE-2026-2",
                "amount_eur": 900,
                "days_overdue": 12,
                "context": "",
                "mode": "demo",
            },
        ).json()
        revised = client.post(
            f"/api/runs/{run['id']}/decision",
            json={"action": "revise", "guidance": "Kürzer formulieren"},
        ).json()
        assert revised["status"] == "awaiting_human"
        assert "Kürzer formulieren" in revised["recommendation"]
        assert len(revised["checkpoints"]) == 2
