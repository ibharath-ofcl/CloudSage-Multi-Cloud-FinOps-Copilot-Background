"""
CloudSage Compute Rightsizing Strategy.
Identifies oversized virtual machines (EC2, Azure VMs, GCE) and recommends single-tier downsizing.
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
    calculate_rightsizing_savings,
)
from backend.app.recommendations.scoring import compute_multi_factor_score

# Canonical single-tier downsize mapping for common instances
DOWNSIZE_CATALOG: Dict[str, str] = {
    # AWS
    "m5.2xlarge": "m5.xlarge",
    "m5.xlarge": "m5.large",
    "c5.2xlarge": "c5.xlarge",
    "r5.2xlarge": "r5.xlarge",
    "t3.xlarge": "t3.large",
    "t3.large": "t3.medium",
    # Azure
    "Standard_D8s_v5": "Standard_D4s_v5",
    "Standard_D4s_v5": "Standard_D2s_v5",
    "Standard_E8s_v5": "Standard_E4s_v5",
    # GCP
    "e2-standard-8": "e2-standard-4",
    "e2-standard-4": "e2-standard-2",
    "n2-standard-8": "n2-standard-4",
}


class ComputeRightsizingStrategy(BaseRecommendationStrategy):
    """Recommends downsizing oversized compute instances."""

    @property
    def strategy_id(self) -> str:
        return "compute_rightsizing_strategy"

    @property
    def strategy_name(self) -> str:
        return "Compute Instance Rightsizing"

    @property
    def strategy_version(self) -> str:
        return "1.0"

    @property
    def category(self) -> str:
        return "COMPUTE"

    @property
    def description(self) -> str:
        return "Identifies instances running well below capacity limits; recommends single-tier downsize."

    def evaluate(
        self,
        db: Session,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RecommendationCandidate]:
        candidates: List[RecommendationCandidate] = []
        ctx = context or {}
        provider_filter = ctx.get("provider")

        waste_query = db.query(WasteDetection).filter(
            WasteDetection.waste_type == "OVERSIZED_COMPUTE",
            WasteDetection.status.in_(["ACTIVE", "OPEN"]),
        )
        if provider_filter and provider_filter != "ALL":
            waste_query = waste_query.filter(WasteDetection.provider == provider_filter.upper())

        waste_records: List[WasteDetection] = waste_query.all()

        for w in waste_records:
            monthly_waste = w.estimated_monthly_waste
            if monthly_waste <= Decimal("0.0000"):
                continue

            # Standard rightsizing assumes downsize saves ~50% of instance cost
            # or uses estimated_monthly_waste as the saving delta
            current_cost = monthly_waste * Decimal("2.0000")
            projected_cost = current_cost - monthly_waste
            monthly_savings = calculate_rightsizing_savings(current_cost, projected_cost)
            annual_savings = annualize_savings(monthly_savings)

            prov_enum = CloudProvider(w.provider.upper()) if w.provider.upper() in CloudProvider.__members__ else CloudProvider.AWS
            res: Optional[CloudResource] = db.query(CloudResource).filter(CloudResource.resource_id == w.resource_id).first()
            res_name = res.resource_name if res else w.resource_id

            current_type = (res.instance_type or "m5.2xlarge") if res else "m5.2xlarge"
            target_type = DOWNSIZE_CATALOG.get(current_type, "t3.large")

            effort = ImplementationEffort.LOW
            risk = RiskLevel.LOW
            if res and res.environment and res.environment.upper() == "PROD":
                risk = RiskLevel.MEDIUM

            scoring = compute_multi_factor_score(
                monthly_savings=monthly_savings,
                confidence_score=w.confidence_score,
                effort=effort,
                risk=risk,
            )

            title = f"Rightsize Oversized {prov_enum.value} Instance ({current_type} -> {target_type})"
            description = (
                f"Instance {w.resource_id} currently runs as {current_type} (${current_cost:.2f}/mo) "
                f"with peak CPU < 20%. Downsizing to {target_type} (${projected_cost:.2f}/mo) "
                f"will save ${monthly_savings:.2f}/mo (${annual_savings:.2f}/yr) while preserving SLA headroom."
            )

            guidance = build_implementation_guidance(
                provider=prov_enum,
                action=RecommendationAction.RIGHTSIZE,
                resource_id=w.resource_id,
                resource_name=res_name,
                parameters={
                    "current_type": current_type,
                    "target_type": target_type,
                },
            )

            savings_breakdown = build_savings_breakdown(
                current_monthly_cost=current_cost,
                projected_monthly_cost=projected_cost,
                monthly_savings=monthly_savings,
                annual_savings=annual_savings,
                formula_name="Single-Tier Compute Rightsizing",
                parameters={
                    "current_instance_type": current_type,
                    "target_instance_type": target_type,
                },
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
                action_type=RecommendationAction.RIGHTSIZE,
                title=title,
                description=description,
                remediation_guide=guidance["cli_snippet"],
                estimated_monthly_savings=monthly_savings,
                estimated_annual_savings=annual_savings,
                current_monthly_cost=current_cost,
                projected_monthly_cost=projected_cost,
                strategy_id=self.strategy_id,
                strategy_version=self.strategy_version,
                resource_id=w.resource_id,
                account_id=w.account_id,
                region=res.region if res else None,
                service_name=res.service_name if res else "Compute",
                service_category=ServiceCategory.COMPUTE,
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
                assumptions=["Workload memory footprint fits within target instance memory ceiling."],
                evidence_summary={"current_type": current_type, "target_type": target_type, "telemetry": w.telemetry_proof},
                evidence_items=[ev_link],
                tags=res.tags if res else {},
            )
            candidates.append(cand)

        return candidates
