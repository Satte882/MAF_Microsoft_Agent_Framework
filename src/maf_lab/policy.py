from __future__ import annotations

from maf_lab.domain import InvoiceCaseCreate, RiskAssessment


HIGH_RISK_TERMS = {
    "insolvenz",
    "insolvent",
    "streit",
    "widerspruch",
    "anwalt",
    "mangel",
    "reklamation",
}


def assess_risk(case: InvoiceCaseCreate) -> RiskAssessment:
    reasons: list[str] = []
    context_terms = set(case.context.lower().replace(",", " ").split())

    if case.amount_eur >= 5_000:
        reasons.append("Forderungsbetrag ab 5.000 EUR")
    if case.days_overdue >= 45:
        reasons.append("Mindestens 45 Tage überfällig")
    matched_terms = sorted(HIGH_RISK_TERMS.intersection(context_terms))
    if matched_terms:
        reasons.append(f"Konflikt- oder Insolvenzsignal: {', '.join(matched_terms)}")

    if reasons:
        return RiskAssessment(
            level="high",
            reasons=reasons,
            deterministic_action="Menschliche Prüfung vor jeder externen Aktion erzwingen.",
        )

    medium_reasons: list[str] = []
    if case.amount_eur >= 1_500:
        medium_reasons.append("Forderungsbetrag ab 1.500 EUR")
    if case.days_overdue >= 21:
        medium_reasons.append("Mindestens 21 Tage überfällig")

    if medium_reasons:
        return RiskAssessment(
            level="medium",
            reasons=medium_reasons,
            deterministic_action="Entwurf erzeugen und Freigabe einholen.",
        )

    return RiskAssessment(
        level="low",
        reasons=["Kein definierter Hoch- oder Mittelrisiko-Auslöser"],
        deterministic_action="Standardentwurf erzeugen und Freigabe einholen.",
    )
