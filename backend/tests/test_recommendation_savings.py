"""
CloudSage Recommendation Savings Calculator Unit Tests.
Verifies strict Decimal math, annualization, percentages, ROI, and Zero Float Rule.
"""

from decimal import Decimal
import pytest
from backend.app.recommendations.savings import (
    annualize_savings,
    build_savings_breakdown,
    calculate_commitment_savings,
    calculate_idle_release_savings,
    calculate_rightsizing_savings,
    calculate_roi,
    calculate_savings_percentage,
    calculate_schedule_savings,
    calculate_storage_tier_savings,
    calculate_termination_savings,
    quantize_currency,
)


def test_quantize_currency_precision():
    """Confirms exact 4-decimal precision rounding."""
    val = Decimal("123.45678")
    assert quantize_currency(val) == Decimal("123.4568")


def test_calculate_termination_savings():
    """Termination recovers 100% of monthly cost."""
    assert calculate_termination_savings(Decimal("150.2500")) == Decimal("150.2500")
    assert calculate_termination_savings(Decimal("0.0000")) == Decimal("0.0000")
    assert calculate_termination_savings(Decimal("-50.0000")) == Decimal("0.0000")


def test_calculate_rightsizing_savings():
    """Rightsizing savings = current - target."""
    current = Decimal("292.0000")
    target = Decimal("146.0000")
    assert calculate_rightsizing_savings(current, target) == Decimal("146.0000")
    # Edge case: target > current should yield 0 savings
    assert calculate_rightsizing_savings(Decimal("100.0000"), Decimal("150.0000")) == Decimal("0.0000")


def test_calculate_schedule_savings():
    """Scheduling 50 hours/week out of 168 hours yields ~70.24% reduction."""
    current = Decimal("100.0000")
    savings = calculate_schedule_savings(current, running_hours_per_week=50)
    # (168 - 50) / 168 = 118 / 168 = 0.70238... -> 70.2381
    assert savings == Decimal("70.2381")

    # If running 168 hours, zero savings
    assert calculate_schedule_savings(current, running_hours_per_week=168) == Decimal("0.0000")


def test_calculate_storage_tier_savings():
    """Default 80% discount rate yields 80% savings."""
    current = Decimal("1000.0000")
    savings = calculate_storage_tier_savings(current, target_rate_multiplier=Decimal("0.2000"))
    assert savings == Decimal("800.0000")


def test_calculate_commitment_savings():
    """Commitment discount rate (30%) yields 30% savings."""
    spend = Decimal("5000.0000")
    savings = calculate_commitment_savings(spend, commitment_discount_rate=Decimal("0.3000"))
    assert savings == Decimal("1500.0000")


def test_annualize_savings():
    """Annualized savings = 12 * monthly savings."""
    monthly = Decimal("125.5000")
    assert annualize_savings(monthly) == Decimal("1506.0000")
    assert annualize_savings(Decimal("0.0000")) == Decimal("0.0000")


def test_calculate_savings_percentage():
    """Percentage savings calculation."""
    current = Decimal("400.0000")
    savings = Decimal("100.0000")
    assert calculate_savings_percentage(current, savings) == Decimal("25.00")
    # Edge cases
    assert calculate_savings_percentage(Decimal("0.0000"), savings) == Decimal("0.00")


def test_calculate_roi():
    """ROI calculation percentage."""
    annual_savings = Decimal("12000.0000")
    impl_cost = Decimal("2000.0000")
    # (12000 - 2000) / 2000 * 100 = 500.00%
    assert calculate_roi(annual_savings, impl_cost) == Decimal("500.00")
    # Zero implementation cost returns nominal 999.00%
    assert calculate_roi(annual_savings, Decimal("0.0000")) == Decimal("999.00")


def test_build_savings_breakdown():
    """Savings breakdown dictionary structure contains pure stringified decimals."""
    b = build_savings_breakdown(
        current_monthly_cost=Decimal("200.0000"),
        projected_monthly_cost=Decimal("50.0000"),
        monthly_savings=Decimal("150.0000"),
        annual_savings=Decimal("1800.0000"),
        formula_name="Test Rightsizing",
        parameters={"test": True},
    )
    assert b["formula"] == "Test Rightsizing"
    assert b["current_monthly_cost"] == "200.0000"
    assert b["estimated_monthly_savings"] == "150.0000"
    assert b["savings_percentage"] == "75.00"
