"""
CloudSage Cost Anomaly Investigation Strategy.
Converts high-severity, active spending spikes and change points into prioritized investigation advisories.
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
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.resource import CloudResource
from backend.app.recommendations.base import BaseRecommendationStrategy
from backend.app.recommendations.evidence import create_anomaly_evidence_link
from backend.app.recommendations.guidance import build_implementation_guidance
from backend.app.recommendations.models import RecommendationCandidate
from backend.app.recommendations.savings import (
    annualize_savings,
    build_savings_breakdown,
    quantize_currency,
)
from backend.app.recommendations.scoring import compute_multi_factor_score


class AnomalyInvestigationStrategy(BaseRecommendationStrategy):
    """Recommends urgent FinOps investigation for unaddressed high-severity spending spikes."""

    @property
    def strategy_id(self) -> str:
        return "anomaly_investigation_strategy"

    @property
    def strategy_name(self) -> str:
        return "Cost Anomaly & Spike Investigation"

    @property
    def strategy_version(self) -> str:
        return "1.0"

    @property
    def category(self) -> str:
        return "ANOMALY"

    @property
    def description(self) -> str:
        return "Converts unacknowledged spending anomalies into prioritized investigation advisories."

    def evaluate(
        self,
        db: Session,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RecommendationCandidate]:
        candidates: List[RecommendationCandidate] = []
        ctx = context or {}
        provider_filter = ctx.get("provider")

        anomaly_query = db.query(CostAnomaly).filter(
            CostAnomaly.status.in_(["OPEN", "DETECTED"]),
            CostAnomaly.severity.in_(["HIGH", "CRITICAL"]),
        )
        if provider_filter and provider_filter != "ALL":
            anomaly_query = anomaly_query.filter(CostAnomaly.provider == provider_filter.upper())

        anomalies: List[CostAnomaly] = anomaly_query.all()

        for a in anomalies:
            monthly_impact = a.projected_monthly_impact
            if monthly_impact <= Decimal("0.0000"):
                monthly_impact = quantize_currency(a.absolute_deviation * Decimal("30.0"))

            monthly_savings = monthly_impact
            annual_savings = annualize_savings(monthly_savings)

            prov_enum = CloudProvider(a.provider.upper()) if a.provider.upper() in CloudProvider.__members__ else CloudProvider.AWS
            res: Optional[CloudResource] = (
                db.query(CloudResource).filter(CloudResource.resource_id == a.resource_id).first()
                if a.resource_id else None
            )
            res_name = res.resource_name if res else (a.service_name or "Service")

            effort = ImplementationEffort.LOW
            risk = RiskLevel.MEDIUM

            scoring = compute_multi_factor_score(
                monthly_savings=monthly_savings,
                confidence_score=a.confidence_score,
                effort=effort,
                risk=risk,
                urgency_boost=True,
            )

            title = f"Investigate Cost Anomaly in {prov_enum.value} {a.service_name} (+{a.spike_percentage:.1f}%)"
            description = (
                f"Statistical anomaly detected in {a.service_name} ({a.region}) on {a.anomaly_date}: "
                f"actual daily spend reached ${a.actual_cost:.2f} vs baseline ${a.expected_cost:.2f} "
                f"(+{a.spike_percentage:.1f}%, Z-Score: {a.z_score:.2f}). "
                f"If persistent, monthly unbudgeted overrun is projected at ${monthly_impact:.2f}/mo."
            )

            guidance = build_implementation_guidance(
                provider=prov_enum,
                action=RecommendationAction.INVESTIGATE_ANOMALY,
                resource_id=a.resource_id,
                resource_name=res_name,
                parameters={
                    "start_date": str(a.anomaly_date),
                    "end_date": str(a.anomaly_date),
                },
            )

            savings_breakdown = build_savings_breakdown(
                current_monthly_cost=a.actual_cost * Decimal("30.0"),
                projected_monthly_cost=a.expected_cost * Decimal("30.0"),
                monthly_savings=monthly_savings,
                annual_savings=annual_savings,
                formula_name="Projected Monthly Anomaly Excess Spend Elimination",
                parameters={
                    "z_score": str(a.z_score),
                    "spike_percentage": str(a.spike_percentage),
                    "anomaly_date": str(a.anomaly_date),
                },
            )

            ev_link = create_anomaly_evidence_link(
                anomaly_id=a.id,
                category=a.anomaly_category,
                actual_cost=a.actual_cost,
                expected_cost=a.expected_cost,
                spike_pct=a.spike_percentage,
                confidence_score=a.confidence_score,
                resource_id=a.resource_id,
                billing_record_ids=a.source_billing_references or [],
            )

            cat_enum = None
            try:
                cat_enum = ServiceCategory(a.service_category.upper())
            except Exception:
                cat_enum = ServiceCategory.COMPUTE

            cand = RecommendationCandidate(
                provider=prov_enum,
                action_type=RecommendationAction.INVESTIGATE_ANOMALY,
                title=title,
                description=description,
                remediation_guide=guidance["cli_snippet"],
                estimated_monthly_savings=monthly_savings,
                estimated_annual_savings=annual_savings,
                current_monthly_cost=a.actual_cost * Decimal("30.0"),
                projected_monthly_cost=a.expected_cost * Decimal("30.0"),
                strategy_id=self.strategy_id,
                strategy_version=self.strategy_version,
                resource_id=a.resource_id,
                account_id=a.account_id,
                region=a.region,
                service_name=a.service_name,
                service_category=cat_enum,
                resource_name=res_name,
                priority=scoring.priority_tier,
                priority_score=scoring.composite_priority_score,
                risk_level=scoring.risk_level,
                risk_score=scoring.risk_score,
                confidence_score=a.confidence_score,
                implementation_effort=scoring.effort_level,
                anomaly_id=a.id,
                savings_calculation=savings_breakdown,
                implementation_guidance=guidance,
                assumptions=["Cost surge is an unintended regression or configuration drift."],
                evidence_summary={
                    "anomaly_category": a.anomaly_category,
                    "z_score": str(a.z_score),
                    "root_cause": a.root_cause_analysis,
                },
                evidence_items=[ev_link],
                tags=res.tags if res else {},
            )
            candidates.append(cand)

        return candidates
