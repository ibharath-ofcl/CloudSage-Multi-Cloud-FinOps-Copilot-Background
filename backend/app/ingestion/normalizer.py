"""
CloudSage Unified Data Normalizer.
Harmonizes heterogeneous multi-cloud billing feeds into the canonical FOCUS 1.0 schema.
"""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.base import RawBillingItem
from backend.app.schemas.billing import BillingRecordCreate


class UnifiedNormalizer:
    """Standardizes multi-cloud records to canonical BillingRecord schema."""

    STANDARD_CURRENCY: str = "USD"
    # Exchange rate lookup table for non-USD currencies (can be extended with live rates)
    EXCHANGE_RATES_TO_USD: Dict[str, Decimal] = {
        "USD": Decimal("1.0000"),
        "EUR": Decimal("1.0850"),
        "GBP": Decimal("1.2950"),
        "CAD": Decimal("0.7250"),
        "AUD": Decimal("0.6600"),
        "JPY": Decimal("0.0067"),
        "INR": Decimal("0.0118"),
    }

    @classmethod
    def normalize_currency(cls, amount: Decimal, currency_code: str) -> Tuple[Decimal, str]:
        """Converts foreign currency amounts into USD using exact Decimal rate multiplication."""
        curr = (currency_code or "USD").upper().strip()
        if curr == cls.STANDARD_CURRENCY:
            return amount, cls.STANDARD_CURRENCY
        
        rate = cls.EXCHANGE_RATES_TO_USD.get(curr, Decimal("1.0000"))
        converted = (amount * rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return converted, cls.STANDARD_CURRENCY

    @classmethod
    def normalize_tags(cls, raw_tags: Dict[str, Any]) -> Dict[str, str]:
        """
        Normalizes tag dictionary:
        - Keys converted to lowercase and stripped of special characters.
        - Values stripped of whitespace.
        - Canonical tags prioritized: 'owner', 'environment', 'project', 'costcenter', 'application'.
        """
        if not raw_tags or not isinstance(raw_tags, dict):
            return {}

        normalized: Dict[str, str] = {}
        for k, v in raw_tags.items():
            if v is None:
                continue
            key_str = str(k).strip().lower()
            # Strip common provider prefix tags
            for prefix in ["resourcetags/user:", "user:", "tag:", "labels/"]:
                if key_str.startswith(prefix):
                    key_str = key_str[len(prefix):]
            
            clean_key = key_str.replace("-", "_").replace(" ", "_")
            normalized[clean_key] = str(v).strip()

        return normalized

    @classmethod
    def extract_core_metadata(cls, tags: Dict[str, str]) -> Dict[str, Optional[str]]:
        """Extracts standard FinOps metadata attributes from normalized tags."""
        env = tags.get("environment") or tags.get("env") or "unknown"
        owner = tags.get("owner") or tags.get("team") or tags.get("creator")
        cost_center = tags.get("costcenter") or tags.get("cost_center") or tags.get("department")
        project = tags.get("project") or tags.get("app") or tags.get("application")

        return {
            "environment": env.lower() if env else "unknown",
            "owner": owner,
            "cost_center": cost_center,
            "project": project,
        }

    @classmethod
    def to_canonical_schema(cls, item: RawBillingItem) -> BillingRecordCreate:
        """Transforms a RawBillingItem into a validated Pydantic BillingRecordCreate."""
        # Currency normalization
        norm_cost, norm_curr = cls.normalize_currency(item.unblended_cost, item.currency)
        norm_blended = None
        if item.blended_cost is not None:
            norm_blended, _ = cls.normalize_currency(item.blended_cost, item.currency)
        norm_list = None
        if item.list_cost is not None:
            norm_list, _ = cls.normalize_currency(item.list_cost, item.currency)

        # Tag normalization
        clean_tags = cls.normalize_tags(item.tags)

        # Ensure UTC timezone on dates
        start_utc = item.usage_start_time.astimezone(timezone.utc) if item.usage_start_time.tzinfo else item.usage_start_time.replace(tzinfo=timezone.utc)
        end_utc = item.usage_end_time.astimezone(timezone.utc) if item.usage_end_time.tzinfo else item.usage_end_time.replace(tzinfo=timezone.utc)

        return BillingRecordCreate(
            provider=item.provider,
            billing_account_id=item.billing_account_id,
            subscription_id=item.subscription_id,
            resource_id=item.resource_id,
            resource_name=item.resource_name,
            service_category=item.service_category,
            service_name=item.service_name,
            region=item.region,
            zone=item.zone,
            usage_start_time=start_utc,
            usage_end_time=end_utc,
            usage_quantity=item.usage_quantity,
            usage_unit=item.usage_unit.upper(),
            unblended_cost=norm_cost,
            blended_cost=norm_blended,
            list_cost=norm_list,
            pricing_model=item.pricing_model,
            currency=norm_curr,
            tags=clean_tags,
            raw_metadata=item.raw_metadata,
        )
