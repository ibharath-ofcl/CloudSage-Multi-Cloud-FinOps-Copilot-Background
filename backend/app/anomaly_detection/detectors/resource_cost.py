"""
CloudSage Resource Cost Spike Detector.
Monitors individual cloud resource daily expenditure and flags rogue or runaway resource costs.
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


class ResourceCostSpikeDetector(BaseAnomalyDetector):
    """Detector specialized for individual cloud resource cost spikes."""

    def __init__(self) -> None:
        self._ensemble = StatisticalEnsembleDetector()

    @property
    def detector_id(self) -> str:
        return "resource_cost_spike_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> AnomalyCategory:
        return AnomalyCategory.RESOURCE_SPIKE

    @property
    def supported_dimensions(self) -> List[str]:
        return ["RESOURCE"]

    @property
    def description(self) -> str:
        return "Monitors individual resource spending and flags runaway or exploding resources."

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "z_score_threshold": Decimal("2.5000"),
            "modified_z_threshold": Decimal("3.0000"),
            "iqr_multiplier": Decimal("1.5000"),
            "min_excess_cost": Decimal("15.0000"),
            "min_pct_deviation": Decimal("50.0000"),
            "consensus_min_votes": 2,
        }

    def detect(
        self,
        time_series: TimeSeries,
        baseline: Optional[BaselineResult] = None,
        billing_records: Optional[List[Any]] = None,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> DetectorExecutionResult:
        if time_series.dimension_type != "RESOURCE":
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                status="CLEAN",
                message="ResourceCostSpikeDetector only applies to RESOURCE dimension.",
            )

        t = {**self.default_thresholds, **(thresholds or {})}
        res = self._ensemble.detect(time_series, baseline, billing_records, thresholds=t)

        for anom in res.anomalies:
            anom.detector_id = self.detector_id
            anom.detector_version = self.detector_version
            anom.anomaly_category = self.category
            r_name = time_series.resource_id or "Resource"
            anom.title = f"Runaway Cost on Resource {r_name}"

        return DetectorExecutionResult(
            detector_id=self.detector_id,
            status=res.status,
            anomalies=res.anomalies,
            message=res.message,
            metrics=res.metrics,
        )
