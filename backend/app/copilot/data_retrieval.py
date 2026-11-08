"""
Safe Analytical Data Retrieval Engine for CloudSage AI FinOps Copilot.
Executes allowlisted query plans across Stages 3–8 canonical database models:
BillingRecord, CloudResource, WasteDetection, CostAnomaly, and Recommendation.
Enforces the Zero Float Rule: all monetary numbers use Python Decimal.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.copilot.query_planner import QueryPlan
from backend.app.core.enums import CopilotIntent
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection


class DataRetrievalEngine:
    """Executes safe, parameterized queries on underlying FinOps models."""

    @classmethod
    def execute(cls, db: Session, plan: QueryPlan) -> Dict[str, Any]:
        """
        Executes the query plan against the SQLAlchemy session.
        Returns aggregated summary, breakdown buckets, and sample records for evidence citation.
        """
        if plan.target_dataset == "billing_records":
            return cls._retrieve_billing(db, plan)
        elif plan.target_dataset == "cost_anomalies":
            return cls._retrieve_anomalies(db, plan)
        elif plan.target_dataset == "waste_detections":
            return cls._retrieve_waste(db, plan)
        elif plan.target_dataset == "recommendations":
            return cls._retrieve_recommendations(db, plan)
        elif plan.target_dataset == "cloud_resources":
            return cls._retrieve_resources(db, plan)
        else:
            return {
                "total_metric": Decimal("0.0000"),
                "record_count": 0,
                "breakdown": [],
                "sample_records": [],
            }

    @classmethod
    def _retrieve_billing(cls, db: Session, plan: QueryPlan) -> Dict[str, Any]:
        """Queries normalized FOCUS billing records."""
        stmt = select(
            func.coalesce(func.sum(BillingRecord.unblended_cost), 0),
            func.count(BillingRecord.record_id),
        )

        filters = []
        if "provider" in plan.filters:
            prov = plan.filters["provider"]
            if isinstance(prov, list):
                filters.append(BillingRecord.provider.in_(prov))
            else:
                filters.append(BillingRecord.provider == prov)

        if "service_name" in plan.filters:
            svc = plan.filters["service_name"]
            if isinstance(svc, list):
                filters.append(BillingRecord.service_name.in_(svc))
            else:
                filters.append(BillingRecord.service_name == svc)

        if "resource_id" in plan.filters:
            filters.append(BillingRecord.resource_id == plan.filters["resource_id"])

        if filters:
            stmt = stmt.where(*filters)

        total_cost_raw, record_count = db.execute(stmt).one()
        total_cost = Decimal(str(total_cost_raw or 0)).quantize(Decimal("0.0001"))

        # Breakdown query if grouped
        breakdown: List[Dict[str, Any]] = []
        if plan.group_by:
            group_col_name = plan.group_by[0]
            if hasattr(BillingRecord, group_col_name):
                col = getattr(BillingRecord, group_col_name)
                grp_stmt = (
                    select(
                        col,
                        func.coalesce(func.sum(BillingRecord.unblended_cost), 0),
                        func.count(BillingRecord.record_id),
                    )
                    .group_by(col)
                    .order_by(func.sum(BillingRecord.unblended_cost).desc())
                    .limit(plan.limit)
                )
                if filters:
                    grp_stmt = grp_stmt.where(*filters)

                for item_name, item_cost, item_cnt in db.execute(grp_stmt).all():
                    breakdown.append({
                        "dimension": str(item_name or "Unknown"),
                        "cost": Decimal(str(item_cost or 0)).quantize(Decimal("0.0001")),
                        "count": int(item_cnt or 0),
                    })

        # Fetch sample records for evidence citation
        sample_stmt = select(BillingRecord).limit(5)
        if filters:
            sample_stmt = sample_stmt.where(*filters)
        samples = db.execute(sample_stmt).scalars().all()
        sample_records = [
            {
                "id": str(r.record_id),
                "provider": r.provider,
                "service": r.service_name,
                "resource_id": r.resource_id,
                "unblended_cost": Decimal(str(r.unblended_cost)).quantize(Decimal("0.0001")),
                "currency": r.currency,
            }
            for r in samples
        ]

        return {
            "total_metric": total_cost,
            "record_count": int(record_count or 0),
            "breakdown": breakdown,
            "sample_records": sample_records,
        }

    @classmethod
    def _retrieve_anomalies(cls, db: Session, plan: QueryPlan) -> Dict[str, Any]:
        """Queries cost anomalies detected in Stage 7."""
        stmt = select(
            func.coalesce(func.sum(CostAnomaly.estimated_excess_cost), 0),
            func.count(CostAnomaly.id),
        )

        filters = []
        if "provider" in plan.filters:
            filters.append(CostAnomaly.provider == plan.filters["provider"])
        if "status" in plan.filters:
            filters.append(CostAnomaly.status == plan.filters["status"])

        if filters:
            stmt = stmt.where(*filters)

        total_excess_raw, record_count = db.execute(stmt).one()
        total_excess = Decimal(str(total_excess_raw or 0)).quantize(Decimal("0.0001"))

        # Breakdown by category
        breakdown = []
        grp_stmt = (
            select(
                CostAnomaly.anomaly_category,
                func.coalesce(func.sum(CostAnomaly.estimated_excess_cost), 0),
                func.count(CostAnomaly.id),
            )
            .group_by(CostAnomaly.anomaly_category)
            .order_by(func.sum(CostAnomaly.estimated_excess_cost).desc())
            .limit(plan.limit)
        )
        if filters:
            grp_stmt = grp_stmt.where(*filters)

        for cat, cost, cnt in db.execute(grp_stmt).all():
            breakdown.append({
                "dimension": str(cat or "UNKNOWN"),
                "cost": Decimal(str(cost or 0)).quantize(Decimal("0.0001")),
                "count": int(cnt or 0),
            })

        # Fetch sample anomalies
        sample_stmt = select(CostAnomaly).limit(5)
        if filters:
            sample_stmt = sample_stmt.where(*filters)
        samples = db.execute(sample_stmt).scalars().all()
        sample_records = [
            {
                "id": str(a.id),
                "provider": a.provider,
                "category": a.anomaly_category,
                "service": a.service_name,
                "excess_cost": Decimal(str(a.estimated_excess_cost)).quantize(Decimal("0.0001")),
                "severity": str(a.severity),
                "status": str(a.status),
            }
            for a in samples
        ]

        return {
            "total_metric": total_excess,
            "record_count": int(record_count or 0),
            "breakdown": breakdown,
            "sample_records": sample_records,
        }

    @classmethod
    def _retrieve_waste(cls, db: Session, plan: QueryPlan) -> Dict[str, Any]:
        """Queries cloud waste detections from Stage 6."""
        stmt = select(
            func.coalesce(func.sum(WasteDetection.estimated_monthly_waste), 0),
            func.count(WasteDetection.id),
        )

        filters = []
        if "provider" in plan.filters:
            filters.append(WasteDetection.provider == plan.filters["provider"])
        if "status" in plan.filters:
            filters.append(WasteDetection.status == plan.filters["status"])

        if filters:
            stmt = stmt.where(*filters)

        total_waste_raw, record_count = db.execute(stmt).one()
        total_waste = Decimal(str(total_waste_raw or 0)).quantize(Decimal("0.0001"))

        # Breakdown by waste type
        breakdown = []
        grp_stmt = (
            select(
                WasteDetection.waste_type,
                func.coalesce(func.sum(WasteDetection.estimated_monthly_waste), 0),
                func.count(WasteDetection.id),
            )
            .group_by(WasteDetection.waste_type)
            .order_by(func.sum(WasteDetection.estimated_monthly_waste).desc())
            .limit(plan.limit)
        )
        if filters:
            grp_stmt = grp_stmt.where(*filters)

        for w_type, cost, cnt in db.execute(grp_stmt).all():
            breakdown.append({
                "dimension": str(w_type or "OTHER"),
                "cost": Decimal(str(cost or 0)).quantize(Decimal("0.0001")),
                "count": int(cnt or 0),
            })

        # Fetch sample waste items
        sample_stmt = select(WasteDetection).limit(5)
        if filters:
            sample_stmt = sample_stmt.where(*filters)
        samples = db.execute(sample_stmt).scalars().all()
        sample_records = [
            {
                "id": str(w.id),
                "provider": w.provider,
                "waste_type": str(w.waste_type),
                "resource_id": w.resource_id,
                "monthly_waste": Decimal(str(w.estimated_monthly_waste)).quantize(Decimal("0.0001")),
                "severity": str(w.severity),
                "status": str(w.status),
            }
            for w in samples
        ]

        return {
            "total_metric": total_waste,
            "record_count": int(record_count or 0),
            "breakdown": breakdown,
            "sample_records": sample_records,
        }

    @classmethod
    def _retrieve_recommendations(cls, db: Session, plan: QueryPlan) -> Dict[str, Any]:
        """Queries advisory optimization recommendations from Stage 8."""
        stmt = select(
            func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0),
            func.count(Recommendation.id),
        )

        filters = []
        if "provider" in plan.filters:
            filters.append(Recommendation.provider == plan.filters["provider"])
        if "status" in plan.filters:
            filters.append(Recommendation.status == plan.filters["status"])

        if filters:
            stmt = stmt.where(*filters)

        total_savings_raw, record_count = db.execute(stmt).one()
        total_savings = Decimal(str(total_savings_raw or 0)).quantize(Decimal("0.0001"))

        # Breakdown by strategy or priority
        breakdown = []
        grp_stmt = (
            select(
                Recommendation.strategy_id,
                func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0),
                func.count(Recommendation.id),
            )
            .group_by(Recommendation.strategy_id)
            .order_by(func.sum(Recommendation.estimated_monthly_savings).desc())
            .limit(plan.limit)
        )
        if filters:
            grp_stmt = grp_stmt.where(*filters)

        for strat, cost, cnt in db.execute(grp_stmt).all():
            breakdown.append({
                "dimension": str(strat or "advisory_strategy"),
                "cost": Decimal(str(cost or 0)).quantize(Decimal("0.0001")),
                "count": int(cnt or 0),
            })

        # Fetch sample recommendations
        sample_stmt = select(Recommendation).limit(5)
        if filters:
            sample_stmt = sample_stmt.where(*filters)
        samples = db.execute(sample_stmt).scalars().all()
        sample_records = [
            {
                "id": str(r.id),
                "provider": r.provider,
                "strategy": r.strategy_id,
                "title": r.title,
                "monthly_savings": Decimal(str(r.estimated_monthly_savings)).quantize(Decimal("0.0001")),
                "annual_savings": Decimal(str(r.estimated_annual_savings)).quantize(Decimal("0.0001")),
                "priority": str(r.priority),
                "status": str(r.status),
            }
            for r in samples
        ]

        return {
            "total_metric": total_savings,
            "record_count": int(record_count or 0),
            "breakdown": breakdown,
            "sample_records": sample_records,
        }

    @classmethod
    def _retrieve_resources(cls, db: Session, plan: QueryPlan) -> Dict[str, Any]:
        """Queries multi-cloud resource inventory from Stage 5."""
        stmt = select(func.count(CloudResource.resource_id))
        filters = []
        if "provider" in plan.filters:
            filters.append(CloudResource.provider == plan.filters["provider"])
        if filters:
            stmt = stmt.where(*filters)

        record_count = db.execute(stmt).scalar() or 0

        # Breakdown by resource type
        breakdown = []
        grp_stmt = (
            select(
                CloudResource.resource_type,
                func.count(CloudResource.resource_id),
            )
            .group_by(CloudResource.resource_type)
            .order_by(func.count(CloudResource.resource_id).desc())
            .limit(plan.limit)
        )
        if filters:
            grp_stmt = grp_stmt.where(*filters)

        for r_type, cnt in db.execute(grp_stmt).all():
            breakdown.append({
                "dimension": str(r_type or "resource"),
                "cost": Decimal("0.0000"),
                "count": int(cnt or 0),
            })

        sample_stmt = select(CloudResource).limit(5)
        if filters:
            sample_stmt = sample_stmt.where(*filters)
        samples = db.execute(sample_stmt).scalars().all()
        sample_records = [
            {
                "id": r.resource_id,
                "provider": r.provider,
                "resource_name": r.resource_name,
                "resource_type": r.resource_type,
                "region": r.region,
                "status": r.status,
            }
            for r in samples
        ]

        return {
            "total_metric": Decimal(str(record_count)),
            "record_count": int(record_count),
            "breakdown": breakdown,
            "sample_records": sample_records,
        }

