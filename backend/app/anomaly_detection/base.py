"""
CloudSage Base Anomaly Detector Abstract Interface.
Defines contracts for all statistical, change-point, and dimensional anomaly detectors.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from backend.app.anomaly_detection.models import BaselineResult, DetectorExecutionResult, TimeSeries
from backend.app.core.enums import AnomalyCategory
from backend.app.models.billing import BillingRecord


class BaseAnomalyDetector(ABC):
    """Abstract base class for all pluggable cost anomaly detectors."""

    @property
    @abstractmethod
    def detector_id(self) -> str:
        """Unique machine-readable identifier for detector."""
        pass

    @property
    @abstractmethod
    def detector_version(self) -> str:
        """Semantic version of detection logic."""
        pass

    @property
    @abstractmethod
    def category(self) -> AnomalyCategory:
        """Primary classification of anomalies produced by this detector."""
        pass

    @property
    @abstractmethod
    def supported_dimensions(self) -> List[str]:
        """List of supported aggregation dimensions (e.g., ['PROVIDER', 'SERVICE', 'RESOURCE'])."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of detection heuristic."""
        pass

    @property
    @abstractmethod
    def default_thresholds(self) -> Dict[str, Any]:
        """Default operational parameters and statistical thresholds."""
        pass

    @abstractmethod
    def detect(
        self,
        time_series: TimeSeries,
        baseline: Optional[BaselineResult] = None,
        billing_records: Optional[List[BillingRecord]] = None,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> DetectorExecutionResult:
        """
        Evaluates an expenditure time series against a statistical baseline,
        returning any detected anomaly candidates.
        """
        pass

