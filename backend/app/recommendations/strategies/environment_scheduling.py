"""
CloudSage Environment Scheduling Strategy.
Identifies non-production development and staging resources running 24x7 and advises scheduled shutdown.
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
    calculate_schedule_savings,
)
from backend.app.recommendations.scoring import compute_multi_factor_score


class EnvironmentSchedulingStrategy(BaseRecommendationStrategy):
    """Recommends automated off-hours and weekend shutdown for non-production environments."""

    @property
    def strategy_id(self) -> str:
        return "environment_scheduling_strategy"

    @property
    def strategy_name(self) -> str:
        return "Non-Production Environment Scheduling"

    @property
    def strategy_version(self) -> str:
        return "1.0"

    @property
    def category(self) -> str:
        return "SCHEDULING"

    @property
    def description(self) -> str:
        return "Schedules dev/test/staging environments to run during business hours only (50 hrs/week vs 168 hrs)."

    def evaluate(
        self,
        db: Session,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RecommendationCandidate]:
        candidates: List[RecommendationCandidate] = []
        ctx = context or {}
        provider_filter = ctx.get("provider")

        waste_query = db.query(WasteDetection).filter(
            WasteDetection.waste_type == "CONTINUOUS_NON_PROD",
            WasteDetection.status.in_(["ACTIVE", "OPEN"]),
        )
        if provider_filter and provider_filter != "ALL":
            waste_query = waste_query.filter(WasteDetection.provider == provider_filter.upper())

        waste_records: List[WasteDetection] = waste_query.all()

        for w in waste_records:
            monthly_waste = w.estimated_monthly_waste
            if monthly_waste <= Decimal("0.0000"):
                continue

            # Full 24/7 monthly cost inferred from ~70% waste
            # cost = waste / 0.7024
            current_cost = monthly_waste * Decimal("1.4237")
            monthly_savings = calculate_schedule_savings(current_cost, running_hours_per_week=50)
            annual_savings = annualize_savings(monthly_savings)
            projected_cost = current_cost - monthly_savings

            prov_enum = CloudProvider(w.provider.upper()) if w.provider.upper() in CloudProvider.__members__ else CloudProvider.AWS
            res: Optional[CloudResource] = db.query(CloudResource).filter(CloudResource.resource_id == w.resource_id).first()
            res_name = res.resource_name if res else w.resource_id

            effort = ImplementationEffort.QUICK_WIN
            risk = RiskLevel.LOW

            scoring = compute_multi_factor_score(
                monthly_savings=monthly_savings,
                confidence_score=w.confidence_score,
                effort=effort,
                risk=risk,
            )

            title = f"Schedule Business-Hours Shutdown for Non-Prod Instance ({res_name})"
            description = (
                f"Non-production instance {w.resource_id} is running 24x7 with recurring expenditure of ${current_cost:.2f}/mo. "
                f"Enabling automated nightly and weekend shutdown (50 hrs/week) avoids 118 idle hours weekly, "
                f"saving ${monthly_savings:.2f}/mo (~70% reduction)."
            )

            guidance = build_implementation_guidance(
                provider=prov_enum,
                action=RecommendationAction.SCHEDULE_SHUTDOWN,
                resource_id=w.resource_id,
                resource_name=res_name,
                parameters={"schedule": "Mon-Fri 08:00-18:00 UTC"},
            )

            savings_breakdown = build_savings_breakdown(
                current_monthly_cost=current_cost,
                projected_monthly_cost=projected_cost,
                monthly_savings=monthly_savings,
                annual_savings=annual_savings,
                formula_name="Business Hours Scheduling (50 hrs/wk out of 168 hrs)",
                parameters={
                    "business_hours_per_week": 50,
                    "total_hours_per_week": 168,
                    "reduction_fraction": "70.24%",
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
                action_type=RecommendationAction.SCHEDULE_SHUTDOWN,
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
                assumptions=["No offshore or overnight automated regression tests run on this instance."],
                evidence_summary={"waste_type": w.waste_type, "telemetry": w.telemetry_proof},
                evidence_items=[ev_link],
                tags=res.tags if res else {},
            )
            candidates.append(cand)

        return candidates
