"""
CloudSage SKU Catalog Data Models.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class CatalogEntry:
    """Represents a canonical service and SKU resolution entry."""
    provider: str
    service_code: str
    sku_id: Optional[str]
    canonical_category: str
    service_family: str
    resource_type: str
    normalized_unit: str
    pricing_model_default: Optional[str]
    confidence: Decimal
    provenance: str
    is_known: bool
