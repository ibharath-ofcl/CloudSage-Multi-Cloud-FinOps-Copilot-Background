"""
CloudSage Currency Normalization Exceptions.
"""


class CurrencyError(Exception):
    """Base exception for currency operations."""
    pass


class UnsupportedCurrencyError(CurrencyError):
    """Raised when an unknown or invalid currency code is supplied."""
    pass


class ExchangeRateUnavailableError(CurrencyError):
    """Raised when an exchange rate for a given currency and date cannot be resolved."""
    pass


class ProviderConnectionError(CurrencyError):
    """Raised when an external exchange rate provider API cannot be reached."""
    pass
