"""
CloudSage Recommendation Financial Savings Calculator.
Strictly adheres to the Zero Float Rule: all monetary operations use Python Decimal
with 4-decimal precision (Numeric(18, 4)).
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict


FOUR_PLACES = Decimal("0.0001")
TWO_PLACES = Decimal("0.01")


def quantize_currency(value: Decimal) -> Decimal:
    """Quantizes a Decimal value to 4 decimal places."""
    return value.quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def calculate_termination_savings(current_monthly_cost: Decimal) -> Decimal:
    """
    Terminating an idle/unattached resource eliminates 100% of its current monthly cost.
    """
    if current_monthly_cost <= Decimal("0.0000"):
        return Decimal("0.0000")
    return quantize_currency(current_monthly_cost)


def calculate_idle_release_savings(current_monthly_cost: Decimal) -> Decimal:
    """
    Releasing an idle asset (e.g. Elastic IP, idle load balancer) saves 100% of recurring cost.
    """
    return calculate_termination_savings(current_monthly_cost)


def calculate_rightsizing_savings(
    current_monthly_cost: Decimal,
    target_monthly_cost: Decimal,
) -> Decimal:
    """
    Downsizing a resource to a smaller specification tier.
    Savings = current_cost - target_cost (cannot be negative).
    """
    if current_monthly_cost <= Decimal("0.0000"):
        return Decimal("0.0000")
    if target_monthly_cost < Decimal("0.0000"):
        target_monthly_cost = Decimal("0.0000")
    savings = current_monthly_cost - target_monthly_cost
    return quantize_currency(max(Decimal("0.0000"), savings))


def calculate_schedule_savings(
    current_monthly_cost: Decimal,
    running_hours_per_week: int = 50,
) -> Decimal:
    """
    Schedules non-production instances to run only during business hours (e.g. 50 hrs/week instead of 168 hrs).
    Savings = current_cost * ((168 - running_hours_per_week) / 168).
    Default 50 hrs/week gives ~70.24% reduction.
    """
    if current_monthly_cost <= Decimal("0.0000"):
        return Decimal("0.0000")
    if running_hours_per_week >= 168:
        return Decimal("0.0000")
    if running_hours_per_week < 0:
        running_hours_per_week = 0

    total_hours = Decimal("168.0")
    off_hours = Decimal(168 - running_hours_per_week)
    reduction_fraction = off_hours / total_hours
    savings = current_monthly_cost * reduction_fraction
    return quantize_currency(savings)


def calculate_storage_tier_savings(
    current_monthly_cost: Decimal,
    target_rate_multiplier: Decimal = Decimal("0.2000"),
) -> Decimal:
    """
    Transitioning infrequent/cold data to archival storage tiers (e.g. S3 Standard -> Glacier, Blob Hot -> Cold/Archive).
    Default target multiplier 0.20 assumes an 80% discount rate.
    """
    if current_monthly_cost <= Decimal("0.0000"):
        return Decimal("0.0000")
    if target_rate_multiplier >= Decimal("1.0000"):
        return Decimal("0.0000")
    if target_rate_multiplier < Decimal("0.0000"):
        target_rate_multiplier = Decimal("0.0000")

    savings_multiplier = Decimal("1.0000") - target_rate_multiplier
    savings = current_monthly_cost * savings_multiplier
    return quantize_currency(savings)


def calculate_commitment_savings(
    on_demand_monthly_spend: Decimal,
    commitment_discount_rate: Decimal = Decimal("0.3000"),
) -> Decimal:
    """
    Simulates purchasing 1-year or 3-year commitment discount (AWS Savings Plans/RI, Azure Reservations, GCP CUD).
    Default discount rate 30% (0.3000).
    """
    if on_demand_monthly_spend <= Decimal("0.0000"):
        return Decimal("0.0000")
    if commitment_discount_rate <= Decimal("0.0000"):
        return Decimal("0.0000")
    if commitment_discount_rate >= Decimal("1.0000"):
        commitment_discount_rate = Decimal("0.9000")

    savings = on_demand_monthly_spend * commitment_discount_rate
    return quantize_currency(savings)


def annualize_savings(monthly_savings: Decimal) -> Decimal:
    """Multiplies monthly savings by 12 months with exact Decimal arithmetic."""
    if monthly_savings <= Decimal("0.0000"):
        return Decimal("0.0000")
    return quantize_currency(monthly_savings * Decimal("12"))


def calculate_savings_percentage(
    current_monthly_cost: Decimal,
    monthly_savings: Decimal,
) -> Decimal:
    """Calculates percentage reduction (0.00% to 100.00%)."""
    if current_monthly_cost <= Decimal("0.0000") or monthly_savings <= Decimal("0.0000"):
        return Decimal("0.00")
    pct = (monthly_savings / current_monthly_cost) * Decimal("100.0")
    capped = min(Decimal("100.00"), max(Decimal("0.00"), pct))
    return capped.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calculate_roi(
    annual_savings: Decimal,
    estimated_implementation_cost: Decimal = Decimal("0.0000"),
) -> Decimal:
    """
    Computes annualized ROI percentage.
    If implementation cost is 0, returns high nominal ROI (999.00%).
    """
    if annual_savings <= Decimal("0.0000"):
        return Decimal("0.00")
    if estimated_implementation_cost <= Decimal("0.0000"):
        return Decimal("999.00")
    net_savings = annual_savings - estimated_implementation_cost
    roi = (net_savings / estimated_implementation_cost) * Decimal("100.0")
    return roi.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def build_savings_breakdown(
    current_monthly_cost: Decimal,
    projected_monthly_cost: Decimal,
    monthly_savings: Decimal,
    annual_savings: Decimal,
    formula_name: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """Builds a structured savings calculation audit dict."""
    pct = calculate_savings_percentage(current_monthly_cost, monthly_savings)
    return {
        "formula": formula_name,
        "current_monthly_cost": str(current_monthly_cost),
        "projected_monthly_cost": str(projected_monthly_cost),
        "estimated_monthly_savings": str(monthly_savings),
        "estimated_annual_savings": str(annual_savings),
        "savings_percentage": str(pct),
        "parameters": parameters,
    }
