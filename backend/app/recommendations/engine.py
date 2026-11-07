"""
CloudSage Recommendation Engine.
Orchestrates multi-cloud strategy execution, candidate consolidation, anti-double-counting,
PostgreSQL persistence, and execution run audit logging.
Strictly non-destructive and advisory-only.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.enums import CloudProvider, RecommendationAction, RecommendationStatus
from backend.app.models.recommendation import (
    Recommendation,
    RecommendationEvidence,
    RecommendationHistory,
    RecommendationRun,
)
from backend.app.recommendations.correlation import filter_and_consolidate_candidates, generate_recommendation_key
from backend.app.recommendations.models import RecommendationCandidate
from backend.app.recommendations.registry import RecommendationRegistry
from backend.app.recommendations.savings import annualize_savings, quantize_currency
from backend.app.recommendations.strategies import register_all_strategies


class RecommendationEngine:
    """Core advisory optimization recommendation engine."""

    def __init__(self) -> None:
        # Ensure strategies are registered
        if len(RecommendationRegistry.list_strategies()) == 0:
            register_all_strategies()

    def execute_run(
        self,
        db: Session,
        provider: Optional[str] = "ALL",
        strategies: Optional[List[str]] = None,
        account_id: Optional[str] = None,
        service_name: Optional[str] = None,
        scope: str = "FULL",
    ) -> RecommendationRun:
        """
        Executes a complete recommendation generation run.
        Collects candidates, enforces anti-double-counting, upserts recommendations,
        links evidence, and writes run audit logs.
        """
        now = datetime.now(timezone.utc)
        effective_provider = provider.upper() if provider else "ALL"

        run = RecommendationRun(
            run_id=uuid.uuid4(),
            provider=effective_provider,
            scope=scope,
            status="RUNNING",
            started_at=now,
            strategy_summary={},
            error_details=[],
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # 1. Select Active Strategies
        all_strats = RecommendationRegistry.list_strategies()
        if strategies:
            strat_ids = set(strategies)
            active_strategies = [s for s in all_strats if s.strategy_id in strat_ids]
        else:
            active_strategies = all_strats

        context: Dict[str, Any] = {
            "provider": effective_provider,
            "account_id": account_id,
            "service_name": service_name,
        }

        all_candidates: List[RecommendationCandidate] = []
        strategy_stats: Dict[str, int] = {}
        errors: List[Dict[str, Any]] = []

        # 2. Execute Each Strategy
        for strat in active_strategies:
            try:
                cands = strat.evaluate(db, context=context)
                strategy_stats[strat.strategy_id] = len(cands)
                all_candidates.extend(cands)
            except Exception as e:
                strategy_stats[strat.strategy_id] = 0
                errors.append({
                    "strategy_id": strat.strategy_id,
                    "error": str(e),
                })

        # 3. Consolidate and apply anti-double-counting
        active_candidates, suppressed_records = filter_and_consolidate_candidates(all_candidates)

        created_count = 0
        updated_count = 0
        unchanged_count = 0
        total_monthly = Decimal("0.0000")
        total_annual = Decimal("0.0000")

        # 4. Upsert into database
        for cand in active_candidates:
            existing: Optional[Recommendation] = (
                db.query(Recommendation)
                .filter(Recommendation.recommendation_key == cand.recommendation_key)
                .first()
            )

            if existing:
                # Update financial projections and refreshed telemetry
                existing.estimated_monthly_savings = cand.estimated_monthly_savings
                existing.estimated_annual_savings = cand.estimated_annual_savings
                existing.current_monthly_cost = cand.current_monthly_cost
                existing.projected_monthly_cost = cand.projected_monthly_cost
                existing.priority_score = cand.priority_score
                existing.risk_score = cand.risk_score
                existing.confidence_score = cand.confidence_score
                existing.priority = cand.priority.value
                existing.risk_level = cand.risk_level.value
                existing.savings_calculation = cand.savings_calculation
                existing.implementation_guidance = cand.implementation_guidance
                existing.assumptions = cand.assumptions
                existing.evidence_summary = cand.evidence_summary
                existing.updated_at = now

                # If in PROPOSED/NEW, ensure latest title and descriptions
                if existing.status in ("PROPOSED", "NEW"):
                    existing.title = cand.title
                    existing.description = cand.description
                    existing.remediation_guide = cand.remediation_guide

                updated_count += 1
                total_monthly += cand.estimated_monthly_savings
                total_annual += cand.estimated_annual_savings

            else:
                new_rec = Recommendation(
                    id=uuid.uuid4(),
                    recommendation_key=cand.recommendation_key,
                    waste_detection_id=cand.waste_detection_id,
                    resource_id=cand.resource_id,
                    provider=cand.provider.value,
                    account_id=cand.account_id,
                    region=cand.region,
                    service_name=cand.service_name,
                    service_category=cand.service_category.value if cand.service_category else None,
                    resource_name=cand.resource_name,
                    strategy_id=cand.strategy_id,
                    strategy_version=cand.strategy_version,
                    action_type=cand.action_type.value,
                    priority=cand.priority.value,
                    priority_score=cand.priority_score,
                    risk_level=cand.risk_level.value,
                    risk_score=cand.risk_score,
                    confidence_score=cand.confidence_score,
                    status=RecommendationStatus.PROPOSED.value,
                    current_monthly_cost=cand.current_monthly_cost,
                    projected_monthly_cost=cand.projected_monthly_cost,
                    estimated_monthly_savings=cand.estimated_monthly_savings,
                    estimated_annual_savings=cand.estimated_annual_savings,
                    currency=cand.currency,
                    implementation_effort=cand.implementation_effort.value,
                    title=cand.title,
                    description=cand.description,
                    remediation_guide=cand.remediation_guide,
                    savings_calculation=cand.savings_calculation,
                    implementation_guidance=cand.implementation_guidance,
                    assumptions=cand.assumptions,
                    evidence_summary=cand.evidence_summary,
                    tags=cand.tags,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_rec)
                db.flush()

                # Add Evidence Items
                for ev in cand.evidence_items:
                    ev_record = RecommendationEvidence(
                        id=uuid.uuid4(),
                        recommendation_id=new_rec.id,
                        evidence_type=ev.evidence_type,
                        waste_detection_id=ev.waste_detection_id,
                        anomaly_id=ev.anomaly_id,
                        resource_id=ev.resource_id or cand.resource_id,
                        description=ev.description,
                        telemetry_data=ev.telemetry_data,
                        billing_record_ids=ev.billing_record_ids,
                        confidence_score=ev.confidence_score,
                        created_at=now,
                    )
                    db.add(ev_record)

                # Add initial History entry
                hist_record = RecommendationHistory(
                    id=uuid.uuid4(),
                    recommendation_id=new_rec.id,
                    from_status=None,
                    to_status="PROPOSED",
                    actor="RecommendationEngine",
                    action="PROPOSAL_CREATED",
                    notes=f"Generated by strategy {cand.strategy_id} v{cand.strategy_version}",
                    details={"estimated_monthly_savings": str(cand.estimated_monthly_savings)},
                    created_at=now,
                )
                db.add(hist_record)

                created_count += 1
                total_monthly += cand.estimated_monthly_savings
                total_annual += cand.estimated_annual_savings

        # 5. Finalize Run Audit Record
        run.status = "COMPLETED" if not errors else ("PARTIAL_SUCCESS" if created_count > 0 or updated_count > 0 else "FAILED")
        run.total_evaluated = len(all_candidates)
        run.recommendations_created = created_count
        run.recommendations_updated = updated_count
        run.recommendations_unchanged = unchanged_count
        run.recommendations_suppressed = len(suppressed_records)
        run.total_monthly_savings = quantize_currency(total_monthly)
        run.total_annual_savings = quantize_currency(total_annual)
        run.strategy_summary = strategy_stats
        run.error_details = errors + suppressed_records
        run.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(run)
        return run

    @classmethod
    def get_summary(cls, db: Session) -> Dict[str, Any]:
        """Calculates multi-cloud executive summary KPIs."""
        recs = db.query(Recommendation).all()

        total_count = len(recs)
        total_monthly = sum((r.estimated_monthly_savings for r in recs), Decimal("0.0000"))
        total_annual = sum((r.estimated_annual_savings for r in recs), Decimal("0.0000"))

        by_provider: Dict[str, Dict[str, Any]] = {
            "AWS": {"count": 0, "monthly_savings": Decimal("0.0000")},
            "AZURE": {"count": 0, "monthly_savings": Decimal("0.0000")},
            "GCP": {"count": 0, "monthly_savings": Decimal("0.0000")},
        }
        by_priority: Dict[str, int] = {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
        by_status: Dict[str, int] = {}
        by_effort: Dict[str, int] = {}
        by_risk: Dict[str, int] = {}
        by_action: Dict[str, Dict[str, Any]] = {}

        for r in recs:
            p = r.provider.upper()
            if p in by_provider:
                by_provider[p]["count"] += 1
                by_provider[p]["monthly_savings"] += r.estimated_monthly_savings

            by_priority[r.priority] = by_priority.get(r.priority, 0) + 1
            by_status[r.status] = by_status.get(r.status, 0) + 1
            by_effort[r.implementation_effort] = by_effort.get(r.implementation_effort, 0) + 1
            by_risk[r.risk_level] = by_risk.get(r.risk_level, 0) + 1

            act = r.action_type
            if act not in by_action:
                by_action[act] = {"action_type": act, "count": 0, "monthly_savings": Decimal("0.0000")}
            by_action[act]["count"] += 1
            by_action[act]["monthly_savings"] += r.estimated_monthly_savings

        # Convert Decimals in by_provider for serialization
        prov_summary = {
            k: {
                "count": v["count"],
                "monthly_savings": quantize_currency(v["monthly_savings"]),
                "annual_savings": quantize_currency(v["monthly_savings"] * Decimal("12")),
            }
            for k, v in by_provider.items()
        }

        top_cats = sorted(
            [
                {
                    "action_type": v["action_type"],
                    "count": v["count"],
                    "monthly_savings": quantize_currency(v["monthly_savings"]),
                    "annual_savings": quantize_currency(v["monthly_savings"] * Decimal("12")),
                }
                for v in by_action.values()
            ],
            key=lambda x: x["monthly_savings"],
            reverse=True,
        )

        return {
            "total_recommendations": total_count,
            "total_monthly_savings": quantize_currency(total_monthly),
            "total_annual_savings": quantize_currency(total_annual),
            "by_provider": prov_summary,
            "by_priority": by_priority,
            "by_status": by_status,
            "by_effort": by_effort,
            "by_risk": by_risk,
            "top_categories": top_cats,
        }

    @classmethod
    def get_financial_impact(cls, db: Session) -> Dict[str, Any]:
        """Calculates realized vs unrealized savings and realization rates."""
        recs = db.query(Recommendation).all()

        total_identified_monthly = sum((r.estimated_monthly_savings for r in recs), Decimal("0.0000"))
        total_identified_annual = sum((r.estimated_annual_savings for r in recs), Decimal("0.0000"))

        realized_recs = [r for r in recs if r.status in ("IMPLEMENTED", "VERIFIED")]
        total_realized_monthly = sum(
            ((r.verified_savings if r.verified_savings is not None else r.estimated_monthly_savings) for r in realized_recs),
            Decimal("0.0000"),
        )
        total_realized_annual = total_realized_monthly * Decimal("12")

        realization_rate = Decimal("0.00")
        if total_identified_monthly > Decimal("0.0000"):
            realization_rate = ((total_realized_monthly / total_identified_monthly) * Decimal("100.0")).quantize(Decimal("0.01"))

        by_prov: Dict[str, Decimal] = {}
        by_svc: Dict[str, Decimal] = {}

        for r in recs:
            p = r.provider.upper()
            by_prov[p] = by_prov.get(p, Decimal("0.0000")) + r.estimated_monthly_savings

            svc = r.service_name or "General"
            by_svc[svc] = by_svc.get(svc, Decimal("0.0000")) + r.estimated_monthly_savings

        return {
            "total_identified_monthly_savings": quantize_currency(total_identified_monthly),
            "total_identified_annual_savings": quantize_currency(total_identified_annual),
            "total_realized_monthly_savings": quantize_currency(total_realized_monthly),
            "total_realized_annual_savings": quantize_currency(total_realized_annual),
            "realization_rate_pct": realization_rate,
            "savings_by_provider": {k: quantize_currency(v) for k, v in by_prov.items()},
            "savings_by_service": {k: quantize_currency(v) for k, v in by_svc.items()},
        }


def get_recommendation_engine() -> RecommendationEngine:
    """Returns RecommendationEngine instance."""
    return RecommendationEngine()

