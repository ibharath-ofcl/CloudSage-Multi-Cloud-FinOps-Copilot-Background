"""
CloudSage Recommendation Multi-Factor Prioritization and Risk Scoring Engine.
Computes objective, auditable priority and risk scores for advisory recommendations.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple

from backend.app.core.enums import ImplementationEffort, Priority, RiskLevel
from backend.app.recommendations.models import ScoringBreakdown

SCORE_QUANT = Decimal("0.0001")


def quantize_score(val: Decimal) -> Decimal:
    """Clamps value between 0.0000 and 1.0000 and quantizes to 4 decimal places."""
    clamped = min(Decimal("1.0000"), max(Decimal("0.0000"), val))
    return clamped.quantize(SCORE_QUANT, rounding=ROUND_HALF_UP)


EFFORT_SCORES: Dict[ImplementationEffort, Decimal] = {
    ImplementationEffort.QUICK_WIN: Decimal("1.0000"),
    ImplementationEffort.LOW: Decimal("0.8000"),
    ImplementationEffort.MEDIUM: Decimal("0.5000"),
    ImplementationEffort.HIGH: Decimal("0.3000"),
    ImplementationEffort.COMPLEX: Decimal("0.1000"),
}

RISK_LEVEL_SCORES: Dict[RiskLevel, Decimal] = {
    RiskLevel.NONE: Decimal("0.0500"),
    RiskLevel.LOW: Decimal("0.2000"),
    RiskLevel.MEDIUM: Decimal("0.5000"),
    RiskLevel.HIGH: Decimal("0.8000"),
    RiskLevel.CRITICAL: Decimal("1.0000"),
}


def calculate_savings_score(monthly_savings: Decimal) -> Decimal:
    """
    Computes normalized financial impact score based on monthly savings.
    $1,000+/mo yields 1.0000; scales down with a minimum base of 0.1000.
    """
    if monthly_savings <= Decimal("0.0000"):
        return Decimal("0.0000")
    if monthly_savings >= Decimal("1000.0000"):
        return Decimal("1.0000")
    # Linear scale from $0 to $1,000
    norm = monthly_savings / Decimal("1000.0000")
    return quantize_score(norm)


def calculate_risk_level_from_score(risk_score: Decimal) -> RiskLevel:
    """Maps normalized risk score (0-1) to RiskLevel enum."""
    if risk_score <= Decimal("0.1000"):
        return RiskLevel.NONE
    elif risk_score <= Decimal("0.3500"):
        return RiskLevel.LOW
    elif risk_score <= Decimal("0.6500"):
        return RiskLevel.MEDIUM
    elif risk_score <= Decimal("0.8500"):
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


def calculate_priority_tier(composite_score: Decimal) -> Priority:
    """Maps normalized composite score (0-1) to Priority tier."""
    if composite_score >= Decimal("0.7500"):
        return Priority.P1
    elif composite_score >= Decimal("0.5000"):
        return Priority.P2
    elif composite_score >= Decimal("0.2500"):
        return Priority.P3
    else:
        return Priority.P4


def compute_multi_factor_score(
    monthly_savings: Decimal,
    confidence_score: Decimal = Decimal("1.0000"),
    effort: ImplementationEffort = ImplementationEffort.LOW,
    risk: RiskLevel = RiskLevel.LOW,
    urgency_boost: bool = False,
    custom_risk_score: Optional[Decimal] = None,
) -> ScoringBreakdown:
    """
    Computes composite priority score and full multi-factor breakdown.
    Formula:
        Composite = 0.35 * savings_norm + 0.25 * confidence + 0.20 * effort_factor + 0.20 * (1 - risk_score)
        + urgency_boost (0.05 bonus if active anomaly/critical waste)
    """
    savings_norm = calculate_savings_score(monthly_savings)
    conf_norm = quantize_score(confidence_score)
    effort_norm = EFFORT_SCORES.get(effort, Decimal("0.5000"))

    if custom_risk_score is not None:
        risk_norm = quantize_score(custom_risk_score)
        risk_lvl = calculate_risk_level_from_score(risk_norm)
    else:
        risk_norm = RISK_LEVEL_SCORES.get(risk, Decimal("0.2000"))
        risk_lvl = risk

    inv_risk = quantize_score(Decimal("1.0000") - risk_norm)
    urgency_norm = Decimal("0.0500") if urgency_boost else Decimal("0.0000")

    # Weighted sum
    composite = (
        (savings_norm * Decimal("0.3500")) +
        (conf_norm * Decimal("0.2500")) +
        (effort_norm * Decimal("0.2000")) +
        (inv_risk * Decimal("0.2000")) +
        urgency_norm
    )
    final_priority_score = quantize_score(composite)
    tier = calculate_priority_tier(final_priority_score)

    factors = {
        "savings_component": str(quantize_score(savings_norm * Decimal("0.3500"))),
        "confidence_component": str(quantize_score(conf_norm * Decimal("0.2500"))),
        "effort_component": str(quantize_score(effort_norm * Decimal("0.2000"))),
        "risk_mitigation_component": str(quantize_score(inv_risk * Decimal("0.2000"))),
        "urgency_bonus": str(urgency_norm),
    }

    return ScoringBreakdown(
        savings_score=savings_norm,
        confidence_score=conf_norm,
        effort_score=effort_norm,
        risk_score=risk_norm,
        urgency_score=urgency_norm,
        composite_priority_score=final_priority_score,
        priority_tier=tier,
        risk_level=risk_lvl,
        effort_level=effort,
        factors_explanation=factors,
    )
