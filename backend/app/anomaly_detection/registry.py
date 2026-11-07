"""
CloudSage Anomaly Detector Registry.
Provides registration, lookup, and lifecycle management for all anomaly detectors.
"""

from typing import Dict, List, Optional
from backend.app.anomaly_detection.base import BaseAnomalyDetector
from backend.app.anomaly_detection.detectors import (
    ChangePointDetector,
    NewSpendPatternDetector,
    ProviderAccountSpikeDetector,
    ResourceCostSpikeDetector,
    ServiceCostSpikeDetector,
    StatisticalEnsembleDetector,
    UsagePriceDivergenceDetector,
)


class AnomalyDetectorRegistry:
    """Registry maintaining active cost anomaly detector instances."""

    def __init__(self) -> None:
        self._detectors: Dict[str, BaseAnomalyDetector] = {}

    def register(self, detector: BaseAnomalyDetector) -> None:
        """Registers a detector instance."""
        self._detectors[detector.detector_id] = detector

    def get(self, detector_id: str) -> Optional[BaseAnomalyDetector]:
        """Retrieves a detector by ID."""
        return self._detectors.get(detector_id)

    def list_all(self) -> List[BaseAnomalyDetector]:
        """Lists all registered detectors."""
        return list(self._detectors.values())

    def get_for_dimension(self, dimension_type: str) -> List[BaseAnomalyDetector]:
        """Returns all detectors supporting a specific aggregation dimension."""
        return [
            d for d in self._detectors.values()
            if dimension_type in d.supported_dimensions
        ]

    def initialize_defaults(self) -> None:
        """Initializes all built-in detectors."""
        self.register(StatisticalEnsembleDetector())
        self.register(ChangePointDetector())
        self.register(ServiceCostSpikeDetector())
        self.register(ResourceCostSpikeDetector())
        self.register(ProviderAccountSpikeDetector())
        self.register(UsagePriceDivergenceDetector())
        self.register(NewSpendPatternDetector())


_GLOBAL_REGISTRY: Optional[AnomalyDetectorRegistry] = None


def get_detector_registry() -> AnomalyDetectorRegistry:
    """Returns singleton instance of AnomalyDetectorRegistry."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = AnomalyDetectorRegistry()
        _GLOBAL_REGISTRY.initialize_defaults()
    return _GLOBAL_REGISTRY

