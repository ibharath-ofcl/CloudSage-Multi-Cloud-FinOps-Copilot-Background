"""
CloudSage Database Optimization Strategy.
Identifies underutilized managed databases (RDS, Cloud SQL, CosmosDB, Azure SQL) and recommends rightsizing or pausing.
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


class DatabaseOptimizationStrategy(BaseRecommendationStrategy):
    """Recommends rightsizing or pausing underutilized relational/NoSQL databases."""

    @property
    def strategy_id(self) -> str:
        return "database_optimization_strategy"

    @property
    def strategy_name(self) -> str:
        return "Database Rightsizing & Tier Optimization"

    @property
    def strategy_version(self) -> str:
        return "1.0"

    @property
    def category(self) -> str:
        return "DATABASE"

    @property
    def description(self) -> str:
        return "Analyzes DB connection counts and IOPS to recommend instance downsizing or auto-pause."

    def evaluate(
        self,
        db: Session,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RecommendationCandidate]:
        candidates: List[RecommendationCandidate] = []
        ctx = context or {}
        provider_filter = ctx.get("provider")

        waste_query = db.query(WasteDetection).filter(
            WasteDetection.waste_type == "UNDERUTILIZED_DATABASE",
            WasteDetection.status.in_(["ACTIVE", "OPEN"]),
        )
        if provider_filter and provider_filter != "ALL":
            waste_query = waste_query.filter(WasteDetection.provider == provider_filter.upper())

        waste_records: List[WasteDetection] = waste_query.all()

        for w in waste_records:
            monthly_waste = w.estimated_monthly_waste
            if monthly_waste <= Decimal("0.0000"):
                continue

            current_cost = monthly_waste * Decimal("2.0000")
            projected_cost = current_cost - monthly_waste
            monthly_savings = calculate_rightsizing_savings(current_cost, projected_cost)
            annual_savings = annualize_savings(monthly_savings)

            prov_enum = CloudProvider(w.provider.upper()) if w.provider.upper() in CloudProvider.__members__ else CloudProvider.AWS
            res: Optional[CloudResource] = db.query(CloudResource).filter(CloudResource.resource_id == w.resource_id).first()
            res_name = res.resource_name if res else w.resource_id

            effort = ImplementationEffort.MEDIUM
            risk = RiskLevel.MEDIUM if (res and res.environment and res.environment.upper() == "PROD") else RiskLevel.LOW

            scoring = compute_multi_factor_score(
                monthly_savings=monthly_savings,
                confidence_score=w.confidence_score,
                effort=effort,
                risk=risk,
            )

            title = f"Rightsize Underutilized {prov_enum.value} Database ({res_name})"
            description = (
                f"Database {w.resource_id} is running with active connections < 5 and CPU < 10%. "
                f"Downsizing database tier reduces expenditure by ${monthly_savings:.2f}/mo "
                f"(${annual_savings:.2f}/yr) while preserving data redundancy and automated backups."
            )

            guidance = build_implementation_guidance(
                provider=prov_enum,
                action=RecommendationAction.RIGHTSIZE,
                resource_id=w.resource_id,
                resource_name=res_name,
                parameters={"service": "Database"},
            )

            savings_breakdown = build_savings_breakdown(
                current_monthly_cost=current_cost,
                projected_monthly_cost=projected_cost,
                monthly_savings=monthly_savings,
                annual_savings=annual_savings,
                formula_name="Database Tier Rightsizing",
                parameters={"reduction_ratio": "50%"},
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
                service_name=res.service_name if res else "Database",
                service_category=ServiceCategory.DATABASE,
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
                assumptions=["Workload IOPS does not spike during maintenance windows."],
                evidence_summary={"waste_type": w.waste_type, "telemetry": w.telemetry_proof},
                evidence_items=[ev_link],
                tags=res.tags if res else {},
            )
            candidates.append(cand)

        return candidates
