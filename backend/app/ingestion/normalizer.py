"""
CloudSage Unified Data Normalizer.
Harmonizes heterogeneous multi-cloud billing feeds into the canonical FOCUS 1.0 schema.
Extended in Stage 4 to integrate with historical currency exchange rates,
SKU catalog lookups, advanced tag sanitization, and data quality scoring.
"""

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.base import RawBillingItem
from backend.app.normalization.catalog.lookup import CatalogLookupEngine
from backend.app.normalization.currency.service import CurrencyService
from backend.app.normalization.tags.extractor import TagExtractor
from backend.app.normalization.tags.sanitizer import TagSanitizer
from backend.app.schemas.billing import BillingRecordCreate


class UnifiedNormalizer:
    """Standardizes multi-cloud records to canonical BillingRecord schema."""

    STANDARD_CURRENCY: str = "USD"
    NORMALIZATION_VERSION: str = "1.0.0"
    MAPPING_VERSION: str = "2026.11"

    # Preserved backward-compatible exchange rates mapping
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
    def normalize_currency(
        cls,
        amount: Decimal,
        currency_code: str,
        effective_date: Optional[date] = None,
    ) -> Tuple[Decimal, str]:
        """
        Converts foreign currency amounts into USD using exact Decimal rate multiplication.
        Leverages CurrencyService with historical date-aware lookup.
        """
        curr = (currency_code or cls.STANDARD_CURRENCY).upper().strip()
        if curr == cls.STANDARD_CURRENCY:
            return amount.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP), cls.STANDARD_CURRENCY

        res = CurrencyService.convert_to_usd(
            amount=amount,
            currency_code=curr,
            effective_date=effective_date,
        )
        return res.converted_amount_usd, cls.STANDARD_CURRENCY

    @classmethod
    def normalize_tags(cls, raw_tags: Dict[str, Any]) -> Dict[str, str]:
        """
        Normalizes tag dictionary:
        - Keys converted to lowercase and stripped of provider prefixes.
        - Values stripped of whitespace.
        """
        sanitized, _ = TagSanitizer.sanitize(raw_tags)
        return sanitized

    @classmethod
    def extract_core_metadata(cls, tags: Dict[str, str]) -> Dict[str, Optional[str]]:
        """Extracts standard FinOps metadata attributes from normalized tags."""
        extracted = TagExtractor.extract_metadata(tags)
        return {
            "environment": extracted.get("environment") or "unknown",
            "owner": extracted.get("owner"),
            "cost_center": extracted.get("cost_center"),
            "project": extracted.get("project"),
        }

    @classmethod
    def to_canonical_schema(cls, item: RawBillingItem) -> BillingRecordCreate:
        """Transforms a RawBillingItem into a validated Pydantic BillingRecordCreate."""
        prov_str = item.provider.value if hasattr(item.provider, "value") else str(item.provider)
        ref_date = item.usage_start_time.date() if item.usage_start_time else date.today()

        # Currency normalization using CurrencyService
        conv_unblended = CurrencyService.convert_to_usd(
            amount=item.unblended_cost,
            currency_code=item.currency,
            effective_date=ref_date,
        )
        norm_cost = conv_unblended.converted_amount_usd

        norm_blended = None
        if item.blended_cost is not None:
            conv_blended = CurrencyService.convert_to_usd(
                amount=item.blended_cost,
                currency_code=item.currency,
                effective_date=ref_date,
            )
            norm_blended = conv_blended.converted_amount_usd

        norm_list = None
        if item.list_cost is not None:
            conv_list = CurrencyService.convert_to_usd(
                amount=item.list_cost,
                currency_code=item.currency,
                effective_date=ref_date,
            )
            norm_list = conv_list.converted_amount_usd

        # Catalog lookup for category and usage unit normalization
        catalog_entry = CatalogLookupEngine.resolve_service(
            provider=prov_str,
            service_code=item.service_name,
        )
        resolved_category = item.service_category
        if resolved_category == ServiceCategory.OTHER and catalog_entry.is_known:
            try:
                resolved_category = ServiceCategory(catalog_entry.canonical_category)
            except ValueError:
                resolved_category = ServiceCategory.OTHER

        resolved_unit = CatalogLookupEngine.normalize_unit(item.usage_unit or catalog_entry.normalized_unit)

        # Tag normalization
        clean_tags = cls.normalize_tags(item.tags)

        # Ensure UTC timezone on dates
        start_utc = (
            item.usage_start_time.astimezone(timezone.utc)
            if item.usage_start_time.tzinfo
            else item.usage_start_time.replace(tzinfo=timezone.utc)
        )
        end_utc = (
            item.usage_end_time.astimezone(timezone.utc)
            if item.usage_end_time.tzinfo
            else item.usage_end_time.replace(tzinfo=timezone.utc)
        )

        metadata = dict(item.raw_metadata or {})
        metadata["_normalization_version"] = cls.NORMALIZATION_VERSION
        metadata["_mapping_version"] = cls.MAPPING_VERSION
        metadata["_exchange_rate_source"] = conv_unblended.source
        metadata["_exchange_rate_date"] = str(conv_unblended.effective_date)
        metadata["original_cost"] = str(item.unblended_cost)
        metadata["original_currency"] = (item.currency or "USD").upper().strip()

        return BillingRecordCreate(
            provider=item.provider,
            billing_account_id=item.billing_account_id,
            subscription_id=item.subscription_id,
            resource_id=item.resource_id,
            resource_name=item.resource_name,
            service_category=resolved_category,
            service_name=item.service_name,
            region=item.region,
            zone=item.zone,
            usage_start_time=start_utc,
            usage_end_time=end_utc,
            usage_quantity=item.usage_quantity,
            usage_unit=resolved_unit,
            unblended_cost=norm_cost,
            blended_cost=norm_blended,
            list_cost=norm_list,
            pricing_model=item.pricing_model,
            currency=cls.STANDARD_CURRENCY,
            tags=clean_tags,
            raw_metadata=metadata,
        )
