"""
CloudSage Exchange Rate Providers.
Implements rate lookup providers with static fallback, database queries, and simulated external feeds.
"""

from abc import ABC, abstractmethod
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy.orm import Session
from backend.app.models.normalization import ExchangeRate
from backend.app.normalization.currency.exceptions import (
    ExchangeRateUnavailableError,
    UnsupportedCurrencyError,
)
from backend.app.normalization.currency.models import RateLookupResult


# Comprehensive baseline reference rates to USD (1 Foreign Unit = X USD)
STATIC_REFERENCE_RATES_TO_USD: Dict[str, Decimal] = {
    "USD": Decimal("1.000000"),
    "EUR": Decimal("1.085000"),
    "GBP": Decimal("1.295000"),
    "CAD": Decimal("0.725000"),
    "AUD": Decimal("0.660000"),
    "JPY": Decimal("0.006700"),
    "INR": Decimal("0.011800"),
    "CHF": Decimal("1.125000"),
    "BRL": Decimal("0.174000"),
    "SGD": Decimal("0.748000"),
    "SEK": Decimal("0.093000"),
    "NZD": Decimal("0.595000"),
    "ZAR": Decimal("0.054000"),
    "AED": Decimal("0.272300"),
    "SAR": Decimal("0.266500"),
}


class BaseExchangeRateProvider(ABC):
    """Abstract interface for foreign exchange rate providers."""

    @abstractmethod
    def get_rate(self, currency_code: str, target_date: date) -> Optional[RateLookupResult]:
        """Resolves rate to USD for currency and target date."""
        pass


class DatabaseExchangeRateProvider(BaseExchangeRateProvider):
    """Retrieves exchange rates persisted in the database with business day rollback."""

    def __init__(self, db: Session):
        self.db = db

    def get_rate(self, currency_code: str, target_date: date) -> Optional[RateLookupResult]:
        curr = currency_code.upper().strip()
        if curr == "USD":
            return RateLookupResult(
                currency_code="USD",
                effective_date=target_date,
                rate_to_usd=Decimal("1.000000"),
                source="IDENTITY",
                is_interpolated=False,
            )

        # 1. Exact date lookup
        exact = (
            self.db.query(ExchangeRate)
            .filter(
                ExchangeRate.currency_code == curr,
                ExchangeRate.effective_date == target_date,
            )
            .first()
        )
        if exact:
            return RateLookupResult(
                currency_code=curr,
                effective_date=exact.effective_date,
                rate_to_usd=exact.rate_to_usd,
                source=exact.source,
                is_interpolated=exact.is_interpolated,
            )

        # 2. Preceding business day rollback (up to 7 days for holidays/weekends)
        for offset in range(1, 8):
            prev_date = target_date - timedelta(days=offset)
            prev_rate = (
                self.db.query(ExchangeRate)
                .filter(
                    ExchangeRate.currency_code == curr,
                    ExchangeRate.effective_date == prev_date,
                )
                .first()
            )
            if prev_rate:
                return RateLookupResult(
                    currency_code=curr,
                    effective_date=prev_date,
                    rate_to_usd=prev_rate.rate_to_usd,
                    source=f"{prev_rate.source}_INTERPOLATED",
                    is_interpolated=True,
                )

        return None


class StaticFallbackProvider(BaseExchangeRateProvider):
    """
    Deterministic static reference rate provider.
    Guarantees offline test stability and reliable fallbacks.
    """

    def __init__(self, rates: Optional[Dict[str, Decimal]] = None):
        self.rates = rates or STATIC_REFERENCE_RATES_TO_USD

    def get_rate(self, currency_code: str, target_date: date) -> Optional[RateLookupResult]:
        curr = currency_code.upper().strip()
        if curr not in self.rates:
            return None

        return RateLookupResult(
            currency_code=curr,
            effective_date=target_date,
            rate_to_usd=self.rates[curr],
            source="STATIC_REFERENCE",
            is_interpolated=False,
        )
