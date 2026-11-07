"""
CloudSage Specialized Waste Detectors Package.
"""

from backend.app.waste_detection.detectors.idle_compute import IdleComputeDetector
from backend.app.waste_detection.detectors.orphaned_snapshots import OrphanedSnapshotsDetector
from backend.app.waste_detection.detectors.oversized_compute import OversizedComputeDetector
from backend.app.waste_detection.detectors.unattached_storage import UnattachedStorageDetector
from backend.app.waste_detection.detectors.underutilized_database import UnderutilizedDatabaseDetector
from backend.app.waste_detection.detectors.unused_network_resources import UnusedNetworkResourcesDetector
from backend.app.waste_detection.detectors.wasteful_spending import BillingBasedWasteDetector

# Aliases
OrphanedSnapshotDetector = OrphanedSnapshotsDetector
UnusedNetworkDetector = UnusedNetworkResourcesDetector
WastefulSpendingDetector = BillingBasedWasteDetector

__all__ = [
    "IdleComputeDetector",
    "OversizedComputeDetector",
    "UnattachedStorageDetector",
    "OrphanedSnapshotsDetector",
    "OrphanedSnapshotDetector",
    "UnderutilizedDatabaseDetector",
    "UnusedNetworkResourcesDetector",
    "UnusedNetworkDetector",
    "BillingBasedWasteDetector",
    "WastefulSpendingDetector",
]
