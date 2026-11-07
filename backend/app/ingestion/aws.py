"""
CloudSage AWS Ingestion Adapter.
Parses AWS Cost and Usage Reports (CUR 2.0 / legacy CUR CSV feeds) into canonical billing items.
"""

import csv
from datetime import datetime, timezone
from decimal import Decimal
import io
from typing import Any, Dict, Iterator, Optional, Union
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.base import BaseIngestionAdapter, RawBillingItem


class AWSCurIngestionAdapter(BaseIngestionAdapter):
    """Adapter for AWS Cost and Usage Report (CUR) format."""

    def __init__(self):
        super().__init__(provider=CloudProvider.AWS)

    @staticmethod
    def map_service_category(product_code: str) -> ServiceCategory:
        """Maps AWS ProductCode to canonical ServiceCategory."""
        code = product_code.lower().strip()
        if any(k in code for k in ["ec2", "lambda", "ecs", "eks", "fargate"]):
            return ServiceCategory.COMPUTE
        if any(k in code for k in ["s3", "ebs", "glacier", "backup", "elasticfilesystem", "efs"]):
            return ServiceCategory.STORAGE
        if any(k in code for k in ["rds", "dynamodb", "elasticache", "aurora", "neptune", "documentdb"]):
            return ServiceCategory.DATABASE
        if any(k in code for k in ["vpc", "cloudfront", "route53", "elb", "loadbalancing", "natgateway", "directconnect"]):
            return ServiceCategory.NETWORKING
        if any(k in code for k in ["sagemaker", "bedrock", "textract", "rekognition", "comprehend"]):
            return ServiceCategory.AI_ML
        if any(k in code for k in ["redshift", "emr", "athena", "kinesis", "quicksight", "glue"]):
            return ServiceCategory.ANALYTICS
        if any(k in code for k in ["cloudwatch", "cloudtrail", "config", "organizations", "systemsmanager"]):
            return ServiceCategory.MANAGEMENT
        if any(k in code for k in ["kms", "waf", "shield", "secretsmanager", "guardduty"]):
            return ServiceCategory.SECURITY
        return ServiceCategory.OTHER

    @staticmethod
    def map_pricing_model(line_item_type: str) -> PricingModel:
        """Maps AWS lineItem/LineItemType to canonical PricingModel."""
        item_type = line_item_type.lower()
        if "savingsplan" in item_type:
            return PricingModel.SAVINGS_PLAN
        if "discounted" in item_type or "reserved" in item_type:
            return PricingModel.RESERVED
        if "spot" in item_type:
            return PricingModel.SPOT
        return PricingModel.ON_DEMAND

    def parse_stream(self, stream_or_path: Union[str, io.TextIOBase]) -> Iterator[RawBillingItem]:
        """
        Streams and parses AWS CUR CSV format.
        Handles both file path and text streams.
        """
        if isinstance(stream_or_path, str):
            f = open(stream_or_path, mode="r", encoding="utf-8-sig")
            should_close = True
        else:
            f = stream_or_path
            should_close = False

        try:
            reader = csv.DictReader(f)
            for row in reader:
                # 1. Identity & Account IDs
                account_id = (
                    row.get("lineItem/UsageAccountId")
                    or row.get("bill/PayerAccountId")
                    or "unknown-aws-account"
                )
                payer_id = row.get("bill/PayerAccountId") or account_id

                # 2. Resource ID & Name
                resource_id = (
                    row.get("lineItem/ResourceId")
                    or row.get("identity/LineItemId")
                    or f"aws:{account_id}:{row.get('lineItem/ProductCode', 'unknown')}"
                )
                product_code = row.get("lineItem/ProductCode") or row.get("product/servicecode") or "AmazonEC2"
                
                # Derive friendly resource name if ARN provided
                resource_name = resource_id.split("/")[-1] if "/" in resource_id else resource_id

                # 3. Time Parsing
                usage_start_raw = row.get("lineItem/UsageStartDate")
                usage_end_raw = row.get("lineItem/UsageEndDate")

                usage_start = (
                    datetime.fromisoformat(usage_start_raw.replace("Z", "+00:00"))
                    if usage_start_raw else datetime.now(timezone.utc)
                )
                usage_end = (
                    datetime.fromisoformat(usage_end_raw.replace("Z", "+00:00"))
                    if usage_end_raw else usage_start
                )

                # 4. Usage & Costs
                quantity = self.parse_decimal(row.get("lineItem/UsageAmount"), Decimal("1.0"))
                unit = row.get("pricing/unit") or row.get("lineItem/Unit") or "HOURS"
                unblended_cost = self.parse_decimal(row.get("lineItem/UnblendedCost"), Decimal("0.0000"))
                blended_cost = self.parse_decimal(row.get("lineItem/BlendedCost"), None)
                list_cost = self.parse_decimal(row.get("pricing/publicOnDemandCost"), None)
                currency = row.get("lineItem/CurrencyCode") or "USD"

                # 5. Region & Zone
                region = (
                    row.get("product/region")
                    or row.get("product/location")
                    or row.get("lineItem/AvailabilityZone", "us-east-1")
                )
                # Normalize region string
                if region and region.startswith("us-") and len(region) > 9:
                    zone = region
                    region = region[:-1]
                else:
                    zone = row.get("lineItem/AvailabilityZone")

                # 6. Tags Extraction
                tags: Dict[str, Any] = {}
                for key, val in row.items():
                    if val and (key.startswith("resourceTags/user:") or key.startswith("tag:")):
                        clean_key = self.sanitize_tag_key(key)
                        tags[clean_key] = val.strip()

                # Extract standard tags if name exists in tags
                if "name" in tags and not resource_name:
                    resource_name = tags["name"]

                yield RawBillingItem(
                    provider=CloudProvider.AWS,
                    billing_account_id=payer_id,
                    subscription_id=account_id,
                    resource_id=resource_id,
                    resource_name=resource_name,
                    service_category=self.map_service_category(product_code),
                    service_name=product_code,
                    region=region or "global",
                    zone=zone,
                    usage_start_time=usage_start,
                    usage_end_time=usage_end,
                    usage_quantity=quantity,
                    usage_unit=unit.upper(),
                    unblended_cost=unblended_cost,
                    blended_cost=blended_cost,
                    list_cost=list_cost,
                    pricing_model=self.map_pricing_model(row.get("lineItem/LineItemType", "")),
                    currency=currency,
                    tags=tags,
                    raw_metadata={k: v for k, v in row.items() if v and not k.startswith("resourceTags/")}
                )
        finally:
            if should_close:
                f.close()
