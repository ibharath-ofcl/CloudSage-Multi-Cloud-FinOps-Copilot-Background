"""
CloudSage Network Optimization Strategy.
Identifies idle public IPs, unattached load balancers, and unused gateways.
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
    calculate_idle_release_savings,
)
from backend.app.recommendations.scoring import compute_multi_factor_score


class NetworkOptimizationStrategy(BaseRecommendationStrategy):
    """Recommends releasing idle Elastic IPs and decommissioning zero-target load balancers."""

    @property
    def strategy_id(self) -> str:
        return "network_optimization_strategy"

    @property
    def strategy_name(self) -> str:
        return "Network & Elastic IP Optimization"

    @property
    def strategy_version(self) -> str:
        return "1.0"

    @property
    def category(self) -> str:
        return "NETWORKING"

    @property
    def description(self) -> str:
        return "Flags unattached static IPs and empty load balancer endpoints; advises release or deletion."

    def evaluate(
        self,
        db: Session,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RecommendationCandidate]:
        candidates: List[RecommendationCandidate] = []
        ctx = context or {}
        provider_filter = ctx.get("provider")

        net_waste_types = ["IDLE_IP", "ZERO_TARGET_LB", "UNUSED_NETWORK"]
        waste_query = db.query(WasteDetection).filter(
            WasteDetection.waste_type.in_(net_waste_types),
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

            if w.waste_type == "IDLE_IP":
                action = RecommendationAction.RELEASE_IP
                title = f"Release Unattached Elastic IP ({res_name})"
                action_desc = "Releasing unallocated public IP"
            else:
                action = RecommendationAction.TERMINATE
                title = f"Delete Empty Load Balancer ({res_name})"
                action_desc = "Decommissioning load balancer with zero registered healthy backend targets"

            monthly_savings = calculate_idle_release_savings(monthly_cost)
            annual_savings = annualize_savings(monthly_savings)

            effort = ImplementationEffort.QUICK_WIN
            risk = RiskLevel.NONE if w.waste_type == "IDLE_IP" else RiskLevel.LOW

            scoring = compute_multi_factor_score(
                monthly_savings=monthly_savings,
                confidence_score=w.confidence_score,
                effort=effort,
                risk=risk,
            )

            description = (
                f"{prov_enum.value} network resource {w.resource_id} is idle and costing ${monthly_cost:.2f}/mo. "
                f"{action_desc} will immediately recover ${monthly_savings:.2f}/mo."
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
                formula_name="100% Idle Network Resource Release",
                parameters={"target": w.waste_type},
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
                service_name=res.service_name if res else "Networking",
                service_category=ServiceCategory.NETWORKING,
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
                assumptions=["IP is not hardcoded in external client configurations."],
                evidence_summary={"waste_type": w.waste_type, "telemetry": w.telemetry_proof},
                evidence_items=[ev_link],
                tags=res.tags if res else {},
            )
            candidates.append(cand)

        return candidates
