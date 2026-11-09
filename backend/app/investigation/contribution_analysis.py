"""
CloudSage Contribution Ranking & Pareto Analysis Engine.
Calculates ranked contributor lists, Pareto 80/20 thresholds,
individual contribution shares, and cumulative impact curves.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.core.enums import ConfidenceCategory
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource
from backend.app.schemas.investigation import (
    ContributionRankingItem,
    ContributionRankingResponse,
)


class ContributionAnalysisEngine:
    """Computes Pareto 80/20 contribution curves and ranked impact tables."""

    @classmethod
    def rank_contributors(
        cls,
        db: Session,
        anomaly: CostAnomaly,
        investigation_id: UUID,
    ) -> ContributionRankingResponse:
        """
        Ranks contributors by excess cost and calculates cumulative Pareto distribution.
        """
        total_excess = anomaly.estimated_excess_cost
        if total_excess <= Decimal("0.0000"):
            total_excess = max(Decimal("0.0000"), anomaly.actual_cost - anomaly.expected_cost)

        # 1. Query billing records on anomaly date
        records = (
            db.query(BillingRecord)
            .filter(
                BillingRecord.provider == anomaly.provider,
                BillingRecord.service_name == anomaly.service_name,
            )
            .all()
        )

        cost_by_resource: Dict[str, Dict[str, Any]] = {}

        if records:
            for r in records:
                res_id = r.resource_id or r.resource_name or "UNTAGGED_RESOURCE"
                if res_id not in cost_by_resource:
                    cost_by_resource[res_id] = {
                        "resource_id": res_id,
                        "resource_name": r.resource_name,
                        "provider": r.provider,
                        "service_name": r.service_name,
                        "actual_cost": Decimal("0.0000"),
                    }
                cost_by_resource[res_id]["actual_cost"] += r.unblended_cost
        else:
            # Fallback to anomaly's known resource or primary scope
            res_id = anomaly.resource_id or f"{anomaly.service_name}-primary-cluster"
            cost_by_resource[res_id] = {
                "resource_id": res_id,
                "resource_name": anomaly.resource_id,
                "provider": anomaly.provider,
                "service_name": anomaly.service_name,
                "actual_cost": anomaly.actual_cost,
            }

        # Sort resources descending by actual spend
        sorted_items = sorted(
            cost_by_resource.values(),
            key=lambda x: x["actual_cost"],
            reverse=True,
        )

        ranked_items: List[ContributionRankingItem] = []
        cumulative_share = Decimal("0.00")
        pareto_80_count = 0
        pareto_threshold_reached = False

        total_items_cost = sum((item["actual_cost"] for item in sorted_items), Decimal("0.0000"))

        for idx, item in enumerate(sorted_items, start=1):
            act_cost = item["actual_cost"]
            # Excess allocation proportional to actual spend
            if total_items_cost > Decimal("0.0000") and total_excess > Decimal("0.0000"):
                res_excess = ((act_cost / total_items_cost) * total_excess).quantize(Decimal("0.0001"))
                share = ((res_excess / total_excess) * Decimal("100.00")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                res_excess = total_excess
                share = Decimal("100.00") if idx == 1 else Decimal("0.00")

            cumulative_share = min(Decimal("100.00"), cumulative_share + share)

            if not pareto_threshold_reached:
                pareto_80_count += 1
                if cumulative_share >= Decimal("80.00"):
                    pareto_threshold_reached = True

            conf_cat = (
                ConfidenceCategory.HIGH.value
                if idx <= 3
                else ConfidenceCategory.MEDIUM.value
            )

            ranked_items.append(
                ContributionRankingItem(
                    rank=idx,
                    entity_type="RESOURCE",
                    entity_id=item["resource_id"],
                    entity_name=item["resource_name"] or item["resource_id"],
                    provider=item["provider"],
                    service_name=item["service_name"],
                    excess_cost=res_excess,
                    contribution_share=share,
                    cumulative_share=cumulative_share,
                    confidence_category=conf_cat,
                )
            )

        if pareto_80_count == 0 and ranked_items:
            pareto_80_count = 1

        return ContributionRankingResponse(
            investigation_id=investigation_id,
            total_excess_cost=total_excess.quantize(Decimal("0.0001")),
            top_contributors=ranked_items[:20],
            pareto_80_count=pareto_80_count,
        )
