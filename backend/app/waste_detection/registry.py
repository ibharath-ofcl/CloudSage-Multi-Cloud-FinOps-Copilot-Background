"""
CloudSage Waste Detector Registry.
Central registry for pluggable multi-cloud waste detection heuristics.
"""

from typing import Dict, List, Optional
from backend.app.core.enums import WasteType
from backend.app.waste_detection.base import BaseWasteDetector
from backend.app.waste_detection.detectors.idle_compute import IdleComputeDetector
from backend.app.waste_detection.detectors.orphaned_snapshots import OrphanedSnapshotsDetector
from backend.app.waste_detection.detectors.oversized_compute import OversizedComputeDetector
from backend.app.waste_detection.detectors.unattached_storage import UnattachedStorageDetector
from backend.app.waste_detection.detectors.underutilized_database import UnderutilizedDatabaseDetector
from backend.app.waste_detection.detectors.unused_network_resources import UnusedNetworkResourcesDetector
from backend.app.waste_detection.detectors.wasteful_spending import BillingBasedWasteDetector


class DetectorRegistry:
    """Registry maintaining active detection heuristics."""

    _detectors: Dict[str, BaseWasteDetector] = {}

    @classmethod
    def initialize_defaults(cls) -> None:
        """Initializes default suite of 7 multi-cloud waste detectors."""
        defaults = [
            IdleComputeDetector(),
            OversizedComputeDetector(),
            UnattachedStorageDetector(),
            OrphanedSnapshotsDetector(),
            UnderutilizedDatabaseDetector(),
            UnusedNetworkResourcesDetector(),
            BillingBasedWasteDetector(),
        ]
        cls._detectors = {d.detector_id: d for d in defaults}

    @classmethod
    def register(cls, detector: BaseWasteDetector) -> None:
        """Registers a custom or extended waste detector."""
        cls._detectors[detector.detector_id] = detector

    @classmethod
    def get_detector(cls, detector_id: str) -> BaseWasteDetector:
        """Retrieves a detector by its unique ID."""
        if not cls._detectors:
            cls.initialize_defaults()
        if detector_id not in cls._detectors:
            raise ValueError(f"No waste detector registered with ID: '{detector_id}'")
        return cls._detectors[detector_id]

    @classmethod
    def list_detectors(
        cls,
        provider: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[BaseWasteDetector]:
        """Lists active detectors matching optional provider or category criteria."""
        if not cls._detectors:
            cls.initialize_defaults()

        detectors = list(cls._detectors.values())
        if provider:
            p_upper = provider.upper()
            detectors = [d for d in detectors if p_upper in d.supported_providers or "ALL" in d.supported_providers]
        if category:
            cat_upper = category.upper()
            detectors = [d for d in detectors if d.waste_category.value == cat_upper or d.waste_category.name == cat_upper]

        return detectors


# Initialize on import
DetectorRegistry.initialize_defaults()
detector_registry = DetectorRegistry
