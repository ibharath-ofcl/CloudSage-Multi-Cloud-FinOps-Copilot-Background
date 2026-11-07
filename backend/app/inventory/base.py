"""
CloudSage Inventory Base Adapter Interface.
Abstract base class defining the contract for cloud inventory discovery adapters.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
from backend.app.core.enums import CloudProvider
from backend.app.inventory.models import AdapterDiscoveryResult


class BaseInventoryAdapter(ABC):
    """Abstract interface implemented by all hyperscaler inventory discovery adapters."""

    @property
    @abstractmethod
    def provider(self) -> CloudProvider:
        """Returns the cloud provider handled by this adapter."""
        pass

    @abstractmethod
    def parse_export(
        self,
        stream_or_path: Any,
        source_identifier: str = "export",
    ) -> AdapterDiscoveryResult:
        """
        Mode A: Parses an inventory export file (JSON or CSV) and extracts
        normalized resources and relationships.
        """
        pass

    @abstractmethod
    def discover_live(
        self,
        regions: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
    ) -> AdapterDiscoveryResult:
        """
        Mode B: Queries hyperscaler read-only inventory APIs.
        Safely returns missing credential or permission errors if unconfigured.
        """
        pass
