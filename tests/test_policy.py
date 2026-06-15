from maf_lab.domain import InvoiceCaseCreate, RunMode
from maf_lab.policy import assess_risk


def test_high_risk_amount_requires_human_review() -> None:
    case = InvoiceCaseCreate(
        customer_name="Test GmbH",
        invoice_number="RE-1",
        amount_eur=6000,
        days_overdue=10,
        context="",
        mode=RunMode.DEMO,
    )
    result = assess_risk(case)
    assert result.level == "high"
    assert "Menschliche Prüfung" in result.deterministic_action


def test_low_risk_case_remains_low() -> None:
    case = InvoiceCaseCreate(
        customer_name="Test GmbH",
        invoice_number="RE-2",
        amount_eur=400,
        days_overdue=5,
        context="",
        mode=RunMode.DEMO,
    )
    assert assess_risk(case).level == "low"
