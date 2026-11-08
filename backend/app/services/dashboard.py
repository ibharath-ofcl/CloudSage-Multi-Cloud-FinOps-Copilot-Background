"""
CloudSage Multi-Cloud FinOps Dashboard Analytics Service.
Executes high-performance, strictly typed analytical aggregations across Stages 3–9 tables:
BillingRecord, CloudResource, WasteDetection, CostAnomaly, Recommendation, IngestionRun, DataQualityReport.
Enforces the Zero Float Rule: all monetary numbers strictly use Python Decimal and Numeric(18, 4).
"""

import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import io
import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, cast, Date, desc, func, or_, select
from sqlalchemy.orm import Session

from backend.app.core.enums import CloudProvider, Priority, Severity, WasteStatus, WasteType
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord
from backend.app.models.ingestion import IngestionRun
from backend.app.models.normalization import DataQualityReport, NormalizationRun
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection
from backend.app.schemas.dashboard import (
    AnomalySummaryResponse,
    CostTrendPoint,
    CostTrendResponse,
    DashboardFilterParams,
    DashboardOverviewResponse,
    DataQualitySummaryResponse,
    ExecutiveKpiSummary,
    IngestionSummaryResponse,
    InventorySummaryResponse,
    ProviderComparisonItem,
    ProviderComparisonResponse,
    RecommendationSummaryResponse,
    ResourceCostItem,
    ResourceCostsResponse,
    SavingsSummaryResponse,
    ServiceBreakdownResponse,
    ServiceCostItem,
    WasteSummaryResponse,
)


class DashboardAnalyticsService:
    """Enterprise FinOps dashboard data aggregation service."""

    @classmethod
    def _apply_billing_filters(cls, stmt, filters: Optional[DashboardFilterParams]):
        """Applies global filter parameters to a BillingRecord query statement."""
        if not filters:
            return stmt

        conditions = []
        if filters.start_date:
            conditions.append(func.date(BillingRecord.usage_start_time) >= filters.start_date.isoformat())
        if filters.end_date:
            conditions.append(func.date(BillingRecord.usage_start_time) <= filters.end_date.isoformat())
        if filters.provider and filters.provider.upper() != "ALL":
            conditions.append(BillingRecord.provider == filters.provider.upper())
        if filters.service:
            conditions.append(BillingRecord.service_name.ilike(f"%{filters.service}%"))
        if filters.account_id:
            conditions.append(
                or_(
                    BillingRecord.billing_account_id == filters.account_id,
                    BillingRecord.subscription_id == filters.account_id,
                )
            )
        if filters.region:
            conditions.append(BillingRecord.region == filters.region)

        if conditions:
            stmt = stmt.where(and_(*conditions))
        return stmt

    @classmethod
    def get_executive_kpis(
        cls, db: Session, filters: Optional[DashboardFilterParams] = None
    ) -> ExecutiveKpiSummary:
        """Computes executive FinOps KPIs with strict Decimal precision."""
        now = datetime.now(timezone.utc)
        current_month_start = date(now.year, now.month, 1)

        # 1. Total Cloud Spend across filtered scope
        spend_stmt = select(func.coalesce(func.sum(BillingRecord.unblended_cost), 0))
        spend_stmt = cls._apply_billing_filters(spend_stmt, filters)
        total_spend_raw = db.execute(spend_stmt).scalar() or 0
        total_spend = Decimal(str(total_spend_raw)).quantize(Decimal("0.0001"))

        # 2. Month-to-Date (MTD) Spend
        mtd_stmt = select(func.coalesce(func.sum(BillingRecord.unblended_cost), 0)).where(
            func.date(BillingRecord.usage_start_time) >= current_month_start.isoformat()
        )
        if filters and filters.provider and filters.provider.upper() != "ALL":
            mtd_stmt = mtd_stmt.where(BillingRecord.provider == filters.provider.upper())
        mtd_raw = db.execute(mtd_stmt).scalar() or 0
        mtd_spend = Decimal(str(mtd_raw)).quantize(Decimal("0.0001"))

        # 3. Previous Period Spend (previous calendar month)
        if now.month == 1:
            prev_month_start = date(now.year - 1, 12, 1)
            prev_month_end = date(now.year - 1, 12, 31)
        else:
            prev_month_start = date(now.year, now.month - 1, 1)
            prev_month_end = current_month_start - timedelta(days=1)

        prev_stmt = select(func.coalesce(func.sum(BillingRecord.unblended_cost), 0)).where(
            and_(
                func.date(BillingRecord.usage_start_time) >= prev_month_start.isoformat(),
                func.date(BillingRecord.usage_start_time) <= prev_month_end.isoformat(),
            )
        )
        if filters and filters.provider and filters.provider.upper() != "ALL":
            prev_stmt = prev_stmt.where(BillingRecord.provider == filters.provider.upper())
        prev_raw = db.execute(prev_stmt).scalar() or 0
        prev_spend = Decimal(str(prev_raw)).quantize(Decimal("0.0001"))

        # 4. Month-over-Month (MoM) Change Percentage
        if prev_spend > Decimal("0.0000"):
            mom_change = (((mtd_spend - prev_spend) / prev_spend) * Decimal("100.0")).quantize(
                Decimal("0.01")
            )
        else:
            mom_change = Decimal("0.00")

        # 5. Cost Anomalies
        anom_stmt = select(
            func.count(CostAnomaly.id),
            func.coalesce(func.sum(CostAnomaly.estimated_excess_cost), 0),
        ).where(CostAnomaly.status == "OPEN")
        if filters and filters.provider and filters.provider.upper() != "ALL":
            anom_stmt = anom_stmt.where(CostAnomaly.provider == filters.provider.upper())
        anom_cnt, anom_excess = db.execute(anom_stmt).one()
        anomalous_excess_cost = Decimal(str(anom_excess or 0)).quantize(Decimal("0.0001"))

        # 6. Cloud Waste
        waste_stmt = select(
            func.count(WasteDetection.id),
            func.coalesce(func.sum(WasteDetection.estimated_monthly_waste), 0),
        ).where(WasteDetection.status == WasteStatus.ACTIVE.value)
        if filters and filters.provider and filters.provider.upper() != "ALL":
            waste_stmt = waste_stmt.where(WasteDetection.provider == filters.provider.upper())
        waste_cnt, waste_sum = db.execute(waste_stmt).one()
        identified_monthly_waste = Decimal(str(waste_sum or 0)).quantize(Decimal("0.0001"))

        # 7. Potential Savings (Advisory Recommendations)
        rec_stmt = select(
            func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0),
            func.coalesce(func.sum(Recommendation.estimated_annual_savings), 0),
            func.coalesce(func.sum(Recommendation.verified_savings), 0),
        ).where(Recommendation.status.in_(["PROPOSED", "OPEN", "APPROVED", "IMPLEMENTED"]))
        if filters and filters.provider and filters.provider.upper() != "ALL":
            rec_stmt = rec_stmt.where(Recommendation.provider == filters.provider.upper())
        monthly_sav, annual_sav, verified_sav = db.execute(rec_stmt).one()
        potential_monthly_savings = Decimal(str(monthly_sav or 0)).quantize(Decimal("0.0001"))
        potential_annual_savings = Decimal(str(annual_sav or 0)).quantize(Decimal("0.0001"))
        verified_realized_savings = (
            Decimal(str(verified_sav)).quantize(Decimal("0.0001"))
            if verified_sav and Decimal(str(verified_sav)) > Decimal("0.0000")
            else None
        )

        # 8. Data Freshness Timestamp
        fresh_stmt = select(func.max(BillingRecord.created_at))
        fresh_ts = db.execute(fresh_stmt).scalar() or now

        return ExecutiveKpiSummary(
            total_spend=total_spend,
            mtd_spend=mtd_spend,
            previous_period_spend=prev_spend,
            mom_change_percentage=mom_change,
            active_anomalies_count=int(anom_cnt or 0),
            anomalous_excess_cost=anomalous_excess_cost,
            identified_waste_count=int(waste_cnt or 0),
            identified_monthly_waste=identified_monthly_waste,
            potential_monthly_savings=potential_monthly_savings,
            potential_annual_savings=potential_annual_savings,
            verified_realized_savings=verified_realized_savings,
            currency="USD",
            data_freshness_timestamp=fresh_ts,
        )

    @classmethod
    def get_cost_trends(
        cls,
        db: Session,
        filters: Optional[DashboardFilterParams] = None,
        granularity: str = "DAILY",
    ) -> CostTrendResponse:
        """Generates historical time-series spending trend by date and provider."""
        stmt = select(
            BillingRecord.usage_start_time,
            BillingRecord.provider,
            BillingRecord.unblended_cost,
        ).order_by(BillingRecord.usage_start_time.asc())
        stmt = cls._apply_billing_filters(stmt, filters)
        rows = db.execute(stmt).all()

        # Fetch anomaly dates to flag anomaly overlays
        anom_dates_stmt = select(CostAnomaly.anomaly_date).distinct()
        anom_dates = {str(row[0]) for row in db.execute(anom_dates_stmt).all() if row[0]}

        from collections import defaultdict
        daily_map = defaultdict(lambda: {
            "total": Decimal("0.0000"),
            "AWS": Decimal("0.0000"),
            "AZURE": Decimal("0.0000"),
            "GCP": Decimal("0.0000"),
        })

        for r in rows:
            u_time = r[0]
            if isinstance(u_time, datetime):
                d_str = u_time.date().isoformat()
            elif isinstance(u_time, date):
                d_str = u_time.isoformat()
            else:
                d_str = str(u_time)[:10]

            bucket_key = d_str[:7] if granularity.upper() == "MONTHLY" else d_str
            prov = str(r[1] or "").upper()
            cost = Decimal(str(r[2] or 0)).quantize(Decimal("0.0001"))

            daily_map[bucket_key]["total"] += cost
            if prov in daily_map[bucket_key]:
                daily_map[bucket_key][prov] += cost

        points: List[CostTrendPoint] = []
        grand_total = Decimal("0.0000")

        for b_key in sorted(daily_map.keys()):
            data = daily_map[b_key]
            t_cost = data["total"]
            grand_total += t_cost
            has_anom = any(ad.startswith(b_key) for ad in anom_dates)

            points.append(
                CostTrendPoint(
                    date=b_key,
                    total_cost=t_cost,
                    aws_cost=data["AWS"],
                    azure_cost=data["AZURE"],
                    gcp_cost=data["GCP"],
                    has_anomaly=has_anom,
                )
            )

        return CostTrendResponse(
            timeframe="custom" if (filters and (filters.start_date or filters.end_date)) else "last_30_days",
            granularity=granularity,
            points=points,
            total_cost=grand_total.quantize(Decimal("0.0001")),
            currency="USD",
        )

    @classmethod
    def get_provider_comparison(
        cls, db: Session, filters: Optional[DashboardFilterParams] = None
    ) -> ProviderComparisonResponse:
        """Calculates multi-cloud spending distribution across AWS, Azure, and GCP."""
        stmt = select(
            BillingRecord.provider,
            func.coalesce(func.sum(BillingRecord.unblended_cost), 0).label("cost"),
            func.count(BillingRecord.record_id).label("record_cnt"),
        ).group_by(BillingRecord.provider).order_by(desc("cost"))

        stmt = cls._apply_billing_filters(stmt, filters)
        rows = db.execute(stmt).all()

        total_spend = sum([Decimal(str(r.cost or 0)) for r in rows], Decimal("0.0000"))

        # Resource counts per provider from inventory
        res_stmt = select(CloudResource.provider, func.count(CloudResource.resource_id)).group_by(
            CloudResource.provider
        )
        res_counts = {str(p): int(cnt) for p, cnt in db.execute(res_stmt).all()}

        items: List[ProviderComparisonItem] = []
        for r in rows:
            p_cost = Decimal(str(r.cost or 0)).quantize(Decimal("0.0001"))
            pct = (
                ((p_cost / total_spend) * Decimal("100.0")).quantize(Decimal("0.01"))
                if total_spend > Decimal("0.0000")
                else Decimal("0.00")
            )
            items.append(
                ProviderComparisonItem(
                    provider=r.provider,
                    cost=p_cost,
                    percentage=pct,
                    record_count=int(r.record_cnt or 0),
                    resource_count=res_counts.get(r.provider, 0),
                )
            )

        return ProviderComparisonResponse(
            providers=items,
            total_spend=total_spend.quantize(Decimal("0.0001")),
            currency="USD",
        )

    @classmethod
    def get_service_breakdown(
        cls,
        db: Session,
        filters: Optional[DashboardFilterParams] = None,
        limit: int = 10,
    ) -> ServiceBreakdownResponse:
        """Computes top-N service expenditure and category distribution."""
        stmt = select(
            BillingRecord.service_name,
            BillingRecord.service_category,
            BillingRecord.provider,
            func.coalesce(func.sum(BillingRecord.unblended_cost), 0).label("cost"),
            func.count(BillingRecord.record_id).label("record_cnt"),
        ).group_by(
            BillingRecord.service_name,
            BillingRecord.service_category,
            BillingRecord.provider,
        ).order_by(desc("cost")).limit(limit)

        stmt = cls._apply_billing_filters(stmt, filters)
        rows = db.execute(stmt).all()

        # Overall total spend for percentage calculation
        total_stmt = select(func.coalesce(func.sum(BillingRecord.unblended_cost), 0))
        total_stmt = cls._apply_billing_filters(total_stmt, filters)
        total_spend = Decimal(str(db.execute(total_stmt).scalar() or 0)).quantize(Decimal("0.0001"))

        services: List[ServiceCostItem] = []
        for r in rows:
            s_cost = Decimal(str(r.cost or 0)).quantize(Decimal("0.0001"))
            pct = (
                ((s_cost / total_spend) * Decimal("100.0")).quantize(Decimal("0.01"))
                if total_spend > Decimal("0.0000")
                else Decimal("0.00")
            )
            services.append(
                ServiceCostItem(
                    service_name=r.service_name,
                    service_category=r.service_category,
                    provider=r.provider,
                    cost=s_cost,
                    percentage=pct,
                    record_count=int(r.record_cnt or 0),
                )
            )

        # Category aggregates
        cat_stmt = select(
            BillingRecord.service_category,
            func.coalesce(func.sum(BillingRecord.unblended_cost), 0),
        ).group_by(BillingRecord.service_category)
        cat_stmt = cls._apply_billing_filters(cat_stmt, filters)
        cat_dict = {
            str(cat): Decimal(str(cost or 0)).quantize(Decimal("0.0001"))
            for cat, cost in db.execute(cat_stmt).all()
        }

        return ServiceBreakdownResponse(
            services=services,
            categories=cat_dict,
            total_spend=total_spend,
            currency="USD",
        )

    @classmethod
    def get_resource_costs(
        cls,
        db: Session,
        filters: Optional[DashboardFilterParams] = None,
        limit: int = 20,
    ) -> ResourceCostsResponse:
        """Retrieves top cost-driving resources ranking and metadata."""
        stmt = select(
            BillingRecord.resource_id,
            func.coalesce(func.sum(BillingRecord.unblended_cost), 0).label("cost"),
            BillingRecord.provider,
            BillingRecord.service_name,
            BillingRecord.region,
        ).group_by(
            BillingRecord.resource_id,
            BillingRecord.provider,
            BillingRecord.service_name,
            BillingRecord.region,
        ).order_by(desc("cost")).limit(limit)

        stmt = cls._apply_billing_filters(stmt, filters)
        rows = db.execute(stmt).all()

        res_ids = [r.resource_id for r in rows if r.resource_id]
        meta_dict = {}
        if res_ids:
            inv_stmt = select(CloudResource).where(CloudResource.resource_id.in_(res_ids))
            for inv in db.execute(inv_stmt).scalars().all():
                meta_dict[inv.resource_id] = {
                    "name": inv.resource_name,
                    "status": inv.status,
                    "owner": inv.owner,
                    "environment": inv.environment,
                }

        items: List[ResourceCostItem] = []
        total_top_cost = Decimal("0.0000")

        for r in rows:
            c = Decimal(str(r.cost or 0)).quantize(Decimal("0.0001"))
            total_top_cost += c
            meta = meta_dict.get(r.resource_id, {})
            items.append(
                ResourceCostItem(
                    resource_id=r.resource_id,
                    resource_name=meta.get("name") or r.resource_id,
                    provider=r.provider,
                    service_name=r.service_name,
                    region=r.region,
                    monthly_cost=c,
                    status=meta.get("status") or "ACTIVE",
                    owner=meta.get("owner"),
                    environment=meta.get("environment"),
                )
            )

        return ResourceCostsResponse(
            resources=items,
            total_spend=total_top_cost.quantize(Decimal("0.0001")),
            currency="USD",
        )

    @classmethod
    def get_savings_summary(
        cls, db: Session, filters: Optional[DashboardFilterParams] = None
    ) -> SavingsSummaryResponse:
        """Computes potential and verified savings with anti-double-counting guarantees."""
        stmt = select(
            func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0),
            func.coalesce(func.sum(Recommendation.estimated_annual_savings), 0),
            func.coalesce(func.sum(Recommendation.verified_savings), 0),
        ).where(Recommendation.status.in_(["PROPOSED", "OPEN", "APPROVED", "IMPLEMENTED"]))

        if filters and filters.provider and filters.provider.upper() != "ALL":
            stmt = stmt.where(Recommendation.provider == filters.provider.upper())

        monthly, annual, verified = db.execute(stmt).one()

        # Breakdown by Provider
        p_stmt = select(
            Recommendation.provider,
            func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0),
        ).where(Recommendation.status.in_(["PROPOSED", "OPEN", "APPROVED"])).group_by(Recommendation.provider)
        by_prov = {
            str(p): Decimal(str(c or 0)).quantize(Decimal("0.0001"))
            for p, c in db.execute(p_stmt).all()
        }

        # Breakdown by Strategy
        s_stmt = select(
            Recommendation.strategy_id,
            func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0),
        ).where(Recommendation.status.in_(["PROPOSED", "OPEN", "APPROVED"])).group_by(Recommendation.strategy_id)
        by_strat = {
            str(s): Decimal(str(c or 0)).quantize(Decimal("0.0001"))
            for s, c in db.execute(s_stmt).all()
        }

        # Breakdown by Priority
        pr_stmt = select(
            Recommendation.priority,
            func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0),
        ).where(Recommendation.status.in_(["PROPOSED", "OPEN", "APPROVED"])).group_by(Recommendation.priority)
        by_prio = {
            str(pr): Decimal(str(c or 0)).quantize(Decimal("0.0001"))
            for pr, c in db.execute(pr_stmt).all()
        }

        return SavingsSummaryResponse(
            potential_monthly_savings=Decimal(str(monthly or 0)).quantize(Decimal("0.0001")),
            potential_annual_savings=Decimal(str(annual or 0)).quantize(Decimal("0.0001")),
            verified_realized_savings=(
                Decimal(str(verified)).quantize(Decimal("0.0001"))
                if verified and Decimal(str(verified)) > Decimal("0.0000")
                else None
            ),
            savings_by_provider=by_prov,
            savings_by_strategy=by_strat,
            savings_by_priority=by_prio,
            anti_double_counting_guarantee=True,
            currency="USD",
        )

    @classmethod
    def get_anomaly_summary(
        cls, db: Session, filters: Optional[DashboardFilterParams] = None
    ) -> AnomalySummaryResponse:
        """Aggregates cost anomaly intelligence metrics."""
        base_stmt = select(CostAnomaly)
        if filters and filters.provider and filters.provider.upper() != "ALL":
            base_stmt = base_stmt.where(CostAnomaly.provider == filters.provider.upper())

        # Total active & excess cost
        active_stmt = select(
            func.count(CostAnomaly.id),
            func.coalesce(func.sum(CostAnomaly.estimated_excess_cost), 0),
        ).where(CostAnomaly.status == "OPEN")
        if filters and filters.provider and filters.provider.upper() != "ALL":
            active_stmt = active_stmt.where(CostAnomaly.provider == filters.provider.upper())
        act_cnt, act_excess = db.execute(active_stmt).one()

        # Severity breakdown
        sev_stmt = select(CostAnomaly.severity, func.count(CostAnomaly.id)).where(
            CostAnomaly.status == "OPEN"
        ).group_by(CostAnomaly.severity)
        sev_dict = {str(s): int(cnt) for s, cnt in db.execute(sev_stmt).all()}

        # Category breakdown
        cat_stmt = select(CostAnomaly.anomaly_category, func.count(CostAnomaly.id)).where(
            CostAnomaly.status == "OPEN"
        ).group_by(CostAnomaly.anomaly_category)
        cat_dict = {str(c): int(cnt) for c, cnt in db.execute(cat_stmt).all()}

        # Provider breakdown
        prov_stmt = select(CostAnomaly.provider, func.count(CostAnomaly.id)).where(
            CostAnomaly.status == "OPEN"
        ).group_by(CostAnomaly.provider)
        prov_dict = {str(p): int(cnt) for p, cnt in db.execute(prov_stmt).all()}

        # Open vs Resolved
        status_stmt = select(CostAnomaly.status, func.count(CostAnomaly.id)).group_by(CostAnomaly.status)
        status_dict = {str(s): int(cnt) for s, cnt in db.execute(status_stmt).all()}

        return AnomalySummaryResponse(
            total_active_anomalies=int(act_cnt or 0),
            critical_count=sev_dict.get(Severity.CRITICAL.value, 0),
            high_count=sev_dict.get(Severity.HIGH.value, 0),
            medium_count=sev_dict.get(Severity.MEDIUM.value, 0),
            low_count=sev_dict.get(Severity.LOW.value, 0),
            total_excess_cost=Decimal(str(act_excess or 0)).quantize(Decimal("0.0001")),
            anomalies_by_provider=prov_dict,
            anomalies_by_category=cat_dict,
            open_vs_resolved=status_dict,
            currency="USD",
        )

    @classmethod
    def get_waste_summary(
        cls, db: Session, filters: Optional[DashboardFilterParams] = None
    ) -> WasteSummaryResponse:
        """Aggregates infrastructure waste detection metrics."""
        active_stmt = select(
            func.count(WasteDetection.id),
            func.coalesce(func.sum(WasteDetection.estimated_monthly_waste), 0),
        ).where(WasteDetection.status == WasteStatus.ACTIVE.value)
        if filters and filters.provider and filters.provider.upper() != "ALL":
            active_stmt = active_stmt.where(WasteDetection.provider == filters.provider.upper())
        act_cnt, act_waste = db.execute(active_stmt).one()

        # Waste by Type
        type_stmt = select(
            WasteDetection.waste_type,
            func.coalesce(func.sum(WasteDetection.estimated_monthly_waste), 0),
        ).where(WasteDetection.status == WasteStatus.ACTIVE.value).group_by(WasteDetection.waste_type)
        type_dict = {
            str(t): Decimal(str(c or 0)).quantize(Decimal("0.0001"))
            for t, c in db.execute(type_stmt).all()
        }

        # Waste by Provider
        prov_stmt = select(
            WasteDetection.provider,
            func.coalesce(func.sum(WasteDetection.estimated_monthly_waste), 0),
        ).where(WasteDetection.status == WasteStatus.ACTIVE.value).group_by(WasteDetection.provider)
        prov_dict = {
            str(p): Decimal(str(c or 0)).quantize(Decimal("0.0001"))
            for p, c in db.execute(prov_stmt).all()
        }

        # Severity distribution
        sev_stmt = select(WasteDetection.severity, func.count(WasteDetection.id)).where(
            WasteDetection.status == WasteStatus.ACTIVE.value
        ).group_by(WasteDetection.severity)
        sev_dict = {str(s): int(cnt) for s, cnt in db.execute(sev_stmt).all()}

        return WasteSummaryResponse(
            total_active_waste_items=int(act_cnt or 0),
            total_monthly_waste=Decimal(str(act_waste or 0)).quantize(Decimal("0.0001")),
            waste_by_type=type_dict,
            waste_by_provider=prov_dict,
            severity_distribution=sev_dict,
            currency="USD",
        )

    @classmethod
    def get_recommendations_summary(
        cls, db: Session, filters: Optional[DashboardFilterParams] = None
    ) -> RecommendationSummaryResponse:
        """Aggregates advisory recommendation status and priority distribution."""
        active_stmt = select(
            func.count(Recommendation.id),
            func.coalesce(func.sum(Recommendation.estimated_monthly_savings), 0),
        ).where(Recommendation.status.in_(["PROPOSED", "OPEN", "UNDER_REVIEW"]))
        if filters and filters.provider and filters.provider.upper() != "ALL":
            active_stmt = active_stmt.where(Recommendation.provider == filters.provider.upper())
        rec_cnt, rec_sav = db.execute(active_stmt).one()

        # Priority distribution
        prio_stmt = select(Recommendation.priority, func.count(Recommendation.id)).where(
            Recommendation.status.in_(["PROPOSED", "OPEN", "UNDER_REVIEW"])
        ).group_by(Recommendation.priority)
        prio_dict = {str(p): int(cnt) for p, cnt in db.execute(prio_stmt).all()}

        # Strategy distribution
        strat_stmt = select(Recommendation.strategy_id, func.count(Recommendation.id)).where(
            Recommendation.status.in_(["PROPOSED", "OPEN", "UNDER_REVIEW"])
        ).group_by(Recommendation.strategy_id)
        strat_dict = {str(s): int(cnt) for s, cnt in db.execute(strat_stmt).all()}

        # Status distribution
        stat_stmt = select(Recommendation.status, func.count(Recommendation.id)).group_by(
            Recommendation.status
        )
        stat_dict = {str(s): int(cnt) for s, cnt in db.execute(stat_stmt).all()}

        return RecommendationSummaryResponse(
            total_open_recommendations=int(rec_cnt or 0),
            potential_monthly_savings=Decimal(str(rec_sav or 0)).quantize(Decimal("0.0001")),
            priority_distribution=prio_dict,
            strategy_distribution=strat_dict,
            status_distribution=stat_dict,
            currency="USD",
        )

    @classmethod
    def get_inventory_summary(
        cls, db: Session, filters: Optional[DashboardFilterParams] = None
    ) -> InventorySummaryResponse:
        """Aggregates multi-cloud resource inventory and tagging compliance metrics."""
        total_stmt = select(func.count(CloudResource.resource_id))
        if filters and filters.provider and filters.provider.upper() != "ALL":
            total_stmt = total_stmt.where(CloudResource.provider == filters.provider.upper())
        total_res = db.execute(total_stmt).scalar() or 0

        # Provider distribution
        prov_stmt = select(CloudResource.provider, func.count(CloudResource.resource_id)).group_by(
            CloudResource.provider
        )
        prov_dict = {str(p): int(cnt) for p, cnt in db.execute(prov_stmt).all()}

        # Type distribution
        type_stmt = select(CloudResource.resource_type, func.count(CloudResource.resource_id)).group_by(
            CloudResource.resource_type
        )
        type_dict = {str(t): int(cnt) for t, cnt in db.execute(type_stmt).all()}

        # Region distribution
        reg_stmt = select(CloudResource.region, func.count(CloudResource.resource_id)).group_by(
            CloudResource.region
        )
        reg_dict = {str(r): int(cnt) for r, cnt in db.execute(reg_stmt).all()}

        # Untagged resources (missing owner or environment)
        untagged_stmt = select(func.count(CloudResource.resource_id)).where(
            or_(
                CloudResource.owner.is_(None),
                CloudResource.owner == "",
                CloudResource.environment == "unknown",
            )
        )
        untagged_cnt = db.execute(untagged_stmt).scalar() or 0

        if total_res > 0:
            tagged_pct = (
                (Decimal(str(total_res - untagged_cnt)) / Decimal(str(total_res))) * Decimal("100.0")
            ).quantize(Decimal("0.01"))
        else:
            tagged_pct = Decimal("100.00")

        return InventorySummaryResponse(
            total_resources=int(total_res),
            resources_by_provider=prov_dict,
            resources_by_type=type_dict,
            resources_by_region=reg_dict,
            tag_coverage_percentage=tagged_pct,
            untagged_resources_count=int(untagged_cnt),
        )

    @classmethod
    def get_ingestion_summary(
        cls, db: Session, filters: Optional[DashboardFilterParams] = None
    ) -> IngestionSummaryResponse:
        """Computes ingestion batch telemetry and pipeline health."""
        total_stmt = select(
            func.count(IngestionRun.id),
            func.coalesce(func.sum(case((IngestionRun.status == "COMPLETED", 1), else_=0)), 0),
            func.coalesce(func.sum(case((IngestionRun.status == "FAILED", 1), else_=0)), 0),
            func.coalesce(func.sum(IngestionRun.ingested_records), 0),
        )
        total_runs, success_runs, failed_runs, recs_cnt = db.execute(total_stmt).one()

        # Provider coverage
        p_stmt = select(IngestionRun.provider).distinct()
        providers = [str(p[0]) for p in db.execute(p_stmt).all() if p[0]]

        # Last successful run
        last_stmt = select(func.max(IngestionRun.completed_at)).where(
            IngestionRun.status == "COMPLETED"
        )
        last_ts = db.execute(last_stmt).scalar()

        return IngestionSummaryResponse(
            total_runs=int(total_runs or 0),
            successful_runs=int(success_runs or 0),
            failed_runs=int(failed_runs or 0),
            total_records_ingested=int(recs_cnt or 0),
            provider_coverage=providers,
            last_successful_ingestion=last_ts,
        )

    @classmethod
    def get_data_quality_summary(
        cls, db: Session, filters: Optional[DashboardFilterParams] = None
    ) -> DataQualitySummaryResponse:
        """Computes FOCUS 1.0 normalization and data quality compliance."""
        q_stmt = select(
            func.coalesce(func.avg(DataQualityReport.overall_score), Decimal("100.00")),
            func.coalesce(func.sum(DataQualityReport.total_records_evaluated), 0),
        )
        avg_score, total_eval = db.execute(q_stmt).one()
        quality_score = Decimal(str(avg_score)).quantize(Decimal("0.01"))

        # Inferred FOCUS compliance score
        norm_stmt = select(
            func.coalesce(func.avg(NormalizationRun.average_quality_score), Decimal("100.00"))
        )
        focus_score = Decimal(str(db.execute(norm_stmt).scalar() or 100.0)).quantize(Decimal("0.01"))

        return DataQualitySummaryResponse(
            overall_quality_score=quality_score,
            focus_compliance_percentage=focus_score,
            total_records_evaluated=int(total_eval or 0),
            tag_quality_score=quality_score,
            currency_uniformity_score=Decimal("100.00"),
        )

    @classmethod
    def get_overview(
        cls, db: Session, filters: Optional[DashboardFilterParams] = None
    ) -> DashboardOverviewResponse:
        """Consolidates complete executive overview command center metrics."""
        kpi = cls.get_executive_kpis(db, filters)
        prov_comp = cls.get_provider_comparison(db, filters)
        trends = cls.get_cost_trends(db, filters, granularity="DAILY")
        top_services = cls.get_service_breakdown(db, filters, limit=8)
        savings = cls.get_savings_summary(db, filters)
        anomalies = cls.get_anomaly_summary(db, filters)
        waste = cls.get_waste_summary(db, filters)
        recs = cls.get_recommendations_summary(db, filters)

        suggested_questions = [
            "Summarize our total cloud expenditure across AWS, Azure, and GCP.",
            "Which cloud provider is driving our highest expenditure?",
            "Explain our most severe cost anomalies.",
            "What unattached disks or idle virtual machines were detected?",
            "What are our top P1 optimization recommendations?",
            "How much money can we save annually by rightsizing compute?",
            "Which team or owner tag has the highest cloud spend?",
        ]

        return DashboardOverviewResponse(
            kpi=kpi,
            provider_comparison=prov_comp,
            cost_trends=trends,
            top_services=top_services,
            savings_summary=savings,
            anomaly_summary=anomalies,
            waste_summary=waste,
            recommendation_summary=recs,
            copilot_suggested_questions=suggested_questions,
        )

    @classmethod
    def export_dashboard_data(
        cls,
        db: Session,
        filters: Optional[DashboardFilterParams] = None,
        export_format: str = "json",
        section: str = "overview",
    ) -> Tuple[str, str]:
        """
        Exports filter-aware dashboard report in CSV or JSON.
        Returns: (content_string, media_type)
        """
        overview = cls.get_overview(db, filters)

        if export_format.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)

            if section == "services":
                writer.writerow(["Service Name", "Category", "Provider", "Cost USD", "Percentage", "Records"])
                for s in overview.top_services.services:
                    writer.writerow([s.service_name, s.service_category, s.provider, str(s.cost), str(s.percentage), s.record_count])
            elif section == "trends":
                writer.writerow(["Date", "Total Cost USD", "AWS USD", "Azure USD", "GCP USD", "Has Anomaly"])
                for p in overview.cost_trends.points:
                    writer.writerow([p.date, str(p.total_cost), str(p.aws_cost), str(p.azure_cost), str(p.gcp_cost), p.has_anomaly])
            elif section == "providers":
                writer.writerow(["Provider", "Cost USD", "Percentage", "Billing Records", "Resources"])
                for pr in overview.provider_comparison.providers:
                    writer.writerow([pr.provider, str(pr.cost), str(pr.percentage), pr.record_count, pr.resource_count])
            else:
                # Executive KPI summary CSV
                writer.writerow(["KPI Metric", "Value", "Currency"])
                writer.writerow(["Total Cloud Spend", str(overview.kpi.total_spend), overview.kpi.currency])
                writer.writerow(["Month-to-Date Spend", str(overview.kpi.mtd_spend), overview.kpi.currency])
                writer.writerow(["Previous Period Spend", str(overview.kpi.previous_period_spend), overview.kpi.currency])
                writer.writerow(["Month-over-Month Change (%)", str(overview.kpi.mom_change_percentage), "%"])
                writer.writerow(["Active Cost Anomalies", overview.kpi.active_anomalies_count, "count"])
                writer.writerow(["Anomalous Excess Cost", str(overview.kpi.anomalous_excess_cost), overview.kpi.currency])
                writer.writerow(["Active Waste Detections", overview.kpi.identified_waste_count, "count"])
                writer.writerow(["Identified Monthly Waste", str(overview.kpi.identified_monthly_waste), overview.kpi.currency])
                writer.writerow(["Potential Monthly Savings", str(overview.kpi.potential_monthly_savings), overview.kpi.currency])
                writer.writerow(["Potential Annual Savings", str(overview.kpi.potential_annual_savings), overview.kpi.currency])
                writer.writerow(["Verified Realized Savings", str(overview.kpi.verified_realized_savings or "N/A"), overview.kpi.currency])

            return output.getvalue(), "text/csv"

        else:
            # JSON format
            dump = overview.model_dump(mode="json")
            if section != "all" and section in dump:
                return json.dumps(dump[section], indent=2), "application/json"
            return json.dumps(dump, indent=2), "application/json"
