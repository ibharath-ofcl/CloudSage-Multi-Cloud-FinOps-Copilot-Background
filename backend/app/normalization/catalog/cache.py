"""
CloudSage SKU Catalog Cache.
Provides fast in-memory resolution of service and SKU lookups.
"""

from typing import Dict, Optional, Tuple
from backend.app.normalization.catalog.models import CatalogEntry


class SkuCatalogCache:
    """In-memory cache for catalog resolutions."""

    def __init__(self, max_size: int = 5000):
        self._cache: Dict[Tuple[str, str, Optional[str]], CatalogEntry] = {}
        self.max_size = max_size

    def get(self, provider: str, service_code: str, sku_id: Optional[str] = None) -> Optional[CatalogEntry]:
        key = (provider.upper().strip(), service_code.lower().strip(), sku_id.lower().strip() if sku_id else None)
        return self._cache.get(key)

    def set(self, entry: CatalogEntry) -> None:
        if len(self._cache) >= self.max_size:
            del self._cache[next(iter(self._cache))]
        key = (
            entry.provider.upper().strip(),
            entry.service_code.lower().strip(),
            entry.sku_id.lower().strip() if entry.sku_id else None,
        )
        self._cache[key] = entry

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)
