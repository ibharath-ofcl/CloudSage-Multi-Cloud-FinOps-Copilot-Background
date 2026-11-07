"""
CloudSage Billing Time-Series Aggregation Service.
Extracts daily expenditure and usage series from normalized FOCUS 1.0 billing records
across Provider, Account, Service, Region, Resource, and SKU dimensions.
Guarantees strict Decimal precision, contiguous date zero-filling, and credit isolation.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.models import TimeSeries, TimeSeriesPoint
from backend.app.models.billing import BillingRecord


class BillingAggregationService:
    """Service aggregating normalized billing records into dimensional time series."""

    @classmethod
    def extract_time_series(
        cls,
        db: Session,
        start_date: date,
        end_date: date,
        dimension_type: str = "SERVICE",
        provider: Optional[str] = None,
        account_id: Optional[str] = None,
        service_name: Optional[str] = None,
        resource_id: Optional[str] = None,
        zero_fill: bool = True,
    ) -> List[TimeSeries]:
        """
        Extracts contiguous daily expenditure series across the requested dimension.
        Dimensions: PROVIDER, ACCOUNT, SERVICE, REGION, RESOURCE, SKU
        """
        start_dt = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)

        # Base filter: Usage period overlap
        query = db.query(BillingRecord).filter(
            BillingRecord.usage_start_time >= start_dt,
            BillingRecord.usage_start_time <= end_dt,
        )

        if provider and provider.upper() != "ALL":
            query = query.filter(BillingRecord.provider == provider.upper())
        if account_id:
            query = query.filter(BillingRecord.subscription_id == account_id)
        if service_name:
            query = query.filter(BillingRecord.service_name == service_name)
        if resource_id:
            query = query.filter(BillingRecord.resource_id == resource_id)

        # Fetch records (only columns needed for aggregation and attribution)
        records: List[BillingRecord] = query.all()
        if not records:
            return []

        # Group line items into dimensional buckets and daily dates
        # Map: (dim_key, tuple_metadata) -> date -> list of records
        buckets: Dict[Tuple, Dict[date, List[BillingRecord]]] = defaultdict(lambda: defaultdict(list))

        dim_upper = dimension_type.upper().strip()

        for rec in records:
            # Parse record date
            rec_dt = rec.usage_start_time
            rec_date = rec_dt.date() if isinstance(rec_dt, datetime) else rec_dt

            # Exclude negative credits from positive expenditure series to prevent distribution corruption
            # Negative credits are stored/analyzed separately in attribution
            unblended = rec.unblended_cost or Decimal("0.0000")

            if dim_upper == "PROVIDER":
                key = (rec.provider,)
            elif dim_upper == "ACCOUNT":
                key = (rec.provider, rec.subscription_id)
            elif dim_upper == "REGION":
                key = (rec.provider, rec.region)
            elif dim_upper == "RESOURCE":
                key = (rec.provider, rec.subscription_id, rec.service_category, rec.service_name, rec.region, rec.resource_id)
            elif dim_upper == "SKU":
                key = (rec.provider, rec.subscription_id, rec.service_name, rec.pricing_model.value if hasattr(rec.pricing_model, 'value') else str(rec.pricing_model))
            else:  # Default: SERVICE
                key = (rec.provider, rec.subscription_id, rec.service_category, rec.service_name, rec.region)

            buckets[key][rec_date].append(rec)

        # Build contiguous date sequence
        all_dates: List[date] = []
        cur_date = start_date
        while cur_date <= end_date:
            all_dates.append(cur_date)
            cur_date += timedelta(days=1)

        result_series: List[TimeSeries] = []

        for key, date_map in buckets.items():
            points: List[TimeSeriesPoint] = []

            # Populate points (zero-filled if requested)
            for d in all_dates:
                day_records = date_map.get(d, [])
                # Sum positive costs (treat negative adjustments as 0 in baseline series)
                day_cost = sum((r.unblended_cost for r in day_records if r.unblended_cost > Decimal("0.0000")), Decimal("0.0000"))
                day_usage = sum((r.usage_quantity for r in day_records if r.usage_quantity is not None), Decimal("0.0"))
                record_ids = [str(r.record_id) for r in day_records]

                if day_records or zero_fill:
                    points.append(
                        TimeSeriesPoint(
                            timestamp=datetime(d.year, d.month, d.day, tzinfo=timezone.utc),
                            point_date=d,
                            cost=day_cost,
                            usage_quantity=day_usage,
                            source_record_ids=record_ids,
                        )
                    )

            # Construct dimensional metadata
            if dim_upper == "PROVIDER":
                prov = key[0]
                dim_key = f"{prov}"
                ts = TimeSeries(
                    dimension_type="PROVIDER",
                    dimension_key=dim_key,
                    provider=prov,
                    points=points,
                )
            elif dim_upper == "ACCOUNT":
                prov, acc = key
                dim_key = f"{prov}/{acc}"
                ts = TimeSeries(
                    dimension_type="ACCOUNT",
                    dimension_key=dim_key,
                    provider=prov,
                    account_id=acc,
                    points=points,
                )
            elif dim_upper == "REGION":
                prov, reg = key
                dim_key = f"{prov}/{reg}"
                ts = TimeSeries(
                    dimension_type="REGION",
                    dimension_key=dim_key,
                    provider=prov,
                    region=reg,
                    points=points,
                )
            elif dim_upper == "RESOURCE":
                prov, acc, cat, svc, reg, res_id = key
                dim_key = f"{prov}/{acc}/{svc}/{res_id}"
                ts = TimeSeries(
                    dimension_type="RESOURCE",
                    dimension_key=dim_key,
                    provider=prov,
                    account_id=acc,
                    service_category=cat,
                    service_name=svc,
                    region=reg,
                    resource_id=res_id,
                    points=points,
                )
            elif dim_upper == "SKU":
                prov, acc, svc, sku = key
                dim_key = f"{prov}/{acc}/{svc}/{sku}"
                ts = TimeSeries(
                    dimension_type="SKU",
                    dimension_key=dim_key,
                    provider=prov,
                    account_id=acc,
                    service_name=svc,
                    sku=sku,
                    points=points,
                )
            else:  # SERVICE
                prov, acc, cat, svc, reg = key
                dim_key = f"{prov}/{acc}/{svc}"
                ts = TimeSeries(
                    dimension_type="SERVICE",
                    dimension_key=dim_key,
                    provider=prov,
                    account_id=acc,
                    service_category=cat,
                    service_name=svc,
                    region=reg,
                    points=points,
                )

            result_series.append(ts)

        return result_series


def aggregate_time_series(
    db: Session,
    dimension_type: str = "SERVICE",
    provider: Optional[str] = None,
    account_id: Optional[str] = None,
    service_name: Optional[str] = None,
    resource_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    zero_fill: bool = True,
) -> List[TimeSeries]:
    """Helper delegating to BillingAggregationService.extract_time_series."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    return BillingAggregationService.extract_time_series(
        db=db,
        start_date=start_date,
        end_date=end_date,
        dimension_type=dimension_type,
        provider=provider,
        account_id=account_id,
        service_name=service_name,
        resource_id=resource_id,
        zero_fill=zero_fill,
    )
