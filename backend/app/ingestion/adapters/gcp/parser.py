"""
CloudSage GCP Billing Export Row Parser.
Extracts normalized fields from Google Cloud Billing exports (JSON & CSV representations).
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Any, Dict, List, Optional
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.adapters.gcp.mappings import GCP_SERVICE_CATEGORY_MAP
from backend.app.ingestion.base import RawBillingItem


class GCPApiParser:
    """Parses GCP BigQuery Billing export dictionaries."""

    @staticmethod
    def map_service_category(service_desc: str) -> ServiceCategory:
        """Maps GCP service description to canonical ServiceCategory."""
        desc_lower = (service_desc or "").lower().strip()
        for key, category in GCP_SERVICE_CATEGORY_MAP.items():
            if key in desc_lower:
                return category
        return ServiceCategory.OTHER

    @staticmethod
    def parse_gcp_labels(labels_field: Any) -> Dict[str, str]:
        """
        Parses GCP labels which may be:
        - List of dicts: [{'key': 'env', 'value': 'prod'}]
        - Dict: {'env': 'prod'}
        - JSON string
        """
        if not labels_field:
            return {}
        if isinstance(labels_field, dict):
            return {str(k).lower().strip(): str(v).strip() for k, v in labels_field.items() if v}
        
        if isinstance(labels_field, list):
            res = {}
            for item in labels_field:
                if isinstance(item, dict) and "key" in item:
                    res[str(item["key"]).lower().strip()] = str(item.get("value", "")).strip()
            return res

        if isinstance(labels_field, str):
            try:
                parsed = json.loads(labels_field)
                return GCPApiParser.parse_gcp_labels(parsed)
            except Exception:
                pass
        return {}

    @classmethod
    def parse_record(cls, row: Dict[str, Any], row_idx: int = 0) -> RawBillingItem:
        """Converts a GCP dictionary into a RawBillingItem."""
        # 1. Billing Account
        billing_account_id = (
            row.get("billing_account_id")
            or row.get("billingAccountId")
            or "gcp-billing-account"
        ).strip()

        # 2. Project
        project_obj = row.get("project")
        if isinstance(project_obj, dict):
            project_id = project_obj.get("id") or "gcp-default-project"
            project_name = project_obj.get("name")
        else:
            project_id = str(row.get("project_id") or row.get("project.id") or "gcp-default-project")
            project_name = str(row.get("project_name") or row.get("project.name") or project_id)

        # 3. Service & SKU
        service_obj = row.get("service")
        if isinstance(service_obj, dict):
            service_desc = service_obj.get("description") or "Compute Engine"
        else:
            service_desc = str(row.get("service_description") or row.get("service.description") or "Compute Engine")

        sku_obj = row.get("sku")
        if isinstance(sku_obj, dict):
            sku_desc = sku_obj.get("description") or ""
        else:
            sku_desc = str(row.get("sku_description") or row.get("sku.description") or "")

        # 4. Resource Name & Identifier
        resource_obj = row.get("resource")
        if isinstance(resource_obj, dict):
            resource_name = resource_obj.get("name") or resource_obj.get("global_name")
        else:
            resource_name = row.get("resource_name") or row.get("resource.name")

        if not resource_name:
            resource_id = f"//compute.googleapis.com/projects/{project_id}/global/{service_desc.lower().replace(' ', '-')}-{row_idx}"
            friendly_name = f"{service_desc.lower()}-{row_idx}"
        else:
            resource_id = str(resource_name).strip()
            friendly_name = resource_id.split("/")[-1] if "/" in resource_id else resource_id

        # 5. Usage Interval
        start_raw = row.get("usage_start_time") or row.get("usageStartTime")
        end_raw = row.get("usage_end_time") or row.get("usageEndTime") or start_raw

        try:
            usage_start = datetime.fromisoformat(str(start_raw).replace("Z", "+00:00")) if start_raw else datetime.now(timezone.utc)
        except Exception:
            usage_start = datetime.now(timezone.utc)

        try:
            usage_end = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00")) if end_raw else usage_start
        except Exception:
            usage_end = usage_start

        # 6. Usage & Financial Cost (Strict Decimal)
        usage_obj = row.get("usage")
        if isinstance(usage_obj, dict):
            raw_qty = usage_obj.get("amount") or usage_obj.get("amount_in_pricing_units") or "1.0"
            raw_unit = usage_obj.get("pricing_unit") or usage_obj.get("unit") or "HOURS"
        else:
            raw_qty = row.get("usage_amount") or row.get("usage.amount") or "1.0"
            raw_unit = row.get("usage_unit") or row.get("usage.unit") or "HOURS"

        try:
            usage_quantity = Decimal(str(raw_qty).strip())
        except Exception:
            usage_quantity = Decimal("1.0")

        raw_cost = row.get("cost") or "0.0000"
        try:
            gross_cost = Decimal(str(raw_cost).strip())
        except Exception:
            gross_cost = Decimal("0.0000")

        # Deduct credits if present
        credits = row.get("credits")
        credits_sum = Decimal("0.0000")
        if isinstance(credits, list):
            for c in credits:
                if isinstance(c, dict) and "amount" in c:
                    try:
                        credits_sum += Decimal(str(c["amount"]).strip())
                    except Exception:
                        pass
        net_cost = gross_cost + credits_sum  # credits are typically negative numbers in BigQuery export

        currency = (row.get("currency") or "USD").strip().upper()

        # 7. Location / Region
        loc_obj = row.get("location")
        if isinstance(loc_obj, dict):
            region = loc_obj.get("region") or loc_obj.get("location") or "us-central1"
            zone = loc_obj.get("zone")
        else:
            region = str(row.get("location_region") or row.get("location.region") or row.get("location") or "us-central1")
            zone = row.get("location_zone") or row.get("location.zone")

        # 8. Labels
        raw_labels = row.get("labels")
        tags = cls.parse_gcp_labels(raw_labels)

        # 9. Pricing model
        pricing_model = PricingModel.ON_DEMAND
        if any(term in sku_desc.lower() for term in ["commit", "cud"]):
            pricing_model = PricingModel.RESERVED
        elif "spot" in sku_desc.lower() or "preemptible" in sku_desc.lower():
            pricing_model = PricingModel.SPOT

        return RawBillingItem(
            provider=CloudProvider.GCP,
            billing_account_id=billing_account_id,
            subscription_id=project_id,
            resource_id=resource_id,
            resource_name=friendly_name,
            service_category=cls.map_service_category(service_desc),
            service_name=service_desc,
            region=region,
            zone=zone,
            usage_start_time=usage_start,
            usage_end_time=usage_end,
            usage_quantity=usage_quantity,
            usage_unit=str(raw_unit).upper(),
            unblended_cost=net_cost,
            list_cost=gross_cost,
            pricing_model=pricing_model,
            currency=currency,
            tags=tags,
            raw_metadata={k: v for k, v in row.items() if k not in ["labels", "credits"]}
        )
