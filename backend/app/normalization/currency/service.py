"""
CloudSage Currency Normalization Service.
Coordinates cache, database, and fallback providers to convert foreign currencies to USD.
Enforces strict Decimal arithmetic and precision rules.
"""

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.normalization.currency.cache import ExchangeRateCache
from backend.app.normalization.currency.exceptions import (
    ExchangeRateUnavailableError,
    UnsupportedCurrencyError,
)
from backend.app.normalization.currency.models import ConversionResult, RateLookupResult
from backend.app.normalization.currency.providers import (
    DatabaseExchangeRateProvider,
    StaticFallbackProvider,
)


class CurrencyService:
    """Enterprise Currency Normalization and FX Management Service."""

    _cache = ExchangeRateCache()
    _static_provider = StaticFallbackProvider()

    @classmethod
    def get_rate(
        cls,
        currency_code: str,
        target_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> RateLookupResult:
        """
        Resolves exchange rate to USD for a given currency and date.
        Order of resolution:
        1. In-memory cache
        2. Database lookup (with business-day rollback)
        3. Static fallback provider
        """
        curr = (currency_code or "USD").upper().strip()
        ref_date = target_date or date.today()

        if curr == "USD":
            return RateLookupResult(
                currency_code="USD",
                effective_date=ref_date,
                rate_to_usd=Decimal("1.000000"),
                source="IDENTITY",
                is_interpolated=False,
            )

        # 1. Check in-memory cache
        cached = cls._cache.get(curr, ref_date)
        if cached:
            return cached

        # 2. Check Database if session provided
        if db:
            db_provider = DatabaseExchangeRateProvider(db)
            db_result = db_provider.get_rate(curr, ref_date)
            if db_result:
                cls._cache.set(curr, ref_date, db_result)
                return db_result

        # 3. Check Static Fallback Provider
        static_result = cls._static_provider.get_rate(curr, ref_date)
        if static_result:
            cls._cache.set(curr, ref_date, static_result)
            return static_result

        raise ExchangeRateUnavailableError(
            f"No exchange rate found for currency '{curr}' on date '{ref_date}'"
        )

    @classmethod
    def convert_to_usd(
        cls,
        amount: Decimal,
        currency_code: str,
        effective_date: Optional[date] = None,
        db: Optional[Session] = None,
    ) -> ConversionResult:
        """
        Converts monetary amount to USD using Decimal multiplication.
        Guarantees zero floating point arithmetic.
        """
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))

        curr = (currency_code or "USD").upper().strip()
        ref_date = effective_date or date.today()

        rate_info = cls.get_rate(curr, ref_date, db=db)
        converted = (amount * rate_info.rate_to_usd).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

        return ConversionResult(
            original_amount=amount,
            original_currency=curr,
            converted_amount_usd=converted,
            target_currency="USD",
            effective_date=rate_info.effective_date,
            rate_used=rate_info.rate_to_usd,
            source=rate_info.source,
            is_interpolated=rate_info.is_interpolated,
            conversion_timestamp=datetime.now(timezone.utc),
        )

    @classmethod
    def register_manual_rate(
        cls,
        currency_code: str,
        effective_date: date,
        rate_to_usd: Decimal,
        source: str = "MANUAL_ENTRY",
    ) -> RateLookupResult:
        """Injects or overrides a rate in the cache."""
        result = RateLookupResult(
            currency_code=currency_code.upper().strip(),
            effective_date=effective_date,
            rate_to_usd=rate_to_usd,
            source=source,
            is_interpolated=False,
        )
        cls._cache.set(currency_code, effective_date, result)
        return result

    @classmethod
    def clear_cache(cls) -> None:
        """Clears cached rates (useful for test isolation)."""
        cls._cache.clear()
