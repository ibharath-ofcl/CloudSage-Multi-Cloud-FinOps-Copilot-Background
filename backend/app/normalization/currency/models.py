"""
CloudSage Currency Data Structures.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class RateLookupResult:
    """Internal representation of a resolved exchange rate."""
    currency_code: str
    effective_date: date
    rate_to_usd: Decimal
    source: str
    is_interpolated: bool


@dataclass(frozen=True)
class ConversionResult:
    """Represents the complete result of a currency conversion calculation."""
    original_amount: Decimal
    original_currency: str
    converted_amount_usd: Decimal
    target_currency: str
    effective_date: date
    rate_used: Decimal
    source: str
    is_interpolated: bool
    conversion_timestamp: datetime
