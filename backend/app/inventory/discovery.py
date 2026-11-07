"""
CloudSage Inventory Discovery Service.
Orchestrates Mode A (Export-Based) and Mode B (Live Cloud API) resource discovery across hyperscalers.
"""

from typing import Any, List, Optional
from backend.app.inventory.base import BaseInventoryAdapter
from backend.app.inventory.models import AdapterDiscoveryResult
from backend.app.inventory.registry import InventoryRegistry


class InventoryDiscoveryService:
    """Dispatches discovery operations to provider adapters."""

    @classmethod
    def discover_from_export(
        cls,
        stream_or_path: Any,
        provider: Optional[str] = None,
        source_identifier: str = "inventory_export.json",
    ) -> AdapterDiscoveryResult:
        """Mode A: Discovers resources and relationships from an inventory export payload."""
        prov = provider
        if not prov:
            prov = InventoryRegistry.detect_provider(stream_or_path)

        if not prov:
            res = AdapterDiscoveryResult(provider="UNKNOWN", source_identifier=source_identifier)
            res.errors.append({"error": "Unable to detect cloud provider from inventory payload"})
            return res

        adapter = InventoryRegistry.get_adapter(prov)
        return adapter.parse_export(stream_or_path, source_identifier=source_identifier)

    @classmethod
    def discover_live(
        cls,
        provider: str,
        regions: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
    ) -> AdapterDiscoveryResult:
        """Mode B: Queries hyperscaler read-only discovery APIs."""
        adapter = InventoryRegistry.get_adapter(provider)
        return adapter.discover_live(regions=regions, resource_types=resource_types)
