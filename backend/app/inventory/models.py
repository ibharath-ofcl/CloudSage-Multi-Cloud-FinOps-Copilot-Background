"""
CloudSage Inventory Internal Data Structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class DiscoveredResource:
    """Canonical in-memory representation of a discovered cloud asset."""
    resource_id: str
    provider: str
    account_id: str
    service_category: str
    service_name: str
    resource_type: str
    region: str
    resource_name: Optional[str] = None
    zone: Optional[str] = None
    status: str = "active"
    tags: Dict[str, str] = field(default_factory=dict)
    raw_tags: Dict[str, Any] = field(default_factory=dict)
    owner: Optional[str] = None
    department: Optional[str] = None
    project: Optional[str] = None
    environment: str = "unknown"
    cost_center: Optional[str] = None
    tag_quality_score: Decimal = Decimal("0.00")
    resource_created_at: Optional[datetime] = None
    discovery_source: str = "INVENTORY_EXPORT"
    discovery_status: str = "CONFIRMED"
    resource_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveredRelationship:
    """Canonical in-memory representation of a discovered relationship between two resources."""
    source_resource_id: str
    target_resource_id: str
    relationship_type: str
    provider: str
    discovery_source: str = "INVENTORY_DISCOVERY"
    confidence: Decimal = Decimal("1.0000")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterDiscoveryResult:
    """Result returned by an inventory provider adapter."""
    provider: str
    source_identifier: str = "export"
    resources: List[DiscoveredResource] = field(default_factory=list)
    relationships: List[DiscoveredRelationship] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
