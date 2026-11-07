"""
CloudSage Financial Impact Calculator.
Computes deterministic financial impact metrics: absolute deviation, percentage deviation,
estimated excess cost, projected monthly/annual impact, and severity scoring with strict Decimal arithmetic.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from backend.app.core.enums import Severity
from backend.app.anomaly_detection.statistics import PRECISION_FOUR

DAYS_PER_MONTH = Decimal("30.0000")
DAYS_PER_YEAR = Decimal("365.0000")


def calculate_deviations(
    observed_cost: Decimal,
    expected_cost: Decimal,
) -> Dict[str, Decimal]:
    """Calculates absolute and percentage deviations between observed and expected cost."""
    diff = observed_cost - expected_cost
    abs_dev = abs(diff).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)

    if expected_cost > Decimal("0.0000"):
        pct_dev = ((diff / expected_cost) * Decimal("100.0000")).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
    elif diff > Decimal("0.0000"):
        pct_dev = Decimal("100.0000")
    else:
        pct_dev = Decimal("0.0000")

    return {
        "absolute_deviation": abs_dev,
        "percentage_deviation": pct_dev,
    }


def calculate_excess_cost(
    observed_cost: Decimal,
    expected_cost: Decimal,
) -> Decimal:
    """Calculates excess cost above baseline. Returns 0.0000 if observed <= expected."""
    excess = observed_cost - expected_cost
    if excess < Decimal("0.0000"):
        return Decimal("0.0000")
    return excess.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)


def calculate_projected_impact(
    daily_excess_cost: Decimal,
    anomaly_type: str = "SERVICE_SPIKE",  # SERVICE_SPIKE, PERSISTENT_STEP, GRADUAL_ESCALATION, etc.
    duration_days: int = 1,
) -> Dict[str, Decimal]:
    """
    Projects financial impact over monthly and annual horizons.
    Persistent steps project across 30 days and 365 days.
    Temporary spikes reflect their discrete duration.
    """
    if daily_excess_cost <= Decimal("0.0000"):
        zero = Decimal("0.0000")
        return {"projected_monthly_impact": zero, "projected_annual_impact": zero}

    if anomaly_type in ("PERSISTENT_STEP", "GRADUAL_ESCALATION"):
        monthly = (daily_excess_cost * DAYS_PER_MONTH).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
        annual = (daily_excess_cost * DAYS_PER_YEAR).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
    else:
        # Isolated spike: monthly impact equals the excess cost incurred during the spike
        spike_cost = (daily_excess_cost * Decimal(str(duration_days))).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
        monthly = spike_cost
        annual = spike_cost

    return {
        "projected_monthly_impact": monthly,
        "projected_annual_impact": annual,
    }


def determine_severity(
    estimated_excess_cost: Decimal,
    percentage_deviation: Decimal,
) -> Severity:
    """
    Assigns FinOps severity tier based on excess dollar magnitude and percentage growth:
    - CRITICAL: >= $1,000 excess OR >= 200% increase with >= $250 excess
    - HIGH: >= $250 excess OR >= 100% increase with >= $50 excess
    - MEDIUM: >= $50 excess OR >= 50% increase with >= $15 excess
    - LOW: All other anomalies
    """
    if (
        estimated_excess_cost >= Decimal("1000.0000")
        or (percentage_deviation >= Decimal("200.0000") and estimated_excess_cost >= Decimal("250.0000"))
    ):
        return Severity.CRITICAL

    if (
        estimated_excess_cost >= Decimal("250.0000")
        or (percentage_deviation >= Decimal("100.0000") and estimated_excess_cost >= Decimal("50.0000"))
    ):
        return Severity.HIGH

    if (
        estimated_excess_cost >= Decimal("50.0000")
        or (percentage_deviation >= Decimal("50.0000") and estimated_excess_cost >= Decimal("15.0000"))
    ):
        return Severity.MEDIUM

    return Severity.LOW


def aggregate_deduplicated_impact(
    anomalies: List[Dict[str, Any]],
) -> Dict[str, Decimal]:
    """
    Computes anti-double-counting aggregate financial impact across anomalies.
    Prevents adding both service-level and resource-level excess costs for the same scope and date.
    Prioritizes finer-grained resource level when present, otherwise uses service level.
    """
    grouped: Dict[str, Decimal] = {}

    for anom in anomalies:
        provider = anom.get("provider", "")
        account_id = anom.get("account_id", "")
        service_name = anom.get("service_name", "")
        anom_date = str(anom.get("anomaly_date", ""))
        resource_id = anom.get("resource_id")
        excess = anom.get("estimated_excess_cost", Decimal("0.0000"))

        if not isinstance(excess, Decimal):
            excess = Decimal(str(excess))

        if resource_id:
            # Resource-level key
            key = f"RES:{provider}:{account_id}:{service_name}:{resource_id}:{anom_date}"
        else:
            # Service-level key
            key = f"SRV:{provider}:{account_id}:{service_name}:{anom_date}"

        # Store max excess for that specific entity on that date
        grouped[key] = max(grouped.get(key, Decimal("0.0000")), excess)

    # In a hierarchy where SRV and RES exist for the same date, deduplicate:
    # If any RES exists for that provider:account:service:date, subtract or drop the SRV duplicate
    srv_keys = [k for k in grouped.keys() if k.startswith("SRV:")]
    res_keys = [k for k in grouped.keys() if k.startswith("RES:")]

    total = Decimal("0.0000")
    active_srv_covered = set()
    for rk in res_keys:
        total += grouped[rk]
        # Identify parent service
        parts = rk.split(":")
        # RES:provider:account:service:res_id:date
        if len(parts) >= 6:
            srv_parent = f"SRV:{parts[1]}:{parts[2]}:{parts[3]}:{parts[5]}"
            active_srv_covered.add(srv_parent)

    for sk in srv_keys:
        if sk not in active_srv_covered:
            total += grouped[sk]

    return {
        "deduplicated_total_excess_cost": total.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP),
    }
