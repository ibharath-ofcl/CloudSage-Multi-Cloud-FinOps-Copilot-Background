"""
CloudSage Idle Compute Optimization Strategy.
Identifies idle compute instances (EC2, Azure VMs, GCE) and recommends decommissioning or termination.
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
    calculate_termination_savings,
)
from backend.app.recommendations.scoring import compute_multi_factor_score


class IdleComputeStrategy(BaseRecommendationStrategy):
    """Recommends terminating or stopping idle compute resources."""

    @property
    def strategy_id(self) -> str:
        return "idle_compute_strategy"

    @property
    def strategy_name(self) -> str:
        return "Idle Compute Decommissioning"

    @property
    def strategy_version(self) -> str:
        return "1.0"

    @property
    def category(self) -> str:
        return "COMPUTE"

    @property
    def description(self) -> str:
        return "Detects virtual machines running with sub-5% CPU and near-zero network I/O; advises termination."

    def evaluate(
        self,
        db: Session,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RecommendationCandidate]:
        candidates: List[RecommendationCandidate] = []
        ctx = context or {}
        provider_filter = ctx.get("provider")

        # 1. Query active waste detections of type IDLE_VM or IDLE_COMPUTE
        waste_query = db.query(WasteDetection).filter(
            WasteDetection.waste_type.in_(["IDLE_VM", "IDLE_COMPUTE"]),
            WasteDetection.status.in_(["ACTIVE", "OPEN"]),
        )
        if provider_filter and provider_filter != "ALL":
            waste_query = waste_query.filter(WasteDetection.provider == provider_filter.upper())

        waste_records: List[WasteDetection] = waste_query.all()

        for w in waste_records:
            monthly_cost = w.estimated_monthly_waste
            if monthly_cost <= Decimal("0.0000"):
                continue

            monthly_savings = calculate_termination_savings(monthly_cost)
            annual_savings = annualize_savings(monthly_savings)

            prov_enum = CloudProvider(w.provider.upper()) if w.provider.upper() in CloudProvider.__members__ else CloudProvider.AWS
            res: Optional[CloudResource] = db.query(CloudResource).filter(CloudResource.resource_id == w.resource_id).first()
            res_name = res.resource_name if res else (w.resource_id.split("/")[-1] if "/" in w.resource_id else w.resource_id)

            # Determine effort & risk
            effort = ImplementationEffort.LOW
            risk = RiskLevel.LOW
            is_prod = res.environment.upper() == "PROD" if (res and res.environment) else False
            if is_prod:
                risk = RiskLevel.MEDIUM

            scoring = compute_multi_factor_score(
                monthly_savings=monthly_savings,
                confidence_score=w.confidence_score,
                effort=effort,
                risk=risk,
                urgency_boost=False,
            )

            title = f"Terminate Idle {prov_enum.value} Instance ({res_name})"
            description = (
                f"{prov_enum.value} compute instance {w.resource_id} is consuming ${monthly_cost:.2f}/mo "
                f"while exhibiting sub-5% CPU utilization over the past observation period. "
                f"Decommissioning will save ${monthly_savings:.2f}/month."
            )

            guidance = build_implementation_guidance(
                provider=prov_enum,
                action=RecommendationAction.TERMINATE,
                resource_id=w.resource_id,
                resource_name=res_name,
                parameters={"target_tier": "TERMINATED"},
            )

            savings_breakdown = build_savings_breakdown(
                current_monthly_cost=monthly_cost,
                projected_monthly_cost=Decimal("0.0000"),
                monthly_savings=monthly_savings,
                annual_savings=annual_savings,
                formula_name="100% Resource Decommissioning",
                parameters={"elimination_rate": "100%"},
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
                action_type=RecommendationAction.TERMINATE,
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
                assumptions=["Instance is not serving scheduled batch or failover workloads."],
                evidence_summary={"waste_type": w.waste_type, "telemetry": w.telemetry_proof},
                evidence_items=[ev_link],
                tags=res.tags if res else {},
            )
            candidates.append(cand)

        return candidates
