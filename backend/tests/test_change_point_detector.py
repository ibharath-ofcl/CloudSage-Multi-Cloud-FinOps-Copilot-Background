"""
Unit Tests for CloudSage Change-Point and Structural Shift Detection.
Tests dual-window testing, CUSUM shift tracking, and pattern classification
(temporary spike vs persistent step vs gradual escalation).
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest

from backend.app.anomaly_detection.change_points import (
    classify_pattern,
    cusum_shift_detection,
    detect_change_points,
    dual_window_comparison,
)
from backend.app.anomaly_detection.models import TimeSeries, TimeSeriesPoint


def test_dual_window_comparison_significant_shift():
    """Validates that a 200% jump in observation window triggers significant shift."""
    baseline = [Decimal("100.0000") + Decimal(str(i % 5)) for i in range(14)]
    observation = [Decimal("300.0000") + Decimal(str(i % 5)) for i in range(7)]

    res = dual_window_comparison(
        baseline_values=baseline,
        observation_values=observation,
        min_shift_pct=Decimal("20.0000"),
        min_shift_abs=Decimal("10.0000"),
    )

    assert res["is_significant"] is True
    assert res["delta"] > Decimal("190.0000")
    assert res["percentage_change"] > Decimal("190.0000")
    assert res["t_stat"] > Decimal("5.0000")


def test_dual_window_comparison_flat_spend():
    """Validates that normal random noise does not trigger a false change point."""
    baseline = [Decimal("100.0000") + Decimal(str(i % 3)) for i in range(14)]
    observation = [Decimal("101.0000") + Decimal(str(i % 3)) for i in range(7)]

    res = dual_window_comparison(
        baseline_values=baseline,
        observation_values=observation,
        min_shift_pct=Decimal("20.0000"),
        min_shift_abs=Decimal("10.0000"),
    )

    assert res["is_significant"] is False


def test_cusum_shift_detection():
    """Validates CUSUM detector pinpointing the exact shift date."""
    base_date = date(2026, 10, 1)
    dates = [base_date + timedelta(days=i) for i in range(25)]

    # 15 days of normal $50 spend, followed by 10 days of $200 spend starting on day 15 (2026-10-16)
    values = [Decimal("50.0000")] * 15 + [Decimal("200.0000")] * 10

    res = cusum_shift_detection(
        values=values,
        dates=dates,
        target_mean=Decimal("50.0000"),
        target_stddev=Decimal("5.0000"),
    )

    assert res["shift_detected"] is True
    assert res["change_point_index"] == 15
    assert res["change_point_date"] == date(2026, 10, 16)


def test_temporary_spike_vs_persistent_step():
    """Validates classification distinguishing 1-day spike from multi-day persistent step."""
    base_date = date(2026, 10, 1)
    pts_baseline = [
        TimeSeriesPoint(
            timestamp=datetime(2026, 10, 1 + i, 0, 0, tzinfo=timezone.utc),
            point_date=base_date + timedelta(days=i),
            cost=Decimal("50.0000"),
        )
        for i in range(20)
    ]

    # Scenario A: Temporary spike (1 day high, then back down)
    spike_pts = [
        TimeSeriesPoint(
            timestamp=datetime(2026, 10, 21, 0, 0, tzinfo=timezone.utc),
            point_date=base_date + timedelta(days=20),
            cost=Decimal("500.0000"),
        ),
        TimeSeriesPoint(
            timestamp=datetime(2026, 10, 22, 0, 0, tzinfo=timezone.utc),
            point_date=base_date + timedelta(days=21),
            cost=Decimal("51.0000"),
        ),
        TimeSeriesPoint(
            timestamp=datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc),
            point_date=base_date + timedelta(days=22),
            cost=Decimal("49.0000"),
        ),
    ]

    class_spike = classify_pattern(
        points=pts_baseline + spike_pts,
        baseline_end_idx=20,
        baseline_mean=Decimal("50.0000"),
        baseline_stddev=Decimal("5.0000"),
    )
    assert class_spike["pattern"] == "TEMPORARY_SPIKE"

    # Scenario B: Persistent step (5 consecutive days elevated)
    step_pts = [
        TimeSeriesPoint(
            timestamp=datetime(2026, 10, 21 + i, 0, 0, tzinfo=timezone.utc),
            point_date=base_date + timedelta(days=20 + i),
            cost=Decimal("300.0000"),
        )
        for i in range(5)
    ]

    class_step = classify_pattern(
        points=pts_baseline + step_pts,
        baseline_end_idx=20,
        baseline_mean=Decimal("50.0000"),
        baseline_stddev=Decimal("5.0000"),
    )
    assert class_step["pattern"] == "PERSISTENT_STEP"


def test_gradual_escalation_detection():
    """Validates detection of monotonically increasing gradual cost escalation."""
    base_date = date(2026, 10, 1)
    pts_baseline = [
        TimeSeriesPoint(
            timestamp=datetime(2026, 10, 1 + i, 0, 0, tzinfo=timezone.utc),
            point_date=base_date + timedelta(days=i),
            cost=Decimal("50.0000"),
        )
        for i in range(20)
    ]

    escalation_pts = [
        TimeSeriesPoint(
            timestamp=datetime(2026, 10, 21 + i, 0, 0, tzinfo=timezone.utc),
            point_date=base_date + timedelta(days=20 + i),
            cost=Decimal(str(80 + (i * 40))),  # 80, 120, 160, 200, 240
        )
        for i in range(5)
    ]

    class_esc = classify_pattern(
        points=pts_baseline + escalation_pts,
        baseline_end_idx=20,
        baseline_mean=Decimal("50.0000"),
        baseline_stddev=Decimal("5.0000"),
    )
    assert class_esc["pattern"] == "GRADUAL_ESCALATION"


def test_detect_change_points_insufficient_history():
    """Validates that series shorter than required window returns clean non-change result."""
    base_date = date(2026, 10, 1)
    short_series = TimeSeries(
        dimension_type="SERVICE",
        dimension_key="AWS/1111/AmazonEC2",
        provider="AWS",
        points=[
            TimeSeriesPoint(
                timestamp=datetime(2026, 10, 1 + i, 0, 0, tzinfo=timezone.utc),
                point_date=base_date + timedelta(days=i),
                cost=Decimal("100.0000"),
            )
            for i in range(10)
        ],
    )

    res = detect_change_points(short_series, baseline_window_days=30, observation_window_days=7)
    assert res.is_change_point is False
    assert res.change_type == "NONE"
