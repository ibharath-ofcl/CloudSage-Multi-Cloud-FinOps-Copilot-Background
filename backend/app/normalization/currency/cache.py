"""
CloudSage Exchange Rate Cache.
Provides fast in-memory rate lookups to prevent redundant database queries.
"""

from datetime import date
from typing import Dict, Optional, Tuple
from backend.app.normalization.currency.models import RateLookupResult


class ExchangeRateCache:
    """Thread-safe in-memory cache for resolved exchange rates."""

    def __init__(self, max_size: int = 5000):
        self._cache: Dict[Tuple[str, date], RateLookupResult] = {}
        self.max_size = max_size

    def get(self, currency_code: str, target_date: date) -> Optional[RateLookupResult]:
        key = (currency_code.upper().strip(), target_date)
        return self._cache.get(key)

    def set(self, currency_code: str, target_date: date, result: RateLookupResult) -> None:
        if len(self._cache) >= self.max_size:
            # Evict first key (simple FIFO eviction)
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        key = (currency_code.upper().strip(), target_date)
        self._cache[key] = result

    def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)
