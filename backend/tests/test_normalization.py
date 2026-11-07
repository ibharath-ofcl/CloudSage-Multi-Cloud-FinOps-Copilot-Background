"""
CloudSage Unified Normalization Unit Tests.
Category D: Cross-cloud canonical schema compliance, currency conversion, tag sanitization.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.base import RawBillingItem
from backend.app.ingestion.normalizer import UnifiedNormalizer


def test_currency_conversion_to_usd():
    """Verifies that non-USD currencies convert to USD with exact Decimal arithmetic."""
    # 100 EUR at rate 1.0850 = 108.5000 USD
    cost_eur = Decimal("100.0000")
    usd_amount, curr = UnifiedNormalizer.normalize_currency(cost_eur, "EUR")
    assert curr == "USD"
    assert usd_amount == Decimal("108.5000")

    # USD returns identical value
    cost_usd = Decimal("42.5000")
    usd_same, curr_same = UnifiedNormalizer.normalize_currency(cost_usd, "USD")
    assert curr_same == "USD"
    assert usd_same == cost_usd


def test_tag_sanitization_and_canonical_extraction():
    """Verifies prefix stripping, lowercasing, and core metadata extraction."""
    raw_tags = {
        "resourceTags/user:Owner": "Data-Platform",
        "tag:Environment": "PRODUCTION ",
        "Cost-Center": "CC-901",
        "Project": "FinOps-Copilot",
        "UPPERCASE_TAG": "Value_123",
    }
    cleaned = UnifiedNormalizer.normalize_tags(raw_tags)
    assert cleaned["owner"] == "Data-Platform"
    assert cleaned["environment"] == "PRODUCTION"
    assert cleaned["cost_center"] == "CC-901"
    assert cleaned["project"] == "FinOps-Copilot"
    assert cleaned["uppercase_tag"] == "Value_123"

    core = UnifiedNormalizer.extract_core_metadata(cleaned)
    assert core["owner"] == "Data-Platform"
    assert core["environment"] == "production"
    assert core["cost_center"] == "CC-901"


def test_raw_to_canonical_schema_transformation():
    """Verifies full transformation of RawBillingItem to validated BillingRecordCreate."""
    raw = RawBillingItem(
        provider=CloudProvider.AWS,
        billing_account_id="112233445566",
        subscription_id="112233445566",
        resource_id="arn:aws:ec2:us-east-1:112233445566:instance/i-norm-01",
        resource_name="web-01",
        service_category=ServiceCategory.COMPUTE,
        service_name="AmazonEC2",
        region="us-east-1",
        zone="us-east-1a",
        usage_start_time=datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
        usage_end_time=datetime(2026, 11, 1, 1, 0, 0, tzinfo=timezone.utc),
        usage_quantity=Decimal("1.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("0.1920"),
        currency="USD",
        tags={"resourceTags/user:owner": "web-squad"}
    )
    canonical = UnifiedNormalizer.to_canonical_schema(raw)
    assert canonical.provider == CloudProvider.AWS
    assert canonical.unblended_cost == Decimal("0.1920")
    assert canonical.currency == "USD"
    assert canonical.tags["owner"] == "web-squad"
    assert canonical.usage_start_time.tzinfo is not None
