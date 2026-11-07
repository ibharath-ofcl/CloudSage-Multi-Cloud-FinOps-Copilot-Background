"""
CloudSage GCP Ingestion Adapter Unit Tests.
Category C: BigQuery JSON/CSV format, nested labels, credits, and decimal precision.
"""

from decimal import Decimal
import io
import json
import pytest
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.adapters.gcp.adapter import GCPApiAdapter
from backend.app.ingestion.adapters.gcp.parser import GCPApiParser


def test_gcp_valid_json_parsing_with_credits():
    json_data = [
        {
            "billing_account_id": "01ABCD-23EFGH-45IJKL",
            "project": {"id": "gcp-prod-checkout", "name": "Checkout Production"},
            "service": {"id": "6F81-5844-456A", "description": "Compute Engine"},
            "sku": {"id": "SKU-001", "description": "Instance Core running in Americas"},
            "usage_start_time": "2026-11-01T00:00:00Z",
            "usage_end_time": "2026-11-01T01:00:00Z",
            "cost": 10.0000,
            "currency": "USD",
            "usage": {"amount": 2.0, "unit": "hour"},
            "location": {"location": "us-central1", "region": "us-central1", "zone": "us-central1-a"},
            "resource": {"name": "//compute.googleapis.com/projects/gcp-prod-checkout/zones/us-central1-a/instances/worker-01"},
            "labels": [{"key": "owner", "value": "checkout-team"}, {"key": "env", "value": "prod"}],
            "credits": [{"name": "Sustained Usage Discount", "amount": -2.0000}]
        }
    ]
    adapter = GCPApiAdapter()
    stream = io.StringIO(json.dumps(json_data))
    items = list(adapter.parse_stream(stream))

    assert len(items) == 1
    item = items[0]
    assert item.provider == CloudProvider.GCP
    assert item.billing_account_id == "01ABCD-23EFGH-45IJKL"
    assert item.subscription_id == "gcp-prod-checkout"
    assert item.service_category == ServiceCategory.COMPUTE
    assert item.service_name == "Compute Engine"
    assert item.resource_id == "//compute.googleapis.com/projects/gcp-prod-checkout/zones/us-central1-a/instances/worker-01"
    # Net cost should be 10.0000 - 2.0000 = 8.0000
    assert item.unblended_cost == Decimal("8.0000")
    assert isinstance(item.unblended_cost, Decimal)
    assert item.list_cost == Decimal("10.0000")
    assert item.tags["owner"] == "checkout-team"
    assert item.tags["env"] == "prod"


def test_gcp_jsonl_stream_parsing():
    """Verifies that newline-delimited JSON (JSONL as exported by BigQuery) is supported."""
    line1 = json.dumps({
        "billing_account_id": "01ABCD-23EFGH-45IJKL",
        "project": {"id": "gcp-data-lake"},
        "service": {"description": "Cloud Storage"},
        "usage_start_time": "2026-11-01T00:00:00Z",
        "cost": 5.2500,
        "currency": "USD",
        "usage": {"amount": 100.0, "unit": "gibibyte month"},
        "labels": {"team": "analytics"}
    })
    line2 = json.dumps({
        "billing_account_id": "01ABCD-23EFGH-45IJKL",
        "project": {"id": "gcp-data-lake"},
        "service": {"description": "BigQuery"},
        "usage_start_time": "2026-11-01T00:00:00Z",
        "cost": 12.5000,
        "currency": "USD",
        "usage": {"amount": 2.5, "unit": "tebibyte"},
        "labels": {"team": "analytics"}
    })
    jsonl_data = f"{line1}\n{line2}\n"

    adapter = GCPApiAdapter()
    stream = io.StringIO(jsonl_data)
    items = list(adapter.parse_stream(stream))

    assert len(items) == 2
    assert items[0].service_category == ServiceCategory.STORAGE
    assert items[0].unblended_cost == Decimal("5.2500")
    assert items[1].service_category == ServiceCategory.ANALYTICS
    assert items[1].unblended_cost == Decimal("12.5000")


def test_gcp_csv_export_parsing():
    """Verifies support for flattened GCP CSV billing exports."""
    csv_data = """billing_account_id,project_id,service_description,sku_description,usage_start_time,usage_end_time,cost,currency,location_region,labels
01ABCD-23EFGH-45IJKL,gcp-web,Cloud SQL,PostgreSQL Standard,2026-11-01T00:00:00Z,2026-11-01T01:00:00Z,1.4500,USD,us-central1,"{""owner"": ""backend""}"
"""
    adapter = GCPApiAdapter()
    stream = io.StringIO(csv_data)
    items = list(adapter.parse_stream(stream))

    assert len(items) == 1
    item = items[0]
    assert item.service_category == ServiceCategory.DATABASE
    assert item.service_name == "Cloud SQL"
    assert item.unblended_cost == Decimal("1.4500")
    assert item.tags["owner"] == "backend"
