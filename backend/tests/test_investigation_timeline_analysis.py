"""
Tests for Time-Series Historical Timeline & Moving Average Analysis Engine.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest

from backend.app.investigation.time_series_analysis import TimeSeriesAnalysisEngine
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord


def test_timeline_contiguous_dates(db_session):
    """Verifies timeline builds a contiguous sequence of days without skipping dates."""
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        resource_id="i-test",
        anomaly_category="SERVICE_SPIKE",
        anomaly_date=date(2026, 3, 15),
        actual_cost=Decimal("1500.0000"),
        expected_cost=Decimal("500.0000"),
        estimated_excess_cost=Decimal("1000.0000"),
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)
    db_session.commit()

    res = TimeSeriesAnalysisEngine.analyze_timeline(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
        window_days_before=14,
        window_days_after=2,
    )

    # 14 days before + anomaly day + 2 days after = 17 days
    assert len(res.data_points) == 17
    assert res.anomaly_date == "2026-03-15"

    # Verify contiguous dates
    dates = [pt.date for pt in res.data_points]
    for i in range(len(dates) - 1):
        d1 = datetime.strptime(dates[i], "%Y-%m-%d").date()
        d2 = datetime.strptime(dates[i + 1], "%Y-%m-%d").date()
        assert (d2 - d1).days == 1


def test_anomaly_flagged_in_timeline(db_session):
    """Verifies that the anomaly date is flagged with is_anomaly_period."""
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        resource_id="i-test",
        anomaly_category="SERVICE_SPIKE",
        anomaly_date=date(2026, 3, 15),
        actual_cost=Decimal("1500.0000"),
        expected_cost=Decimal("500.0000"),
        estimated_excess_cost=Decimal("1000.0000"),
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)
    db_session.commit()

    res = TimeSeriesAnalysisEngine.analyze_timeline(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    anomaly_pts = [pt for pt in res.data_points if pt.is_anomaly_period]
    assert len(anomaly_pts) == 1
    assert anomaly_pts[0].date == "2026-03-15"
    assert anomaly_pts[0].actual_cost == Decimal("1500.0000")


def test_rolling_seven_day_moving_average(db_session):
    """Verifies 7-day rolling moving average is populated."""
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        resource_id="i-test",
        anomaly_category="SERVICE_SPIKE",
        anomaly_date=date(2026, 3, 15),
        actual_cost=Decimal("1500.0000"),
        expected_cost=Decimal("500.0000"),
        estimated_excess_cost=Decimal("1000.0000"),
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)
    db_session.commit()

    res = TimeSeriesAnalysisEngine.analyze_timeline(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    for pt in res.data_points:
        assert pt.seven_day_moving_avg is not None
        assert pt.seven_day_moving_avg > Decimal("0.0000")


def test_variance_metrics_dod_wow_mom(db_session):
    """Verifies DoD, WoW, and MoM changes are calculated as percentage values."""
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        resource_id="i-test",
        anomaly_category="SERVICE_SPIKE",
        anomaly_date=date(2026, 3, 15),
        actual_cost=Decimal("1500.0000"),
        expected_cost=Decimal("500.0000"),
        estimated_excess_cost=Decimal("1000.0000"),
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)
    db_session.commit()

    res = TimeSeriesAnalysisEngine.analyze_timeline(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    assert res.day_over_day_change_pct is not None
    assert res.week_over_week_change_pct is not None
    assert res.month_over_month_change_pct is not None
    # Spend jumped from 500 to 1500 -> 200% increase
    assert res.month_over_month_change_pct == Decimal("200.00")
