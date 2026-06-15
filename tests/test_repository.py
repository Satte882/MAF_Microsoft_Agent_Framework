from pathlib import Path

from maf_lab.domain import InvoiceCaseCreate, RunMode
from maf_lab.policy import assess_risk
from maf_lab.repository import SQLiteRepository


def test_repository_roundtrip(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "test.db")
    repository.initialize()
    case = InvoiceCaseCreate(
        customer_name="Test GmbH",
        invoice_number="RE-7",
        amount_eur=1200,
        days_overdue=14,
        context="",
        mode=RunMode.DEMO,
    )
    repository.create_run("run-1", case, assess_risk(case))
    repository.add_event("run-1", "test", "created", "pytest", "event")
    detail = repository.get_run_detail("run-1")
    assert detail.invoice_number == "RE-7"
    assert detail.events[0].source == "pytest"
