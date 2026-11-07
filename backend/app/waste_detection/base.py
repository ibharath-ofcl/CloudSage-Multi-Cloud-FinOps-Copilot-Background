"""
CloudSage Waste Detector Base Interface.
Defines the standard contract implemented by all specialized waste detectors.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from backend.app.core.enums import WasteType
from backend.app.models.billing import BillingRecord
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.waste_detection.models import DetectorExecutionResult


class BaseWasteDetector(ABC):
    """Abstract interface for multi-cloud waste detection heuristics."""

    @property
    @abstractmethod
    def detector_id(self) -> str:
        """Unique machine identifier for this detector."""
        pass

    @property
    @abstractmethod
    def detector_version(self) -> str:
        """Semantic version of the detector logic."""
        pass

    @property
    @abstractmethod
    def waste_category(self) -> WasteType:
        """Canonical waste category emitted by this detector."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable explanation of detector purpose and methodology."""
        pass

    @property
    @abstractmethod
    def supported_providers(self) -> List[str]:
        """Hyperscalers evaluated by this detector (AWS, AZURE, GCP)."""
        pass

    @property
    @abstractmethod
    def supported_resource_types(self) -> List[str]:
        """Specific resource types or service categories evaluated."""
        pass

    @property
    @abstractmethod
    def default_thresholds(self) -> Dict[str, Any]:
        """Configurable detection thresholds and observation windows."""
        pass

    @abstractmethod
    def detect(
        self,
        resource: CloudResource,
        metrics: List[ResourceMetric],
        relationships: List[ResourceRelationship],
        billing_records: List[BillingRecord],
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> DetectorExecutionResult:
        """
        Executes evidence-based evaluation of a cloud resource.
        Returns DetectorExecutionResult with status DETECTED, CLEAN, INSUFFICIENT_DATA, or ERROR.
        """
        pass
