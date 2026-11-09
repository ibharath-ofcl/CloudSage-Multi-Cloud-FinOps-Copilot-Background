"""
CloudSage Root Cause Analysis Confidence Scoring Engine.
Deterministic, explainable rule-based scoring that evaluates corroborating
and contradictory evidence signals across billing, inventory, telemetry, and alerts.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from backend.app.core.enums import ConfidenceCategory


class ConfidenceScorer:
    """
    Evaluates evidence certainty for root-cause findings and hypotheses.
    Enforces strict Decimal arithmetic and transparent rule weights.
    """

    # Signal Weights (Base max = 1.0000)
    WEIGHT_DIRECT_BILLING_EVIDENCE = Decimal("0.3500")
    WEIGHT_INVENTORY_MATCH = Decimal("0.2500")
    WEIGHT_TELEMETRY_CORRELATION = Decimal("0.2000")
    WEIGHT_CROSS_SIGNAL_MATCH = Decimal("0.2000")

    # Penalties
    PENALTY_CONTRADICTORY_TELEMETRY = Decimal("0.2500")
    PENALTY_STALE_INVENTORY = Decimal("0.1500")
    PENALTY_MISSING_BASELINE = Decimal("0.2000")
    PENALTY_UNRECONCILED_RESOURCE = Decimal("0.1500")

    @classmethod
    def evaluate(
        cls,
        has_direct_billing: bool = True,
        billing_record_count: int = 1,
        has_inventory_match: bool = False,
        inventory_status: Optional[str] = None,
        is_inventory_stale: bool = False,
        has_telemetry_metrics: bool = False,
        telemetry_corroborates_surge: Optional[bool] = None,
        has_waste_detection_match: bool = False,
        has_recommendation_match: bool = False,
        has_alert_match: bool = False,
        has_valid_baseline: bool = True,
        is_unreconciled: bool = False,
        additional_notes: Optional[List[str]] = None,
    ) -> Tuple[Decimal, str, List[str], List[str], Optional[str]]:
        """
        Calculates deterministic confidence score, category, observations, and next step.

        Returns:
            (confidence_score, confidence_category, supporting_observations,
             contradictory_observations, suggested_next_step)
        """
        score = Decimal("0.0000")
        supporting: List[str] = []
        contradictory: List[str] = []

        # 1. Billing Record Verification
        if has_direct_billing and billing_record_count > 0:
            score += cls.WEIGHT_DIRECT_BILLING_EVIDENCE
            supporting.append(
                f"Direct billing line-item evidence confirmed ({billing_record_count} records substantiate spend)"
            )
        else:
            contradictory.append("No direct normalized billing line-items located for the anomaly scope")

        # 2. Baseline Validity
        if not has_valid_baseline:
            score -= cls.PENALTY_MISSING_BASELINE
            contradictory.append("Historical baseline window is sparse or missing; expected spend estimated")

        # 3. Inventory Discovery & State
        if has_inventory_match:
            score += cls.WEIGHT_INVENTORY_MATCH
            supporting.append(f"Cloud resource confirmed in multi-cloud inventory (status: {inventory_status or 'active'})")
            if is_inventory_stale:
                score -= cls.PENALTY_STALE_INVENTORY
                contradictory.append("Inventory record is stale (>48 hours without synchronization)")
        else:
            contradictory.append("Resource identifier not found in discovered inventory catalog (unregistered or deleted)")

        if is_unreconciled:
            score -= cls.PENALTY_UNRECONCILED_RESOURCE
            contradictory.append("Resource marked as UNRECONCILED between cloud provider inventory and billing line items")

        # 4. Telemetry Metrics
        if has_telemetry_metrics:
            if telemetry_corroborates_surge is True:
                score += cls.WEIGHT_TELEMETRY_CORRELATION
                supporting.append("Telemetry utilization metrics (CPU/Memory/I/O) show concurrent surge matching cost spike")
            elif telemetry_corroborates_surge is False:
                score -= cls.PENALTY_CONTRADICTORY_TELEMETRY
                contradictory.append("Utilization metrics remain near zero or flat despite significant cost surge (possible pricing tier change or idle provisioned capacity)")
            else:
                score += Decimal("0.1000")
                supporting.append("Telemetry utilization metrics present but neutral/inconclusive regarding spike cause")

        # 5. Cross-Signal Corroboration
        cross_signals_found = 0
        if has_waste_detection_match:
            cross_signals_found += 1
            supporting.append("Corroborated by active Waste Detection finding on identical cloud resource")
        if has_recommendation_match:
            cross_signals_found += 1
            supporting.append("Corroborated by existing FinOps optimization recommendation for this resource")
        if has_alert_match:
            cross_signals_found += 1
            supporting.append("Corroborated by enterprise alert instance triggered for this anomaly")

        if cross_signals_found > 0:
            bonus = min(cls.WEIGHT_CROSS_SIGNAL_MATCH, Decimal("0.1000") * cross_signals_found)
            score += bonus

        # Ensure bounds [0.0000, 1.0000]
        if score > Decimal("1.0000"):
            score = Decimal("1.0000")
        elif score < Decimal("0.0000"):
            score = Decimal("0.0000")

        score = score.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Categorize
        if score >= Decimal("0.8000"):
            category = ConfidenceCategory.HIGH.value
            next_step = "Proceed with recommended remediation playbook or cost reallocation."
        elif score >= Decimal("0.5000"):
            category = ConfidenceCategory.MEDIUM.value
            next_step = "Inspect resource metric time-series and verify recent cloud deployment logs."
        elif score >= Decimal("0.2000"):
            category = ConfidenceCategory.LOW.value
            next_step = "Gather additional operational telemetry and contact resource owner for context."
        else:
            category = ConfidenceCategory.INSUFFICIENT_EVIDENCE.value
            next_step = "Trigger manual cloud provider audit; insufficient telemetry to establish causality."

        return score, category, supporting, contradictory, next_step
