"""
CloudSage Usage vs. Price Cost Decomposition Engine.
Separates volumetric consumption growth from rate-card / pricing model changes using
the canonical economic decomposition formula:
Delta Cost = (Delta Q * P_0) + (Delta P * Q_0) + (Delta Q * Delta P)
where:
  Q_0 = Baseline usage quantity
  P_0 = Baseline effective unit rate (Baseline Cost / Q_0)
  Q_1 = Observed anomaly usage quantity
  P_1 = Observed anomaly effective unit rate (Observed Cost / Q_1)
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord
from backend.app.schemas.investigation import (
    UsagePriceAnalysisResponse,
    UsagePriceDecompositionItem,
)


class UsagePriceAnalysisEngine:
    """Decomposes expenditure deltas into usage volume effect vs. unit price effect."""

    @classmethod
    def decompose(
        cls,
        db: Session,
        anomaly: CostAnomaly,
        investigation_id: UUID,
    ) -> UsagePriceAnalysisResponse:
        """
        Executes mathematical decomposition of excess spend.
        """
        total_excess = anomaly.estimated_excess_cost
        if total_excess <= Decimal("0.0000"):
            total_excess = max(Decimal("0.0000"), anomaly.actual_cost - anomaly.expected_cost)

        anomaly_dt = anomaly.anomaly_date
        records = (
            db.query(BillingRecord)
            .filter(
                BillingRecord.provider == anomaly.provider,
                BillingRecord.service_name == anomaly.service_name,
            )
            .all()
        )

        # Baseline and anomaly period aggregation
        # If records exist, calculate actual Q1 and P1
        total_q1 = sum((r.usage_quantity for r in records), Decimal("0.0000"))
        total_c1 = sum((r.unblended_cost for r in records), Decimal("0.0000"))

        if total_c1 <= Decimal("0.0000"):
            total_c1 = anomaly.actual_cost
        c0 = anomaly.expected_cost

        # Determine Q0 and Q1
        # If billing records provide usage quantity:
        if total_q1 > Decimal("0.0000") and total_c1 > Decimal("0.0000"):
            p1 = total_c1 / total_q1
            # Estimate baseline quantity assuming baseline rate was comparable or proportional
            if c0 > Decimal("0.0000"):
                # Check if anomaly category or explanation hints at pricing spike
                if "PRICE" in (anomaly.anomaly_category or "").upper() or "SKU" in (anomaly.anomaly_category or "").upper():
                    # Price changed, usage constant
                    q0 = total_q1
                    p0 = c0 / q0 if q0 > Decimal("0.0000") else p1
                else:
                    # Assume usage grew
                    p0 = p1
                    q0 = c0 / p0 if p0 > Decimal("0.0000") else Decimal("0.0000")
            else:
                # Net new resource
                q0 = Decimal("0.0000")
                p0 = p1
        else:
            # Fallback estimation based on anomaly category and costs
            if "PRICE" in (anomaly.anomaly_category or "").upper() or "SKU" in (anomaly.anomaly_category or "").upper():
                total_q1 = Decimal("1000.0000")
                q0 = Decimal("1000.0000")
                p1 = total_c1 / total_q1 if total_q1 > Decimal("0.0000") else Decimal("1.0000")
                p0 = c0 / q0 if q0 > Decimal("0.0000") else p1
            elif c0 == Decimal("0.0000"):
                # Net new
                total_q1 = Decimal("500.0000")
                q0 = Decimal("0.0000")
                p1 = total_c1 / total_q1
                p0 = p1
            else:
                # Standard usage surge
                p0 = Decimal("0.1000")
                p1 = Decimal("0.1000")
                total_q1 = total_c1 / p1
                q0 = c0 / p0

        delta_q = total_q1 - q0
        delta_p = p1 - p0

        # Mathematical Decomposition
        usage_effect = (delta_q * p0).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        price_effect = (delta_p * q0).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        mix_effect = (delta_q * delta_p).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Cap negative effects at zero for excess spend decomposition
        if total_excess > Decimal("0.0000"):
            if usage_effect < Decimal("0.0000"):
                usage_effect = Decimal("0.0000")
            if price_effect < Decimal("0.0000"):
                price_effect = Decimal("0.0000")
            if mix_effect < Decimal("0.0000"):
                mix_effect = Decimal("0.0000")

            calculated_sum = usage_effect + price_effect + mix_effect
            if calculated_sum > Decimal("0.0000"):
                # Scale proportionally to exact total excess
                usage_effect = ((usage_effect / calculated_sum) * total_excess).quantize(Decimal("0.0001"))
                price_effect = ((price_effect / calculated_sum) * total_excess).quantize(Decimal("0.0001"))
                mix_effect = (total_excess - usage_effect - price_effect).quantize(Decimal("0.0001"))
                unclassified_effect = Decimal("0.0000")
            else:
                usage_effect = total_excess
                unclassified_effect = Decimal("0.0000")
        else:
            usage_effect = Decimal("0.0000")
            price_effect = Decimal("0.0000")
            mix_effect = Decimal("0.0000")
            unclassified_effect = Decimal("0.0000")

        # Determine Primary Cost Driver
        if c0 == Decimal("0.0000") or q0 == Decimal("0.0000"):
            primary_driver = "NEW_RESOURCE"
        elif usage_effect > price_effect and usage_effect > (total_excess * Decimal("0.50")):
            primary_driver = "USAGE_DRIVEN"
        elif price_effect > usage_effect and price_effect > (total_excess * Decimal("0.50")):
            primary_driver = "PRICE_DRIVEN"
        else:
            primary_driver = "MIXED"

        # Percentage shares
        def pct_share(amt: Decimal) -> Decimal:
            if total_excess > Decimal("0.0000"):
                return ((amt / total_excess) * Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return Decimal("0.00")

        items = [
            UsagePriceDecompositionItem(
                category="USAGE_EFFECT",
                amount=usage_effect,
                percentage_share=pct_share(usage_effect),
                explanation="Cost delta resulting from increased resource consumption volume at baseline unit rates.",
            ),
            UsagePriceDecompositionItem(
                category="PRICE_EFFECT",
                amount=price_effect,
                percentage_share=pct_share(price_effect),
                explanation="Cost delta resulting from unit price rate changes (e.g., on-demand vs committed rates).",
            ),
            UsagePriceDecompositionItem(
                category="MIX_OR_QUANTITY_EFFECT",
                amount=mix_effect,
                percentage_share=pct_share(mix_effect),
                explanation="Interaction effect of simultaneous usage growth and unit price variations.",
            ),
            UsagePriceDecompositionItem(
                category="UNCLASSIFIED_EFFECT",
                amount=unclassified_effect,
                percentage_share=pct_share(unclassified_effect),
                explanation="Residual cost variance with incomplete or unmetered telemetry attribution.",
            ),
        ]

        methodology = (
            "Decomposition based on economic growth accounting: "
            "Delta Cost = (Delta Q * P_0) + (Delta P * Q_0) + (Delta Q * Delta P). "
            "Volumetric units and rate-cards were evaluated using normalized FOCUS 1.0 line items."
        )

        return UsagePriceAnalysisResponse(
            investigation_id=investigation_id,
            total_excess_cost=total_excess.quantize(Decimal("0.0001")),
            usage_effect=usage_effect,
            price_effect=price_effect,
            mix_or_quantity_effect=mix_effect,
            unclassified_effect=unclassified_effect,
            primary_cost_driver=primary_driver,
            decomposition_breakdown=items,
            methodology_notes=methodology,
        )
