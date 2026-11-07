"""
CloudSage Statistical Ensemble Anomaly Detector.
Combines Z-score, Modified Z-score (MAD-based), and Interquartile Range (IQR) Tukey fences
into a robust multi-metric consensus detector.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from backend.app.anomaly_detection.base import BaseAnomalyDetector
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
from backend.app.anomaly_detection.statistics import (
    iqr_fences,
    modified_z_score,
    z_score,
    PRECISION_FOUR,
)
from backend.app.core.enums import AnomalyCategory, DetectionMethod


class StatisticalEnsembleDetector(BaseAnomalyDetector):
    """Ensemble detector evaluating Z-score, Modified Z-score, and IQR simultaneously."""

    @property
    def detector_id(self) -> str:
        return "statistical_ensemble_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> AnomalyCategory:
        return AnomalyCategory.SERVICE_SPIKE

    @property
    def supported_dimensions(self) -> List[str]:
        return ["PROVIDER", "ACCOUNT", "SERVICE", "REGION", "RESOURCE", "SKU"]

    @property
    def description(self) -> str:
        return "Ensemble anomaly detector voting across Z-Score, Modified Z-Score (MAD), and IQR."

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "z_score_threshold": Decimal("2.5000"),
            "modified_z_threshold": Decimal("3.0000"),
            "iqr_multiplier": Decimal("1.5000"),
            "min_excess_cost": Decimal("10.0000"),
            "min_pct_deviation": Decimal("25.0000"),
            "consensus_min_votes": 2,
        }

    def detect(
        self,
        time_series: TimeSeries,
        baseline: Optional[BaselineResult] = None,
        billing_records: Optional[List[Any]] = None,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> DetectorExecutionResult:
        if not baseline or baseline.status == "INSUFFICIENT_HISTORY":
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                status="INSUFFICIENT_DATA",
                message="Statistical baseline requires at least 7 points.",
            )

        t = {**self.default_thresholds, **(thresholds or {})}
        z_thresh = Decimal(str(t["z_score_threshold"]))
        mod_z_thresh = Decimal(str(t["modified_z_threshold"]))
        iqr_mult = Decimal(str(t["iqr_multiplier"]))
        min_excess = Decimal(str(t["min_excess_cost"]))
        min_pct = Decimal(str(t["min_pct_deviation"]))
        min_votes = int(t["consensus_min_votes"])

        _, upper_fence = iqr_fences(baseline.q1, baseline.q3, baseline.iqr, multiplier=iqr_mult)
        anomalies: List[AnomalyCandidate] = []

        # Evaluate the most recent points in the observation window (typically last 1 to 7 points)
        eval_points = time_series.points[-7:] if len(time_series.points) >= 7 else time_series.points

        for pt in eval_points:
            cost = pt.cost
            votes = 0
            methods_triggered: List[DetectionMethod] = []

            # Method 1: Z-Score
            zs = z_score(cost, baseline.mean, baseline.stddev)
            if zs >= z_thresh:
                votes += 1
                methods_triggered.append(DetectionMethod.Z_SCORE)

            # Method 2: Modified Z-Score
            mzs = modified_z_score(cost, baseline.median, baseline.mad)
            if mzs >= mod_z_thresh:
                votes += 1
                methods_triggered.append(DetectionMethod.MODIFIED_Z_SCORE)

            # Method 3: IQR Upper Fence
            if cost > upper_fence:
                votes += 1
                methods_triggered.append(DetectionMethod.IQR)

            # Consensus decision
            is_anomaly = votes >= min_votes or mzs >= Decimal("5.0000")
            if not is_anomaly:
                continue

            expected = baseline.median if baseline.mad > Decimal("0.0000") else baseline.mean
            dev_metrics = calculate_deviations(cost, expected)
            abs_dev = dev_metrics["absolute_deviation"]
            pct_dev = dev_metrics["percentage_deviation"]
            excess = calculate_excess_cost(cost, expected)

            # Filter insignificant dollar amounts or minor percentage shifts
            if excess < min_excess or pct_dev < min_pct:
                continue

            proj = calculate_projected_impact(excess, anomaly_type="SERVICE_SPIKE", duration_days=1)
            sev = determine_severity(excess, pct_dev)

            # Confidence score based on consensus
            if votes == 3:
                conf = Decimal("0.9800")
            elif votes == 2:
                conf = Decimal("0.8800")
            else:
                conf = Decimal("0.7500")

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
                anomaly_date=pt.point_date,
                observed_cost=cost,
                expected_cost=expected,
                absolute_deviation=abs_dev,
                percentage_deviation=pct_dev,
                estimated_excess_cost=excess,
                projected_monthly_impact=proj["projected_monthly_impact"],
                currency=time_series.currency,
                anomaly_category=self.category,
                detection_methods=methods_triggered or [DetectionMethod.ENSEMBLE],
                z_score=zs,
                severity=sev,
                confidence_score=conf,
                baseline_window_days=baseline.window_days,
                observation_window_days=1,
                baseline_metrics={
                    "mean": str(baseline.mean),
                    "stddev": str(baseline.stddev),
                    "median": str(baseline.median),
                    "mad": str(baseline.mad),
                    "q1": str(baseline.q1),
                    "q3": str(baseline.q3),
                    "iqr": str(baseline.iqr),
                    "upper_fence": str(upper_fence),
                    "z_score": str(zs),
                    "modified_z_score": str(mzs),
                    "votes": votes,
                },
                source_billing_references=pt.source_record_ids,
            )
            anomalies.append(candidate)

        return DetectorExecutionResult(
            detector_id=self.detector_id,
            status="DETECTED" if anomalies else "CLEAN",
            anomalies=anomalies,
            message=f"Found {len(anomalies)} statistical anomalies." if anomalies else "No anomalies detected.",
            metrics={"evaluated_points": len(eval_points), "anomalies_count": len(anomalies)},
        )
