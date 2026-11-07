"""
CloudSage Multi-Cloud Resource Inventory & Intelligence Engine.
Provides hyperscaler adapters, topology extraction, reconciliation,
financial correlation, and inventory quality evaluation.
"""

from backend.app.inventory.base import BaseInventoryAdapter
from backend.app.inventory.correlation import BillingCorrelationEngine
from backend.app.inventory.discovery import InventoryDiscoveryService
from backend.app.inventory.models import (
    AdapterDiscoveryResult,
    DiscoveredRelationship,
    DiscoveredResource,
)
from backend.app.inventory.quality import InventoryQualityEvaluator
from backend.app.inventory.reconciliation import InventoryReconciliationEngine
from backend.app.inventory.registry import InventoryRegistry
from backend.app.inventory.service import InventoryService
from backend.app.inventory.synthetic import SyntheticInventoryGenerator

__all__ = [
    "BaseInventoryAdapter",
    "BillingCorrelationEngine",
    "InventoryDiscoveryService",
    "AdapterDiscoveryResult",
    "DiscoveredRelationship",
    "DiscoveredResource",
    "InventoryQualityEvaluator",
    "InventoryReconciliationEngine",
    "InventoryRegistry",
    "InventoryService",
    "SyntheticInventoryGenerator",
]
