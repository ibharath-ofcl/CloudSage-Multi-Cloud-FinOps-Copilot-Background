"""
CloudSage Currency Normalization & Historical FX Tests.
Verifies multi-currency conversions, Decimal precision, historical lookups, and cache behavior.
"""

from datetime import date, timedelta
from decimal import Decimal
import pytest
from backend.app.models.normalization import ExchangeRate
from backend.app.normalization.currency.exceptions import ExchangeRateUnavailableError
from backend.app.normalization.currency.service import CurrencyService


def test_currency_usd_identity_conversion():
    """Verify that USD amounts convert with 1.0 multiplier and identity source."""
    amount = Decimal("123.4567")
    result = CurrencyService.convert_to_usd(amount, "USD")
    assert result.converted_amount_usd == Decimal("123.4567")
    assert result.original_currency == "USD"
    assert result.target_currency == "USD"
    assert result.rate_used == Decimal("1.000000")
    assert result.source == "IDENTITY"
    assert result.is_interpolated is False


def test_currency_foreign_conversions_decimal_precision():
    """Verify conversions from EUR, GBP, INR, JPY maintain strict Decimal precision."""
    # EUR conversion: 100 EUR * 1.0850 = 108.5000 USD
    eur_result = CurrencyService.convert_to_usd(Decimal("100.00"), "EUR")
    assert eur_result.converted_amount_usd == Decimal("108.5000")
    assert eur_result.rate_used == Decimal("1.085000")

    # GBP conversion: 50 GBP * 1.2950 = 64.7500 USD
    gbp_result = CurrencyService.convert_to_usd(Decimal("50.00"), "GBP")
    assert gbp_result.converted_amount_usd == Decimal("64.7500")

    # INR conversion: 100,000 INR * 0.0118 = 1,180.0000 USD
    inr_result = CurrencyService.convert_to_usd(Decimal("100000.00"), "INR")
    assert inr_result.converted_amount_usd == Decimal("1180.0000")

    # JPY conversion: 10,000 JPY * 0.0067 = 67.0000 USD
    jpy_result = CurrencyService.convert_to_usd(Decimal("10000.00"), "JPY")
    assert jpy_result.converted_amount_usd == Decimal("67.0000")


def test_currency_historical_rate_and_interpolation(db_session):
    """Verify historical date lookup and preceding business day rollback for weekends."""
    CurrencyService.clear_cache()
    friday_date = date(2026, 11, 6)   # Friday
    sunday_date = date(2026, 11, 8)   # Sunday (Weekend)

    # Insert a specific Friday exchange rate in the DB for EUR
    db_rate = ExchangeRate(
        currency_code="EUR",
        effective_date=friday_date,
        rate_to_usd=Decimal("1.105000"),
        source="ECB_HISTORICAL",
        is_interpolated=False,
    )
    db_session.add(db_rate)
    db_session.commit()

    # Exact date lookup on Friday
    fri_res = CurrencyService.convert_to_usd(Decimal("100.00"), "EUR", effective_date=friday_date, db=db_session)
    assert fri_res.converted_amount_usd == Decimal("110.5000")
    assert fri_res.source == "ECB_HISTORICAL"
    assert fri_res.is_interpolated is False

    # Sunday lookup: should rollback to Friday's rate and flag is_interpolated=True
    CurrencyService.clear_cache()
    sun_res = CurrencyService.convert_to_usd(Decimal("100.00"), "EUR", effective_date=sunday_date, db=db_session)
    assert sun_res.converted_amount_usd == Decimal("110.5000")
    assert sun_res.is_interpolated is True
    assert "INTERPOLATED" in sun_res.source


def test_currency_cache_performance_and_clear():
    """Verify that multiple lookups hit the in-memory cache."""
    CurrencyService.clear_cache()
    today = date.today()

    res1 = CurrencyService.convert_to_usd(Decimal("100.00"), "CAD", effective_date=today)
    res2 = CurrencyService.convert_to_usd(Decimal("200.00"), "CAD", effective_date=today)

    assert res1.rate_used == res2.rate_used
    assert CurrencyService._cache.get("CAD", today) is not None

    CurrencyService.clear_cache()
    assert CurrencyService._cache.get("CAD", today) is None


def test_currency_unknown_rate_error():
    """Verify that an unsupported currency without fallback raises ExchangeRateUnavailableError."""
    CurrencyService.clear_cache()
    # Temporarily remove fallback rates
    original_rates = CurrencyService._static_provider.rates
    CurrencyService._static_provider.rates = {}

    try:
        with pytest.raises(ExchangeRateUnavailableError) as exc_info:
            CurrencyService.convert_to_usd(Decimal("100.00"), "XYZ", effective_date=date(2026, 1, 1))
        assert "No exchange rate found" in str(exc_info.value)
    finally:
        CurrencyService._static_provider.rates = original_rates
