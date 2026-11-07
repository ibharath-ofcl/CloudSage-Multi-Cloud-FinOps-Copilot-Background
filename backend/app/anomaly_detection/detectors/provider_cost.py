"""
CloudSage Provider & Account Spend Anomaly Detector.
Monitors provider-wide and account-level daily expenditure deviations.
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


class ProviderAccountSpikeDetector(BaseAnomalyDetector):
    """Detector for macro provider and account-level spending surges."""

    def __init__(self) -> None:
        self._ensemble = StatisticalEnsembleDetector()

    @property
    def detector_id(self) -> str:
        return "provider_account_spike_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> AnomalyCategory:
        return AnomalyCategory.ACCOUNT_SPIKE

    @property
    def supported_dimensions(self) -> List[str]:
        return ["PROVIDER", "ACCOUNT"]

    @property
    def description(self) -> str:
        return "Monitors macro provider-wide and account-level daily expenditure."

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "z_score_threshold": Decimal("2.5000"),
            "modified_z_threshold": Decimal("3.0000"),
            "iqr_multiplier": Decimal("1.5000"),
            "min_excess_cost": Decimal("100.0000"),
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
        if time_series.dimension_type not in ("PROVIDER", "ACCOUNT"):
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                status="CLEAN",
                message="ProviderAccountSpikeDetector only applies to PROVIDER or ACCOUNT dimensions.",
            )

        t = {**self.default_thresholds, **(thresholds or {})}
        res = self._ensemble.detect(time_series, baseline, billing_records, thresholds=t)

        for anom in res.anomalies:
            anom.detector_id = self.detector_id
            anom.detector_version = self.detector_version
            anom.anomaly_category = self.category
            target = time_series.account_id or time_series.provider
            anom.title = f"Macro Spend Spike on {time_series.provider} Account {target}"

        return DetectorExecutionResult(
            detector_id=self.detector_id,
            status=res.status,
            anomalies=res.anomalies,
            message=res.message,
            metrics=res.metrics,
        )
