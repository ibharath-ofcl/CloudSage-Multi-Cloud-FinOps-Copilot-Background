"""
CloudSage Recommendation Scoring Unit Tests.
Tests multi-factor priority and risk scoring formulas, quantization, and tier mappings.
"""

from decimal import Decimal
import pytest
from backend.app.core.enums import ImplementationEffort, Priority, RiskLevel
from backend.app.recommendations.scoring import (
    calculate_priority_tier,
    calculate_risk_level_from_score,
    calculate_savings_score,
    compute_multi_factor_score,
    quantize_score,
)


def test_quantize_score_bounds():
    """Score quantization must clamp within [0.0000, 1.0000] and return 4 decimal places."""
    assert quantize_score(Decimal("1.5000")) == Decimal("1.0000")
    assert quantize_score(Decimal("-0.2000")) == Decimal("0.0000")
    assert quantize_score(Decimal("0.55556")) == Decimal("0.5556")


def test_savings_score_normalization():
    """Savings score scales linearly up to $1,000/month."""
    assert calculate_savings_score(Decimal("0.0000")) == Decimal("0.0000")
    assert calculate_savings_score(Decimal("500.0000")) == Decimal("0.5000")
    assert calculate_savings_score(Decimal("1000.0000")) == Decimal("1.0000")
    assert calculate_savings_score(Decimal("5000.0000")) == Decimal("1.0000")


def test_priority_tier_mapping():
    """Asserts composite score maps to correct priority tier."""
    assert calculate_priority_tier(Decimal("0.8500")) == Priority.P1
    assert calculate_priority_tier(Decimal("0.7500")) == Priority.P1
    assert calculate_priority_tier(Decimal("0.6000")) == Priority.P2
    assert calculate_priority_tier(Decimal("0.5000")) == Priority.P2
    assert calculate_priority_tier(Decimal("0.3500")) == Priority.P3
    assert calculate_priority_tier(Decimal("0.2500")) == Priority.P3
    assert calculate_priority_tier(Decimal("0.1500")) == Priority.P4


def test_risk_level_mapping():
    """Asserts risk score maps to correct risk level."""
    assert calculate_risk_level_from_score(Decimal("0.0500")) == RiskLevel.NONE
    assert calculate_risk_level_from_score(Decimal("0.2000")) == RiskLevel.LOW
    assert calculate_risk_level_from_score(Decimal("0.5000")) == RiskLevel.MEDIUM
    assert calculate_risk_level_from_score(Decimal("0.7500")) == RiskLevel.HIGH
    assert calculate_risk_level_from_score(Decimal("0.9500")) == RiskLevel.CRITICAL


def test_compute_multi_factor_score_high_savings_quick_win():
    """High savings + quick win + low risk should produce P1 priority."""
    breakdown = compute_multi_factor_score(
        monthly_savings=Decimal("1500.0000"),
        confidence_score=Decimal("1.0000"),
        effort=ImplementationEffort.QUICK_WIN,
        risk=RiskLevel.LOW,
        urgency_boost=False,
    )
    assert breakdown.priority_tier == Priority.P1
    assert breakdown.composite_priority_score >= Decimal("0.7500")
    assert breakdown.effort_level == ImplementationEffort.QUICK_WIN
    assert breakdown.risk_level == RiskLevel.LOW


def test_compute_multi_factor_score_low_savings_complex():
    """Low savings + complex effort + high risk should produce P3/P4 priority."""
    breakdown = compute_multi_factor_score(
        monthly_savings=Decimal("20.0000"),
        confidence_score=Decimal("0.7000"),
        effort=ImplementationEffort.COMPLEX,
        risk=RiskLevel.HIGH,
        urgency_boost=False,
    )
    assert breakdown.priority_tier in (Priority.P3, Priority.P4)
    assert breakdown.composite_priority_score < Decimal("0.5000")


def test_urgency_bonus_applied():
    """Urgency boost adds bonus score without exceeding 1.0000."""
    regular = compute_multi_factor_score(
        monthly_savings=Decimal("400.0000"),
        confidence_score=Decimal("0.8000"),
        effort=ImplementationEffort.LOW,
        risk=RiskLevel.LOW,
        urgency_boost=False,
    )
    boosted = compute_multi_factor_score(
        monthly_savings=Decimal("400.0000"),
        confidence_score=Decimal("0.8000"),
        effort=ImplementationEffort.LOW,
        risk=RiskLevel.LOW,
        urgency_boost=True,
    )
    assert boosted.composite_priority_score > regular.composite_priority_score
    assert boosted.urgency_score == Decimal("0.0500")
