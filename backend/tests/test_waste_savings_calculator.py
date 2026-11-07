"""
Tests for Waste Savings Financial Calculations.
Validates strict Decimal arithmetic, zero float tolerance, conservative downsize ratios,
and multi-cloud billing correlation.
"""

from decimal import Decimal
import pytest

from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource
from backend.app.waste_detection.savings import SavingsCalculator


def test_savings_calculator_idle_compute_correlated_cost():
    """Validates 100% idle compute savings from correlated monthly cost."""
    res = CloudResource(
        resource_id="i-test-01",
        provider="AWS",
        account_id="111",
        monthly_cost=Decimal("146.5000"),
    )
    savings, methodology, details = SavingsCalculator.estimate_idle_compute_savings(res, [])
    assert isinstance(savings, Decimal)
    assert savings == Decimal("146.5000")
    assert "Correlated" in methodology
    assert details["confidence_level"] == "HIGH"


def test_savings_calculator_idle_compute_billing_records_fallback():
    """Validates fallback to unblended billing records summation when monthly_cost is 0."""
    res = CloudResource(
        resource_id="i-test-02",
        provider="AWS",
        account_id="111",
        monthly_cost=Decimal("0.0000"),
    )
    records = [
        BillingRecord(resource_id=res.resource_id, unblended_cost=Decimal("35.2500")),
        BillingRecord(resource_id=res.resource_id, unblended_cost=Decimal("42.7500")),
    ]
    savings, methodology, details = SavingsCalculator.estimate_idle_compute_savings(res, records)
    assert isinstance(savings, Decimal)
    assert savings == Decimal("78.0000")
    assert "Aggregated 2 billing line items" in methodology


def test_savings_calculator_oversized_downsize_ratio():
    """Validates 50% conservative downsize savings calculation with strict Decimal precision."""
    res = CloudResource(
        resource_id="vm-oversized-01",
        provider="AZURE",
        account_id="sub-1",
        monthly_cost=Decimal("320.0000"),
    )
    savings, methodology, details = SavingsCalculator.estimate_oversized_compute_savings(res)
    assert isinstance(savings, Decimal)
    assert savings == Decimal("160.0000")
    assert "50%" in methodology
    assert details["base_monthly_cost"] == "320.0000"


def test_savings_calculator_unattached_storage_capacity_fallback():
    """Validates unattached storage estimate from capacity ($0.08/GB) when monthly_cost is 0."""
    res = CloudResource(
        resource_id="vol-storage-01",
        provider="AWS",
        account_id="111",
        monthly_cost=Decimal("0.0000"),
        resource_metadata={"size_gb": 500},
    )
    savings, methodology, details = SavingsCalculator.estimate_unattached_storage_savings(res, [])
    assert isinstance(savings, Decimal)
    # 500 GB * 0.08 = 40.0000
    assert savings == Decimal("40.0000")
    assert "500" in methodology
    assert details["source"] == "capacity_rate_estimate"


def test_savings_calculator_zero_rounding_drift():
    """Validates that annualization (monthly * 12) experiences zero IEEE-754 binary floating drift."""
    monthly_waste = Decimal("13.3333")
    annual_waste = monthly_waste * Decimal("12")
    assert annual_waste == Decimal("159.9996")
    assert isinstance(annual_waste, Decimal)
