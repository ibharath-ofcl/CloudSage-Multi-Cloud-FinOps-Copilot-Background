"""
CloudSage Statistical Baseline Engine.
Computes rolling observation baselines (Mean, Standard Deviation, Median, MAD, Quartiles, IQR)
across Provider, Account, Service, Region, and Resource dimensions.
Handles zero-variance, sparse time series, and insufficient historical data.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.models import BaselineResult, TimeSeries
from backend.app.anomaly_detection import statistics
from backend.app.models.anomaly import CostBaseline


class BaselineEngine:
    """Engine computing rolling empirical statistical baselines."""

    @classmethod
    def calculate_baseline(
        cls,
        series: TimeSeries,
        window_days: int = 30,
        target_date: Optional[date] = None,
        min_observations: int = 7,
    ) -> BaselineResult:
        """
        Computes statistical distribution over historical window prior to target_date.
        Excludes target_date itself to avoid contaminating baseline with current anomaly.
        """
        if not series.points:
            today = date.today()
            return cls._empty_baseline(today, today, window_days, "INSUFFICIENT_HISTORY")

        # Determine evaluation date
        eval_date = target_date or series.points[-1].point_date
        window_start = eval_date - timedelta(days=window_days)
        window_end = eval_date - timedelta(days=1)

        # Filter historical points strictly within baseline window [eval_date - window_days, eval_date - 1]
        hist_points = [
            p for p in series.points
            if window_start <= p.point_date <= window_end
        ]

        if len(hist_points) < min_observations:
            return cls._empty_baseline(window_start, window_end, window_days, "INSUFFICIENT_HISTORY")

        costs = [p.cost for p in hist_points]
        zero_count = sum(1 for c in costs if c == Decimal("0.0000"))

        mean_val = statistics.mean(costs)
        stddev_val = statistics.stddev(costs)
        med_val = statistics.median(costs)
        mad_val = statistics.mad(costs)
        q1_val, _, q3_val = statistics.quartiles(costs)
        iqr_val = statistics.iqr(costs)
        min_val = min(costs) if costs else Decimal("0.0000")
        max_val = max(costs) if costs else Decimal("0.0000")

        status = "SUFFICIENT"
        if stddev_val == Decimal("0.0000"):
            status = "ZERO_VARIANCE"

        return BaselineResult(
            mean=mean_val,
            stddev=stddev_val,
            median=med_val,
            mad=mad_val,
            q1=q1_val,
            q3=q3_val,
            iqr=iqr_val,
            min_value=min_val,
            max_value=max_val,
            sample_count=len(hist_points),
            zero_count=zero_count,
            start_date=window_start,
            end_date=window_end,
            window_days=window_days,
            status=status,
        )

    @classmethod
    def persist_baseline(
        cls,
        db: Session,
        series: TimeSeries,
        baseline: BaselineResult,
    ) -> CostBaseline:
        """Saves or updates a computed baseline record in PostgreSQL."""
        record = (
            db.query(CostBaseline)
            .filter(
                CostBaseline.dimension_key == series.dimension_key,
                CostBaseline.window_days == baseline.window_days,
                CostBaseline.end_date == baseline.end_date,
            )
            .first()
        )

        if not record:
            record = CostBaseline(
                dimension_type=series.dimension_type,
                dimension_key=series.dimension_key,
                provider=series.provider,
                account_id=series.account_id,
                service_name=series.service_name,
                region=series.region,
                resource_id=series.resource_id,
                window_days=baseline.window_days,
                start_date=baseline.start_date,
                end_date=baseline.end_date,
                mean=baseline.mean,
                stddev=baseline.stddev,
                median=baseline.median,
                mad=baseline.mad,
                q1=baseline.q1,
                q3=baseline.q3,
                iqr=baseline.iqr,
                min_value=baseline.min_value,
                max_value=baseline.max_value,
                sample_count=baseline.sample_count,
                zero_count=baseline.zero_count,
                currency=series.currency,
            )
            db.add(record)
        else:
            record.mean = baseline.mean
            record.stddev = baseline.stddev
            record.median = baseline.median
            record.mad = baseline.mad
            record.q1 = baseline.q1
            record.q3 = baseline.q3
            record.iqr = baseline.iqr
            record.min_value = baseline.min_value
            record.max_value = baseline.max_value
            record.sample_count = baseline.sample_count
            record.zero_count = baseline.zero_count

        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def _empty_baseline(
        cls,
        start_date: date,
        end_date: date,
        window_days: int,
        status: str,
    ) -> BaselineResult:
        zero = Decimal("0.0000")
        return BaselineResult(
            mean=zero,
            stddev=zero,
            median=zero,
            mad=zero,
            q1=zero,
            q3=zero,
            iqr=zero,
            min_value=zero,
            max_value=zero,
            sample_count=0,
            zero_count=0,
            start_date=start_date,
            end_date=end_date,
            window_days=window_days,
            status=status,
        )


calculate_baseline = BaselineEngine.calculate_baseline
persist_baseline = BaselineEngine.persist_baseline
