"""
CloudSage Change-Point and Structural Shift Detection Engine.
Identifies regime changes, persistent step increases, temporary spikes, and
gradual cost escalations using pure Decimal dual-window comparison and CUSUM tracking.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from backend.app.anomaly_detection.models import ChangePointResult, TimeSeries, TimeSeriesPoint
from backend.app.anomaly_detection.statistics import mean, stddev, median, PRECISION_FOUR


def dual_window_comparison(
    baseline_values: List[Decimal],
    observation_values: List[Decimal],
    min_shift_pct: Decimal = Decimal("20.0000"),
    min_shift_abs: Decimal = Decimal("10.0000"),
) -> Dict[str, Any]:
    """
    Compares baseline window expenditures with observation window expenditures.
    Computes delta, percentage change, and statistical significance via Welch-like t-statistic.
    """
    if not baseline_values or not observation_values:
        return {
            "is_significant": False,
            "baseline_mean": Decimal("0.0000"),
            "observation_mean": Decimal("0.0000"),
            "delta": Decimal("0.0000"),
            "percentage_change": Decimal("0.0000"),
            "t_stat": Decimal("0.0000"),
        }

    mu_base = mean(baseline_values)
    sigma_base = stddev(baseline_values)
    mu_obs = mean(observation_values)
    sigma_obs = stddev(observation_values)

    delta = mu_obs - mu_base
    n_base = Decimal(str(len(baseline_values)))
    n_obs = Decimal(str(len(observation_values)))

    if mu_base > Decimal("0.0000"):
        pct_change = ((delta / mu_base) * Decimal("100.0000")).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
    elif delta > Decimal("0.0000"):
        pct_change = Decimal("100.0000")
    else:
        pct_change = Decimal("0.0000")

    # Standard error of the difference
    var_base = (sigma_base ** 2) / n_base
    var_obs = (sigma_obs ** 2) / n_obs
    pooled_se = (var_base + var_obs).sqrt()

    if pooled_se > Decimal("0.0000"):
        t_stat = (delta / pooled_se).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
    else:
        # Zero variance: if delta > 0, treat as infinitely significant
        t_stat = Decimal("99.9999") if delta > Decimal("0.0000") else Decimal("0.0000")

    # Significant if t_stat >= 2.0 (p < 0.05 approx), delta >= min_shift_abs, and pct_change >= min_shift_pct
    is_significant = (
        delta >= min_shift_abs
        and pct_change >= min_shift_pct
        and t_stat >= Decimal("2.0000")
    )

    return {
        "is_significant": is_significant,
        "baseline_mean": mu_base,
        "baseline_stddev": sigma_base,
        "observation_mean": mu_obs,
        "observation_stddev": sigma_obs,
        "delta": delta.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP),
        "percentage_change": pct_change,
        "t_stat": t_stat,
    }


def cusum_shift_detection(
    values: List[Decimal],
    dates: List[date],
    target_mean: Decimal,
    target_stddev: Decimal,
    k_slack_mult: Decimal = Decimal("0.5000"),
    h_threshold_mult: Decimal = Decimal("4.0000"),
) -> Dict[str, Any]:
    """
    Cumulative Sum (CUSUM) upward shift detector.
    Tracks positive cumulative deviations from target mean.
    Returns whether an upward shift occurred, along with the estimated change-point date.
    """
    if not values or len(values) != len(dates):
        return {
            "shift_detected": False,
            "change_point_index": -1,
            "change_point_date": None,
            "max_cusum": Decimal("0.0000"),
            "threshold": Decimal("0.0000"),
        }

    # Slack allowance k and threshold h
    eff_stddev = target_stddev if target_stddev > Decimal("0.0000") else Decimal("1.0000")
    k = (k_slack_mult * eff_stddev).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
    h = (h_threshold_mult * eff_stddev).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)

    s_prev = Decimal("0.0000")
    cusum_series: List[Decimal] = []
    first_divergence_idx = -1
    breach_idx = -1
    max_cusum = Decimal("0.0000")

    for idx, x in enumerate(values):
        # S_i = max(0, S_{i-1} + (x_i - (target_mean + k)))
        increment = x - (target_mean + k)
        s_curr = s_prev + increment
        if s_curr < Decimal("0.0000"):
            s_curr = Decimal("0.0000")
            first_divergence_idx = -1  # Reset run
        else:
            if first_divergence_idx == -1 and s_curr > Decimal("0.0000"):
                first_divergence_idx = idx

        cusum_series.append(s_curr)
        if s_curr > max_cusum:
            max_cusum = s_curr

        if s_curr >= h and breach_idx == -1:
            breach_idx = idx
            break

        s_prev = s_curr

    shift_detected = breach_idx != -1
    change_idx = first_divergence_idx if shift_detected else -1
    cp_date = dates[change_idx] if (shift_detected and 0 <= change_idx < len(dates)) else None

    return {
        "shift_detected": shift_detected,
        "breach_index": breach_idx,
        "change_point_index": change_idx,
        "change_point_date": cp_date,
        "max_cusum": max_cusum.quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP),
        "threshold": h,
    }


def classify_pattern(
    points: List[TimeSeriesPoint],
    baseline_end_idx: int,
    baseline_mean: Decimal,
    baseline_stddev: Decimal,
) -> Dict[str, Any]:
    """
    Classifies the anomalous observation window into:
    - PERSISTENT_STEP: spending elevated for >= 3 consecutive days and sustains near post-mean.
    - TEMPORARY_SPIKE: spending spikes for 1-2 days then drops back down.
    - GRADUAL_ESCALATION: spending exhibits monotonic or near-monotonic upward growth.
    - NONE: normal variation.
    """
    obs_points = points[baseline_end_idx:]
    if not obs_points:
        return {"pattern": "NONE", "consecutive_elevated": 0, "confidence": Decimal("0.0000")}

    eff_stddev = baseline_stddev if baseline_stddev > Decimal("0.0000") else Decimal("1.0000")
    elevated_threshold = baseline_mean + (Decimal("1.5000") * eff_stddev)

    elevated_flags = [p.cost > elevated_threshold for p in obs_points]
    total_obs = len(obs_points)
    consecutive_elevated = 0
    max_consecutive = 0

    for flag in elevated_flags:
        if flag:
            consecutive_elevated += 1
            if consecutive_elevated > max_consecutive:
                max_consecutive = consecutive_elevated
        else:
            consecutive_elevated = 0

    # Test for monotonic/gradual escalation: count positive steps
    pos_steps = 0
    neg_steps = 0
    for i in range(1, len(obs_points)):
        diff = obs_points[i].cost - obs_points[i - 1].cost
        if diff > Decimal("0.0000"):
            pos_steps += 1
        elif diff < Decimal("0.0000"):
            neg_steps += 1

    obs_costs = [p.cost for p in obs_points]
    obs_mean = mean(obs_costs)

    # Classification logic
    if total_obs <= 2 and max_consecutive >= 1:
        pattern = "TEMPORARY_SPIKE"
        confidence = Decimal("0.8500")
    elif max_consecutive >= 3:
        # Check if tail returned to normal
        tail_normal = not elevated_flags[-1] and not elevated_flags[-2] if len(elevated_flags) >= 2 else False
        if tail_normal:
            pattern = "TEMPORARY_SPIKE"
            confidence = Decimal("0.9000")
        else:
            # Sustained elevated spend: check if gradual or step
            if len(obs_points) >= 4 and pos_steps >= (len(obs_points) - 1):
                pattern = "GRADUAL_ESCALATION"
                confidence = Decimal("0.9000")
            else:
                pattern = "PERSISTENT_STEP"
                confidence = Decimal("0.9500")
    elif len(obs_points) >= 3 and pos_steps >= 2 and neg_steps == 0:
        pattern = "GRADUAL_ESCALATION"
        confidence = Decimal("0.8000")
    elif max_consecutive in (1, 2):
        pattern = "TEMPORARY_SPIKE"
        confidence = Decimal("0.8500")
    else:
        pattern = "NONE"
        confidence = Decimal("0.0000")

    return {
        "pattern": pattern,
        "consecutive_elevated": max_consecutive,
        "confidence": confidence,
        "observation_mean": obs_mean,
    }


def detect_change_points(
    series: TimeSeries,
    baseline_window_days: int = 30,
    observation_window_days: int = 7,
    min_shift_pct: Decimal = Decimal("20.0000"),
    min_shift_abs: Decimal = Decimal("10.0000"),
) -> ChangePointResult:
    """
    Executes full change-point and structural shift detection across a TimeSeries.
    Combines dual-window comparison, CUSUM shift tracking, and pattern classification.
    """
    total_pts = len(series.points)
    min_required = baseline_window_days + 1
    if total_pts < min_required:
        return ChangePointResult(
            is_change_point=False,
            change_type="NONE",
            change_point_date=None,
            confidence=Decimal("0.0000"),
            details={"reason": "INSUFFICIENT_HISTORY", "point_count": total_pts, "required": min_required},
        )

    split_idx = total_pts - observation_window_days
    if split_idx < baseline_window_days:
        split_idx = baseline_window_days

    baseline_points = series.points[:split_idx]
    observation_points = series.points[split_idx:]

    baseline_costs = [p.cost for p in baseline_points]
    observation_costs = [p.cost for p in observation_points]

    # 1. Dual-window comparative test
    dw = dual_window_comparison(
        baseline_values=baseline_costs,
        observation_values=observation_costs,
        min_shift_pct=min_shift_pct,
        min_shift_abs=min_shift_abs,
    )

    # 2. CUSUM shift detection over entire series
    all_costs = series.cost_values
    all_dates = series.point_dates
    mu_base = dw["baseline_mean"]
    sigma_base = dw["baseline_stddev"]

    cusum = cusum_shift_detection(
        values=all_costs,
        dates=all_dates,
        target_mean=mu_base,
        target_stddev=sigma_base,
    )

    # 3. Pattern classification
    pattern_info = classify_pattern(
        points=series.points,
        baseline_end_idx=split_idx,
        baseline_mean=mu_base,
        baseline_stddev=sigma_base,
    )

    is_change = dw["is_significant"] or cusum["shift_detected"]
    change_type = pattern_info["pattern"] if is_change else "NONE"
    if is_change and change_type == "NONE":
        change_type = "PERSISTENT_STEP"

    # Identify date of shift
    cp_date = cusum["change_point_date"]
    if cp_date is None and is_change and observation_points:
        cp_date = observation_points[0].point_date

    return ChangePointResult(
        is_change_point=is_change,
        change_type=change_type,
        change_point_date=cp_date,
        baseline_mean=dw["baseline_mean"],
        post_change_mean=dw["observation_mean"],
        shift_magnitude=dw["delta"],
        shift_percentage=dw["percentage_change"],
        confidence=pattern_info["confidence"],
        consecutive_days_elevated=pattern_info["consecutive_elevated"],
        details={
            "t_stat": str(dw["t_stat"]),
            "max_cusum": str(cusum["max_cusum"]),
            "cusum_threshold": str(cusum["threshold"]),
            "baseline_window_points": len(baseline_points),
            "observation_window_points": len(observation_points),
        },
    )
