"""
CloudSage Service Cost Spike Detector.
Monitors service-level daily expenditure and detects rapid spikes and spending surges.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from backend.app.anomaly_detection.base import BaseAnomalyDetector
from backend.app.anomaly_detection.detectors.statistical import StatisticalEnsembleDetector
from backend.app.anomaly_detection.models import (
    BaselineResult,
    DetectorExecutionResult,
    TimeSeries,
)
from backend.app.core.enums import AnomalyCategory


class ServiceCostSpikeDetector(BaseAnomalyDetector):
    """Detector specialized for service-level cost spikes."""

    def __init__(self) -> None:
        self._ensemble = StatisticalEnsembleDetector()

    @property
    def detector_id(self) -> str:
        return "service_cost_spike_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> AnomalyCategory:
        return AnomalyCategory.SERVICE_SPIKE

    @property
    def supported_dimensions(self) -> List[str]:
        return ["SERVICE"]

    @property
    def description(self) -> str:
        return "Monitors service-level daily expenditure and detects abnormal cost surges."

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "z_score_threshold": Decimal("2.5000"),
            "modified_z_threshold": Decimal("3.0000"),
            "iqr_multiplier": Decimal("1.5000"),
            "min_excess_cost": Decimal("25.0000"),
            "min_pct_deviation": Decimal("40.0000"),
            "consensus_min_votes": 2,
        }

    def detect(
        self,
        time_series: TimeSeries,
        baseline: Optional[BaselineResult] = None,
        billing_records: Optional[List[Any]] = None,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> DetectorExecutionResult:
        if time_series.dimension_type != "SERVICE":
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                status="CLEAN",
                message="ServiceCostSpikeDetector only applies to SERVICE dimension.",
            )

        t = {**self.default_thresholds, **(thresholds or {})}
        res = self._ensemble.detect(time_series, baseline, billing_records, thresholds=t)

        # Re-tag detector_id and category
        for anom in res.anomalies:
            anom.detector_id = self.detector_id
            anom.detector_version = self.detector_version
            anom.anomaly_category = self.category
            anom.title = f"Service Spend Spike in {time_series.provider} {time_series.service_name}"

        return DetectorExecutionResult(
            detector_id=self.detector_id,
            status=res.status,
            anomalies=res.anomalies,
            message=res.message,
            metrics=res.metrics,
        )

