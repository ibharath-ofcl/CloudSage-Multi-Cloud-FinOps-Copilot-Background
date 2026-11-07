"""
CloudSage Azure Cost Export Row Parser.
Extracts normalized fields from Azure Cost Management exports.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import re
from typing import Any, Dict, Optional
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.adapters.azure.mappings import (
    AZURE_METER_CATEGORY_MAP,
    AZURE_PRICING_MODEL_MAP,
)
from backend.app.ingestion.base import RawBillingItem


class AzureCostParser:
    """Parses individual records of Microsoft Azure Cost Management exports."""

    @staticmethod
    def map_service_category(meter_category: str) -> ServiceCategory:
        """Maps Azure MeterCategory to canonical ServiceCategory."""
        cat_lower = (meter_category or "").lower().strip()
        for key, category in AZURE_METER_CATEGORY_MAP.items():
            if key in cat_lower:
                return category
        return ServiceCategory.OTHER

    @staticmethod
    def map_pricing_model(pricing_model_str: str) -> PricingModel:
        """Maps Azure pricing model string to canonical enum."""
        cleaned = (pricing_model_str or "ondemand").lower().replace(" ", "").replace("_", "")
        return AZURE_PRICING_MODEL_MAP.get(cleaned, PricingModel.ON_DEMAND)

    @staticmethod
    def parse_azure_tags(raw_tag_str: Any) -> Dict[str, str]:
        """Parses Azure tag strings into dictionary."""
        if not raw_tag_str:
            return {}
        if isinstance(raw_tag_str, dict):
            return {str(k).lower().strip(): str(v).strip() for k, v in raw_tag_str.items() if v}
        
        tag_str = str(raw_tag_str).strip()
        if not tag_str or tag_str == "{}" or tag_str == "null":
            return {}

        # Attempt JSON parse
        if tag_str.startswith("{") and tag_str.endswith("}"):
            try:
                data = json.loads(tag_str)
                return {str(k).lower().strip(): str(v).strip() for k, v in data.items() if v}
            except Exception:
                pass

        # Attempt key: value parse
        tags = {}
        for part in re.split(r'[,;]\s*', tag_str):
            if ":" in part:
                k, v = part.split(":", 1)
                k_clean = k.replace('"', '').replace("'", "").strip().lower()
                v_clean = v.replace('"', '').replace("'", "").strip()
                if k_clean:
                    tags[k_clean] = v_clean
        return tags

    @classmethod
    def get_field(cls, row: Dict[str, Any], *aliases: str) -> Optional[Any]:
        """Case-insensitive flexible lookup across multiple possible column aliases."""
        for alias in aliases:
            if alias in row and row[alias] is not None and str(row[alias]).strip() != "":
                return row[alias]
        # Case-insensitive search
        lower_map = {k.lower(): v for k, v in row.items()}
        for alias in aliases:
            if alias.lower() in lower_map and lower_map[alias.lower()] is not None:
                val = str(lower_map[alias.lower()]).strip()
                if val:
                    return lower_map[alias.lower()]
        return None

    @classmethod
    def parse_row(cls, row: Dict[str, Any], row_idx: int = 0) -> RawBillingItem:
        """Converts an Azure CSV row into a RawBillingItem."""
        # 1. Accounts & Subscriptions
        billing_account_id = str(
            cls.get_field(row, "BillingAccountId", "billingAccountId", "InvoiceSectionId") or "azure-enterprise-agreement"
        ).strip()

        subscription_id = str(
            cls.get_field(row, "SubscriptionId", "subscriptionId", "SubscriptionGuid", "subscriptionGuid") or "default-azure-subscription"
        ).strip()

        resource_group = str(
            cls.get_field(row, "ResourceGroup", "resourceGroupName", "ResourceGroupName") or "default-rg"
        ).strip()

        # 2. Service & Meter
        meter_category = str(
            cls.get_field(row, "MeterCategory", "meterCategory", "ConsumedService") or "Virtual Machines"
        ).strip()

        service_name = str(
            cls.get_field(row, "ConsumedService", "consumedService", "ServiceName") or meter_category
        ).strip()

        # 3. Resource ID
        raw_res_id = cls.get_field(row, "ResourceId", "resourceId")
        if raw_res_id:
            resource_id = str(raw_res_id).strip()
        else:
            resource_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Resources/resource-{row_idx}"

        raw_res_name = cls.get_field(row, "ResourceName", "resourceName")
        if raw_res_name:
            resource_name = str(raw_res_name).strip()
        else:
            resource_name = resource_id.split("/")[-1]

        # 4. Dates
        date_raw = cls.get_field(row, "Date", "date", "UsageDateTime", "usageDateTime", "BillingPeriodStartDate")
        try:
            if date_raw and "T" in str(date_raw):
                usage_start = datetime.fromisoformat(str(date_raw).replace("Z", "+00:00"))
            elif date_raw and "/" in str(date_raw):
                parts = str(date_raw).split("/")
                if len(parts) == 3:
                    m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
                    usage_start = datetime(y, m, d, tzinfo=timezone.utc)
                else:
                    usage_start = datetime.now(timezone.utc)
            elif date_raw:
                usage_start = datetime.fromisoformat(str(date_raw)).replace(tzinfo=timezone.utc)
            else:
                usage_start = datetime.now(timezone.utc)
        except Exception:
            usage_start = datetime.now(timezone.utc)

        usage_end = usage_start

        # 5. Usage Quantity & Cost (Strict Decimal)
        raw_quantity = cls.get_field(row, "Quantity", "quantity", "UsageQuantity", "usageQuantity") or "1.0"
        raw_cost = cls.get_field(row, "CostInBillingCurrency", "costInBillingCurrency", "PreTaxCost", "preTaxCost", "CostInUsd", "cost") or "0.0000"

        try:
            usage_quantity = Decimal(str(raw_quantity).strip())
        except Exception:
            usage_quantity = Decimal("1.0")

        try:
            unblended_cost = Decimal(str(raw_cost).strip())
        except Exception:
            unblended_cost = Decimal("0.0000")

        unit = str(cls.get_field(row, "UnitOfMeasure", "unitOfMeasure") or "Hours").strip()
        currency = str(cls.get_field(row, "BillingCurrency", "billingCurrency", "currency") or "USD").strip().upper()

        # 6. Region
        region = str(cls.get_field(row, "ResourceLocation", "resourceLocation", "Location", "location") or "eastus").strip().lower()

        # 7. Tags
        raw_tags = cls.get_field(row, "Tags", "tags") or {}
        tags = cls.parse_azure_tags(raw_tags)
        if "resource_group" not in tags and resource_group:
            tags["resource_group"] = resource_group

        pricing_tier = str(cls.get_field(row, "PricingModel", "pricingModel", "PricingTier") or "OnDemand")

        return RawBillingItem(
            provider=CloudProvider.AZURE,
            billing_account_id=billing_account_id,
            subscription_id=subscription_id,
            resource_id=resource_id,
            resource_name=resource_name,
            service_category=cls.map_service_category(meter_category),
            service_name=service_name,
            region=region,
            zone=None,
            usage_start_time=usage_start,
            usage_end_time=usage_end,
            usage_quantity=usage_quantity,
            usage_unit=unit.upper(),
            unblended_cost=unblended_cost,
            pricing_model=cls.map_pricing_model(pricing_tier),
            currency=currency,
            tags=tags,
            raw_metadata={k: v for k, v in row.items() if v and k.lower() != "tags"}
        )
