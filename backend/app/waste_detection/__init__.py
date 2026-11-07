"""CloudSage FinOps - Waste Detection Engine Package.

Provides multi-cloud waste detection across AWS, Azure, and GCP.
Strictly advisory; calculates potential savings with Decimal precision.
"""

from backend.app.waste_detection.base import BaseWasteDetector
from backend.app.waste_detection.detectors import (
    IdleComputeDetector,
    OversizedComputeDetector,
    UnattachedStorageDetector,
    OrphanedSnapshotDetector,
    UnderutilizedDatabaseDetector,
    UnusedNetworkDetector,
    WastefulSpendingDetector,
)
from backend.app.waste_detection.engine import WasteDetectionEngine
from backend.app.waste_detection.evidence import EvidenceValidator
from backend.app.waste_detection.models import DetectorExecutionResult, WasteFinding
from backend.app.waste_detection.registry import DetectorRegistry, detector_registry
from backend.app.waste_detection.savings import SavingsCalculator
from backend.app.waste_detection.severity import SeverityEvaluator
from backend.app.waste_detection.synthetic import SyntheticWasteScenarioGenerator

__all__ = [
    "BaseWasteDetector",
    "DetectorRegistry",
    "detector_registry",
    "WasteDetectionEngine",
    "SavingsCalculator",
    "EvidenceValidator",
    "SeverityEvaluator",
    "SyntheticWasteScenarioGenerator",
    "WasteFinding",
    "DetectorExecutionResult",
    "IdleComputeDetector",
    "OversizedComputeDetector",
    "UnattachedStorageDetector",
    "OrphanedSnapshotDetector",
    "UnderutilizedDatabaseDetector",
    "UnusedNetworkDetector",
    "WastefulSpendingDetector",
]
