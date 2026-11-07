"""
CloudSage Change Point and Structural Shift Detector.
Identifies persistent step increases and continuous spending escalations using CUSUM and dual-window testing.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from backend.app.anomaly_detection.base import BaseAnomalyDetector
from backend.app.anomaly_detection.change_points import detect_change_points
from backend.app.anomaly_detection.impact import (
    calculate_deviations,
    calculate_excess_cost,
    calculate_projected_impact,
    determine_severity,
)
from backend.app.anomaly_detection.models import (
    AnomalyCandidate,
    BaselineResult,
    DetectorExecutionResult,
    TimeSeries,
)
from backend.app.core.enums import AnomalyCategory, DetectionMethod


class ChangePointDetector(BaseAnomalyDetector):
    """Detector for persistent step increases and gradual spending escalations."""

    @property
    def detector_id(self) -> str:
        return "change_point_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> AnomalyCategory:
        return AnomalyCategory.PERSISTENT_STEP

    @property
    def supported_dimensions(self) -> List[str]:
        return ["PROVIDER", "ACCOUNT", "SERVICE", "REGION", "RESOURCE"]

    @property
    def description(self) -> str:
        return "Detects persistent step increases and gradual structural shifts in cloud expenditure."

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "baseline_window_days": 14,
            "observation_window_days": 7,
            "min_shift_pct": Decimal("20.0000"),
            "min_shift_abs": Decimal("10.0000"),
        }

    def detect(
        self,
        time_series: TimeSeries,
        baseline: Optional[BaselineResult] = None,
        billing_records: Optional[List[Any]] = None,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> DetectorExecutionResult:
        t = {**self.default_thresholds, **(thresholds or {})}
        bw_days = int(t["baseline_window_days"])
        obs_days = int(t["observation_window_days"])
        min_pct = Decimal(str(t["min_shift_pct"]))
        min_abs = Decimal(str(t["min_shift_abs"]))

        cp_res = detect_change_points(
            series=time_series,
            baseline_window_days=bw_days,
            observation_window_days=obs_days,
            min_shift_pct=min_pct,
            min_shift_abs=min_abs,
        )

        if not cp_res.is_change_point or not cp_res.change_point_date:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                status="CLEAN",
                anomalies=[],
                message="No structural change-points detected.",
            )

        category = (
            AnomalyCategory.GRADUAL_ESCALATION
            if cp_res.change_type == "GRADUAL_ESCALATION"
            else AnomalyCategory.PERSISTENT_STEP
        )

        excess_daily = calculate_excess_cost(cp_res.post_change_mean, cp_res.baseline_mean)
        devs = calculate_deviations(cp_res.post_change_mean, cp_res.baseline_mean)
        proj = calculate_projected_impact(excess_daily, anomaly_type=cp_res.change_type, duration_days=obs_days)
        sev = determine_severity(proj["projected_monthly_impact"], cp_res.shift_percentage)

        latest_pt = time_series.points[-1]

        candidate = AnomalyCandidate(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            provider=time_series.provider,
            account_id=time_series.account_id or "UNKNOWN",
            service_category=time_series.service_category or "GENERAL",
            service_name=time_series.service_name or "General",
            region=time_series.region or "GLOBAL",
            resource_id=time_series.resource_id,
            sku=time_series.sku,
            anomaly_date=cp_res.change_point_date,
            observed_cost=cp_res.post_change_mean,
            expected_cost=cp_res.baseline_mean,
            absolute_deviation=devs["absolute_deviation"],
            percentage_deviation=devs["percentage_deviation"],
            estimated_excess_cost=excess_daily,
            projected_monthly_impact=proj["projected_monthly_impact"],
            currency=time_series.currency,
            anomaly_category=category,
            detection_methods=[DetectionMethod.CHANGE_POINT],
            severity=sev,
            confidence_score=cp_res.confidence,
            baseline_window_days=bw_days,
            observation_window_days=obs_days,
            baseline_metrics={
                "baseline_mean": str(cp_res.baseline_mean),
                "post_change_mean": str(cp_res.post_change_mean),
                "shift_magnitude": str(cp_res.shift_magnitude),
                "shift_percentage": str(cp_res.shift_percentage),
                "consecutive_days_elevated": cp_res.consecutive_days_elevated,
                **cp_res.details,
            },
            source_billing_references=latest_pt.source_record_ids,
        )

        return DetectorExecutionResult(
            detector_id=self.detector_id,
            status="DETECTED",
            anomalies=[candidate],
            message=f"Detected {cp_res.change_type} shift on {cp_res.change_point_date}.",
            metrics={"change_type": cp_res.change_type, "shift_magnitude": str(cp_res.shift_magnitude)},
        )
