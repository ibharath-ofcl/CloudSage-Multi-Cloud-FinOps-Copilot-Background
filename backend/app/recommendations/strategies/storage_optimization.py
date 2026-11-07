"""
CloudSage Storage Optimization Strategy.
Identifies unattached block disks, orphaned snapshots, and cold tier storage opportunities.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.core.enums import (
    CloudProvider,
    ImplementationEffort,
    Priority,
    RecommendationAction,
    RiskLevel,
    ServiceCategory,
)
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection
from backend.app.recommendations.base import BaseRecommendationStrategy
from backend.app.recommendations.evidence import create_waste_evidence_link
from backend.app.recommendations.guidance import build_implementation_guidance
from backend.app.recommendations.models import RecommendationCandidate
from backend.app.recommendations.savings import (
    annualize_savings,
    build_savings_breakdown,
    calculate_storage_tier_savings,
    calculate_termination_savings,
)
from backend.app.recommendations.scoring import compute_multi_factor_score


class StorageOptimizationStrategy(BaseRecommendationStrategy):
    """Recommends cleaning up unattached storage volumes, snapshots, or lifecycle tiering."""

    @property
    def strategy_id(self) -> str:
        return "storage_optimization_strategy"

    @property
    def strategy_name(self) -> str:
        return "Storage & Snapshot Optimization"

    @property
    def strategy_version(self) -> str:
        return "1.0"

    @property
    def category(self) -> str:
        return "STORAGE"

    @property
    def description(self) -> str:
        return "Detects unattached volumes, orphaned snapshots, and cold storage transition candidates."

    def evaluate(
        self,
        db: Session,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RecommendationCandidate]:
        candidates: List[RecommendationCandidate] = []
        ctx = context or {}
        provider_filter = ctx.get("provider")

        waste_types = ["UNATTACHED_DISK", "UNATTACHED_STORAGE", "ORPHANED_SNAPSHOT"]
        waste_query = db.query(WasteDetection).filter(
            WasteDetection.waste_type.in_(waste_types),
            WasteDetection.status.in_(["ACTIVE", "OPEN"]),
        )
        if provider_filter and provider_filter != "ALL":
            waste_query = waste_query.filter(WasteDetection.provider == provider_filter.upper())

        waste_records: List[WasteDetection] = waste_query.all()

        for w in waste_records:
            monthly_cost = w.estimated_monthly_waste
            if monthly_cost <= Decimal("0.0000"):
                continue

            prov_enum = CloudProvider(w.provider.upper()) if w.provider.upper() in CloudProvider.__members__ else CloudProvider.AWS
            res: Optional[CloudResource] = db.query(CloudResource).filter(CloudResource.resource_id == w.resource_id).first()
            res_name = res.resource_name if res else w.resource_id

            if w.waste_type == "ORPHANED_SNAPSHOT":
                action = RecommendationAction.DELETE_SNAPSHOT
                title = f"Delete Orphaned Snapshot ({res_name})"
                action_desc = "Deleting orphaned snapshot with no associated active volume"
                formula = "100% Snapshot Deletion"
            else:
                action = RecommendationAction.CLEANUP_UNATTACHED
                title = f"Delete Unattached Storage Volume ({res_name})"
                action_desc = "Decommissioning unattached block volume"
                formula = "100% Unattached Storage Deletion"

            monthly_savings = calculate_termination_savings(monthly_cost)
            annual_savings = annualize_savings(monthly_savings)

            effort = ImplementationEffort.QUICK_WIN
            risk = RiskLevel.NONE if w.waste_type == "ORPHANED_SNAPSHOT" else RiskLevel.LOW

            scoring = compute_multi_factor_score(
                monthly_savings=monthly_savings,
                confidence_score=w.confidence_score,
                effort=effort,
                risk=risk,
            )

            description = (
                f"{prov_enum.value} asset {w.resource_id} is unattached and incurring ${monthly_cost:.2f}/mo. "
                f"{action_desc} will immediately save ${monthly_savings:.2f}/mo without production impact."
            )

            guidance = build_implementation_guidance(
                provider=prov_enum,
                action=action,
                resource_id=w.resource_id,
                resource_name=res_name,
            )

            savings_breakdown = build_savings_breakdown(
                current_monthly_cost=monthly_cost,
                projected_monthly_cost=Decimal("0.0000"),
                monthly_savings=monthly_savings,
                annual_savings=annual_savings,
                formula_name=formula,
                parameters={"recovery_snapshot": "recommended"},
            )

            ev_link = create_waste_evidence_link(
                waste_id=w.id,
                waste_type=w.waste_type,
                telemetry=w.telemetry_proof or {},
                monthly_waste=w.estimated_monthly_waste,
                confidence_score=w.confidence_score,
                resource_id=w.resource_id,
            )

            cand = RecommendationCandidate(
                provider=prov_enum,
                action_type=action,
                title=title,
                description=description,
                remediation_guide=guidance["cli_snippet"],
                estimated_monthly_savings=monthly_savings,
                estimated_annual_savings=annual_savings,
                current_monthly_cost=monthly_cost,
                projected_monthly_cost=Decimal("0.0000"),
                strategy_id=self.strategy_id,
                strategy_version=self.strategy_version,
                resource_id=w.resource_id,
                account_id=w.account_id,
                region=res.region if res else None,
                service_name=res.service_name if res else "Storage",
                service_category=ServiceCategory.STORAGE,
                resource_name=res_name,
                priority=scoring.priority_tier,
                priority_score=scoring.composite_priority_score,
                risk_level=scoring.risk_level,
                risk_score=scoring.risk_score,
                confidence_score=w.confidence_score,
                implementation_effort=scoring.effort_level,
                waste_detection_id=w.id,
                savings_calculation=savings_breakdown,
                implementation_guidance=guidance,
                assumptions=["Volume contains no compliance or historical archive data required by policy."],
                evidence_summary={"waste_type": w.waste_type, "telemetry": w.telemetry_proof},
                evidence_items=[ev_link],
                tags=res.tags if res else {},
            )
            candidates.append(cand)

        return candidates
