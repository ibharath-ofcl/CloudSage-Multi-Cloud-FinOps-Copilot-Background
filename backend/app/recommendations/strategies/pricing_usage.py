"""
CloudSage Pricing Model & Commitment Strategy.
Identifies stable, baseline on-demand compute/database workloads and recommends Savings Plans or Reserved Instances.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.enums import (
    CloudProvider,
    ImplementationEffort,
    Priority,
    RecommendationAction,
    RiskLevel,
    ServiceCategory,
)
from backend.app.models.billing import BillingRecord
from backend.app.recommendations.base import BaseRecommendationStrategy
from backend.app.recommendations.guidance import build_implementation_guidance
from backend.app.recommendations.models import EvidenceLink, RecommendationCandidate
from backend.app.recommendations.savings import (
    annualize_savings,
    build_savings_breakdown,
    calculate_commitment_savings,
    quantize_currency,
)
from backend.app.recommendations.scoring import compute_multi_factor_score


class PricingUsageStrategy(BaseRecommendationStrategy):
    """Recommends purchasing Savings Plans or Reserved Capacity for steady baseline workloads."""

    @property
    def strategy_id(self) -> str:
        return "pricing_usage_strategy"

    @property
    def strategy_name(self) -> str:
        return "Commitment Discounts & Savings Plans"

    @property
    def strategy_version(self) -> str:
        return "1.0"

    @property
    def category(self) -> str:
        return "PRICING"

    @property
    def description(self) -> str:
        return "Simulates 1-year / 3-year commitment discount models for stable on-demand compute expenditure."

    def evaluate(
        self,
        db: Session,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RecommendationCandidate]:
        candidates: List[RecommendationCandidate] = []
        ctx = context or {}
        provider_filter = ctx.get("provider")

        # Aggregate total on-demand spending per provider and account
        query = (
            db.query(
                BillingRecord.provider,
                BillingRecord.billing_account_id,
                BillingRecord.service_name,
                func.sum(BillingRecord.unblended_cost).label("total_spend"),
            )
            .filter(BillingRecord.pricing_model == "ON_DEMAND")
            .group_by(
                BillingRecord.provider,
                BillingRecord.billing_account_id,
                BillingRecord.service_name,
            )
        )
        if provider_filter and provider_filter != "ALL":
            query = query.filter(BillingRecord.provider == provider_filter.upper())

        rows = query.all()

        for r in rows:
            spend = quantize_currency(Decimal(str(r.total_spend or "0.0000")))
            # Only recommend commitments if monthly baseline spend > $500
            if spend < Decimal("500.0000"):
                continue

            # Standard 30% discount on commitment
            discount_rate = Decimal("0.3000")
            monthly_savings = calculate_commitment_savings(spend, discount_rate)
            annual_savings = annualize_savings(monthly_savings)
            projected_cost = spend - monthly_savings

            prov_str = str(r.provider).upper()
            prov_enum = CloudProvider(prov_str) if prov_str in CloudProvider.__members__ else CloudProvider.AWS

            if prov_enum == CloudProvider.AWS:
                action = RecommendationAction.PURCHASE_SAVINGS_PLAN
                model_name = "Compute Savings Plan (1-Year All Upfront)"
            elif prov_enum == CloudProvider.AZURE:
                action = RecommendationAction.RESERVE_CAPACITY
                model_name = "Azure Reserved VM Instances (1-Year)"
            else:
                action = RecommendationAction.RESERVE_CAPACITY
                model_name = "GCP Committed Use Discounts (1-Year CUD)"

            effort = ImplementationEffort.LOW
            risk = RiskLevel.LOW

            scoring = compute_multi_factor_score(
                monthly_savings=monthly_savings,
                confidence_score=Decimal("0.9000"),
                effort=effort,
                risk=risk,
            )

            title = f"Acquire {model_name} for {prov_enum.value} {r.service_name}"
            description = (
                f"Account {r.billing_account_id} has sustained ${spend:.2f}/mo in on-demand "
                f"{r.service_name} spend. Committing to a 1-year term reduces effective hourly rates by 30%, "
                f"yielding projected savings of ${monthly_savings:.2f}/mo (${annual_savings:.2f}/yr)."
            )

            guidance = build_implementation_guidance(
                provider=prov_enum,
                action=action,
                resource_id=None,
                parameters={"service": r.service_name, "model": model_name},
            )

            savings_breakdown = build_savings_breakdown(
                current_monthly_cost=spend,
                projected_monthly_cost=projected_cost,
                monthly_savings=monthly_savings,
                annual_savings=annual_savings,
                formula_name="Commitment Discount Plan (30% Net Reduction)",
                parameters={
                    "discount_rate": "30%",
                    "commitment_term": "1-Year",
                    "pricing_model": model_name,
                },
            )

            ev_link = EvidenceLink(
                evidence_type="BILLING_RECORD",
                description=f"Aggregated on-demand billing spend of ${spend:.2f} for {r.service_name}.",
                telemetry_data={"monthly_baseline_spend": str(spend), "service_name": r.service_name},
                confidence_score=Decimal("0.9000"),
            )

            cand = RecommendationCandidate(
                provider=prov_enum,
                action_type=action,
                title=title,
                description=description,
                remediation_guide=guidance["cli_snippet"],
                estimated_monthly_savings=monthly_savings,
                estimated_annual_savings=annual_savings,
                current_monthly_cost=spend,
                projected_monthly_cost=projected_cost,
                strategy_id=self.strategy_id,
                strategy_version=self.strategy_version,
                resource_id=None,
                account_id=r.billing_account_id,
                service_name=r.service_name,
                service_category=ServiceCategory.COMPUTE,
                priority=scoring.priority_tier,
                priority_score=scoring.composite_priority_score,
                risk_level=scoring.risk_level,
                risk_score=scoring.risk_score,
                confidence_score=Decimal("0.9000"),
                implementation_effort=scoring.effort_level,
                savings_calculation=savings_breakdown,
                implementation_guidance=guidance,
                assumptions=["Workload capacity demand remains steady over the 12-month commitment horizon."],
                evidence_summary={"monthly_spend": str(spend), "service_name": r.service_name},
                evidence_items=[ev_link],
            )
            candidates.append(cand)

        return candidates
