"""
CloudSage AWS CUR Row Parser.
Extracts normalized fields from raw AWS CUR dictionaries.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.adapters.aws.mappings import (
    AWS_PRICING_MODEL_MAP,
    AWS_SERVICE_CATEGORY_MAP,
)
from backend.app.ingestion.base import RawBillingItem


class AWSCurParser:
    """Parses individual rows of AWS Cost & Usage Reports."""

    @staticmethod
    def map_service_category(product_code: str) -> ServiceCategory:
        """Determines category based on product code prefix matching."""
        normalized = (product_code or "AmazonEC2").lower().replace(" ", "").replace("_", "")
        for key, cat in AWS_SERVICE_CATEGORY_MAP.items():
            if key in normalized:
                return cat
        return ServiceCategory.OTHER

    @staticmethod
    def map_pricing_model(line_item_type: str) -> PricingModel:
        """Maps AWS LineItemType string to canonical enum."""
        cleaned = (line_item_type or "usage").lower().replace(" ", "").replace("_", "")
        return AWS_PRICING_MODEL_MAP.get(cleaned, PricingModel.ON_DEMAND)

    @classmethod
    def parse_row(cls, row: Dict[str, Any], row_idx: int = 0) -> RawBillingItem:
        """Converts an AWS CUR CSV dictionary into a RawBillingItem."""
        # 1. Accounts
        account_id = (
            row.get("lineItem/UsageAccountId")
            or row.get("bill/PayerAccountId")
            or row.get("UsageAccountId")
            or "unknown-aws-account"
        ).strip()
        payer_id = (
            row.get("bill/PayerAccountId")
            or row.get("PayerAccountId")
            or account_id
        ).strip()

        # 2. Service
        product_code = (
            row.get("lineItem/ProductCode")
            or row.get("product/servicecode")
            or row.get("ProductCode")
            or "AmazonEC2"
        ).strip()

        # 3. Resource ID and Name
        resource_id = (
            row.get("lineItem/ResourceId")
            or row.get("identity/LineItemId")
            or row.get("ResourceId")
            or f"arn:aws:{product_code.lower()}:{account_id}:resource-{row_idx}"
        ).strip()

        resource_name = resource_id.split("/")[-1] if "/" in resource_id else resource_id

        # 4. Dates
        usage_start_raw = (
            row.get("lineItem/UsageStartDate")
            or row.get("UsageStartDate")
            or row.get("identity/TimeInterval", "").split("/")[0]
        )
        usage_end_raw = (
            row.get("lineItem/UsageEndDate")
            or row.get("UsageEndDate")
            or (row.get("identity/TimeInterval", "").split("/")[1] if "/" in row.get("identity/TimeInterval", "") else "")
        )

        try:
            usage_start = datetime.fromisoformat(usage_start_raw.replace("Z", "+00:00")) if usage_start_raw else datetime.now(timezone.utc)
        except Exception:
            usage_start = datetime.now(timezone.utc)

        try:
            usage_end = datetime.fromisoformat(usage_end_raw.replace("Z", "+00:00")) if usage_end_raw else usage_start
        except Exception:
            usage_end = usage_start

        # 5. Usage & Costs (Strict Decimal)
        raw_quantity = row.get("lineItem/UsageAmount") or row.get("UsageAmount") or "1.0"
        raw_cost = row.get("lineItem/UnblendedCost") or row.get("UnblendedCost") or "0.0000"
        raw_blended = row.get("lineItem/BlendedCost") or row.get("BlendedCost")

        try:
            usage_quantity = Decimal(str(raw_quantity).strip())
        except Exception:
            usage_quantity = Decimal("1.0")

        try:
            unblended_cost = Decimal(str(raw_cost).strip())
        except Exception:
            unblended_cost = Decimal("0.0000")

        blended_cost = None
        if raw_blended:
            try:
                blended_cost = Decimal(str(raw_blended).strip())
            except Exception:
                pass

        unit = (row.get("pricing/unit") or row.get("lineItem/Unit") or row.get("Unit") or "HOURS").strip()
        currency = (row.get("lineItem/CurrencyCode") or row.get("CurrencyCode") or "USD").strip().upper()

        # 6. Region & Zone
        region = (
            row.get("product/region")
            or row.get("product/location")
            or row.get("lineItem/AvailabilityZone", "us-east-1")
            or "us-east-1"
        ).strip()
        zone = row.get("lineItem/AvailabilityZone")

        # 7. Tags
        tags: Dict[str, Any] = {}
        for k, v in row.items():
            if v and (k.startswith("resourceTags/user:") or k.startswith("tag:") or k.startswith("user:")):
                clean_k = k.lower().replace("resourcetags/user:", "").replace("user:", "").replace("tag:", "").strip()
                tags[clean_k] = str(v).strip()

        if "name" in tags:
            resource_name = tags["name"]

        line_item_type = row.get("lineItem/LineItemType") or row.get("LineItemType") or "Usage"

        return RawBillingItem(
            provider=CloudProvider.AWS,
            billing_account_id=payer_id,
            subscription_id=account_id,
            resource_id=resource_id,
            resource_name=resource_name,
            service_category=cls.map_service_category(product_code),
            service_name=product_code,
            region=region,
            zone=zone,
            usage_start_time=usage_start,
            usage_end_time=usage_end,
            usage_quantity=usage_quantity,
            usage_unit=unit.upper(),
            unblended_cost=unblended_cost,
            blended_cost=blended_cost,
            pricing_model=cls.map_pricing_model(line_item_type),
            currency=currency,
            tags=tags,
            raw_metadata={k: v for k, v in row.items() if v and not k.startswith("resourceTags/")}
        )
