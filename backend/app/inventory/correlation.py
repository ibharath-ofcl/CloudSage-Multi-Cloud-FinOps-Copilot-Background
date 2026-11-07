"""
CloudSage Inventory-to-Billing Financial Correlation Engine.
Bridges resource inventory with financial billing records, computing cumulative expenditure,
cost coverage metrics, and detecting un-inventoried or orphaned billing items.
Strict Decimal precision enforced throughout.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource


class BillingCorrelationEngine:
    """Correlates physical cloud inventory with financial ledger records."""

    @classmethod
    def correlate_resource(
        cls,
        db: Session,
        resource_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Computes comprehensive financial metrics for a single inventory resource."""
        resource: Optional[CloudResource] = (
            db.query(CloudResource)
            .filter(CloudResource.resource_id == resource_id)
            .first()
        )

        agg = (
            db.query(
                func.sum(BillingRecord.unblended_cost).label("total_billed"),
                func.count(BillingRecord.record_id).label("record_count"),
                func.min(BillingRecord.usage_start_time).label("first_billed"),
                func.max(BillingRecord.usage_end_time).label("last_billed"),
            )
            .filter(BillingRecord.resource_id == resource_id)
            .first()
        )

        total_cost = Decimal(str(agg.total_billed or "0.0000"))
        record_count = int(agg.record_count or 0)
        first_billed = agg.first_billed
        last_billed = agg.last_billed

        correlation_status = "CONFIRMED_BILLED" if record_count > 0 else "INVENTORY_ONLY"

        return {
            "resource_id": resource_id,
            "provider": resource.provider if resource else "UNKNOWN",
            "resource_name": resource.resource_name if resource else resource_id,
            "total_billed_cost": total_cost,
            "total_effective_cost": total_cost,
            "billing_record_count": record_count,
            "first_billed_at": first_billed,
            "last_billed_at": last_billed,
            "correlation_status": correlation_status,
        }

    @classmethod
    def get_coverage_summary(
        cls,
        db: Session,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Computes overall cost coverage metrics comparing total billing expenditure
        against reconciled inventory resources.
        """
        # Billing totals query
        billing_query = db.query(
            func.sum(BillingRecord.unblended_cost).label("total_cost"),
            func.count(func.distinct(BillingRecord.resource_id)).label("unique_billed_resources"),
        )
        if provider:
            billing_query = billing_query.filter(BillingRecord.provider == provider.upper())
        billing_agg = billing_query.first()
        total_billing_cost = Decimal(str(billing_agg.total_cost or "0.0000"))
        total_billed_resources_count = int(billing_agg.unique_billed_resources or 0)

        # Inventory totals query
        inv_query = db.query(
            func.count(CloudResource.resource_id).label("total_inventory"),
        )
        if provider:
            inv_query = inv_query.filter(CloudResource.provider == provider.upper())
        inv_agg = inv_query.first()
        total_inventory_resources = int(inv_agg.total_inventory or 0)

        # Correlated cost: billing records whose resource_id exists in cloud_resources
        correlated_cost_query = (
            db.query(func.sum(BillingRecord.unblended_cost))
            .filter(
                BillingRecord.resource_id.in_(
                    db.query(CloudResource.resource_id)
                )
            )
        )
        if provider:
            correlated_cost_query = correlated_cost_query.filter(BillingRecord.provider == provider.upper())
        correlated_cost = Decimal(str(correlated_cost_query.scalar() or "0.0000"))

        if total_billing_cost > Decimal("0.0000"):
            cost_coverage_pct = (correlated_cost / total_billing_cost * Decimal("100.00")).quantize(Decimal("0.01"))
        else:
            cost_coverage_pct = Decimal("100.00")

        # Count billing-only resources (billed but not in inventory)
        billing_only_subquery = db.query(BillingRecord.resource_id).filter(
            BillingRecord.resource_id.notin_(db.query(CloudResource.resource_id))
        )
        if provider:
            billing_only_subquery = billing_only_subquery.filter(BillingRecord.provider == provider.upper())
        billing_only_count = db.query(func.count(func.distinct(billing_only_subquery.subquery().c.resource_id))).scalar() or 0

        return {
            "provider": provider.upper() if provider else "ALL",
            "total_billing_cost": total_billing_cost,
            "correlated_billing_cost": correlated_cost,
            "unreconciled_billing_cost": (total_billing_cost - correlated_cost).quantize(Decimal("0.0001")),
            "cost_coverage_percentage": cost_coverage_pct,
            "total_inventory_resources": total_inventory_resources,
            "total_billed_resources": total_billed_resources_count,
            "billing_only_resources_count": int(billing_only_count),
        }

    @classmethod
    def sync_resource_monthly_costs(
        cls,
        db: Session,
        lookback_days: int = 30,
    ) -> int:
        """
        Updates CloudResource.monthly_cost for all inventory resources based on
        actual trailing billing records.
        """
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=lookback_days)

        cost_subquery = (
            db.query(
                BillingRecord.resource_id,
                func.sum(BillingRecord.unblended_cost).label("period_cost"),
            )
            .filter(BillingRecord.usage_start_time >= start_date)
            .group_by(BillingRecord.resource_id)
            .all()
        )

        cost_map = {row.resource_id: Decimal(str(row.period_cost or "0.0000")) for row in cost_subquery}

        resources = db.query(CloudResource).all()
        updated = 0
        for res in resources:
            new_cost = cost_map.get(res.resource_id, Decimal("0.0000"))
            if res.monthly_cost != new_cost:
                res.monthly_cost = new_cost
                updated += 1

        db.commit()
        return updated
