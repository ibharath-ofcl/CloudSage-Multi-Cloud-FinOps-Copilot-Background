"""
CloudSage FOCUS 1.0 Exporter.
Transforms canonical database BillingRecord instances into FOCUS 1.0 compliant exports.
"""

from typing import Any, Dict
from backend.app.models.billing import BillingRecord
from backend.app.normalization.focus.models import (
    Focus10Record,
    FocusChargeCategory,
    FocusPricingCategory,
    FocusServiceCategory,
)


class FocusExporter:
    """Exports CloudSage internal models to FOCUS 1.0 standard representation."""

    SERVICE_CATEGORY_MAP = {
        "COMPUTE": FocusServiceCategory.COMPUTE,
        "STORAGE": FocusServiceCategory.STORAGE,
        "DATABASE": FocusServiceCategory.DATABASE,
        "NETWORKING": FocusServiceCategory.NETWORK,
        "ANALYTICS": FocusServiceCategory.ANALYTICS,
        "AI_ML": FocusServiceCategory.AI_AND_ML,
        "SECURITY": FocusServiceCategory.SECURITY,
        "MANAGEMENT": FocusServiceCategory.MANAGEMENT_AND_GOV,
        "OTHER": FocusServiceCategory.OTHER,
    }

    PRICING_MODEL_MAP = {
        "ON_DEMAND": FocusPricingCategory.ON_DEMAND,
        "RESERVED": FocusPricingCategory.COMMITTED,
        "SAVINGS_PLAN": FocusPricingCategory.COMMITTED,
        "SPOT": FocusPricingCategory.SPOT,
        "OTHER": FocusPricingCategory.OTHER,
    }

    @classmethod
    def from_billing_record(cls, record: BillingRecord) -> Focus10Record:
        """Converts an internal BillingRecord to a Focus10Record."""
        srv_cat = cls.SERVICE_CATEGORY_MAP.get(
            record.service_category.upper(), FocusServiceCategory.OTHER
        )
        pricing_cat = cls.PRICING_MODEL_MAP.get(
            record.pricing_model.upper(), FocusPricingCategory.ON_DEMAND
        )

        raw_meta = record.raw_metadata or {}
        orig_cost = raw_meta.get("original_cost") or record.unblended_cost
        orig_curr = raw_meta.get("original_currency") or record.currency
        fingerprint = raw_meta.get("_fingerprint")

        return Focus10Record(
            BillingAccountId=record.billing_account_id,
            BillingAccountName=None,
            BillingCurrency="USD",
            BillingPeriodStart=record.usage_start_time,
            BillingPeriodEnd=record.usage_end_time,
            ChargeCategory=FocusChargeCategory.USAGE,
            ChargePeriodStart=record.usage_start_time,
            ChargePeriodEnd=record.usage_end_time,
            ConsumedQuantity=record.usage_quantity,
            ConsumedUnit=record.usage_unit,
            BilledCost=record.unblended_cost,
            EffectiveCost=record.blended_cost or record.unblended_cost,
            ListCost=record.list_cost or record.unblended_cost,
            PricingCategory=pricing_cat,
            ProviderName=record.provider,
            PublisherName=record.provider,
            RegionId=record.region,
            RegionName=record.region,
            ResourceId=record.resource_id,
            ResourceName=record.resource_name or record.resource_id,
            ResourceType=f"{record.provider.lower()}:{record.service_name.lower()}",
            ServiceCategory=srv_cat,
            ServiceName=record.service_name,
            SubAccountId=record.subscription_id,
            Tags=record.tags or {},
            x_OriginalCost=orig_cost,
            x_OriginalCurrency=orig_curr,
            x_Fingerprint=fingerprint,
        )

    @classmethod
    def to_focus_dict(cls, record: BillingRecord) -> Dict[str, Any]:
        """Convenience method returning serialized dictionary with FOCUS 1.0 keys."""
        return cls.from_billing_record(record).model_dump(by_alias=True)
