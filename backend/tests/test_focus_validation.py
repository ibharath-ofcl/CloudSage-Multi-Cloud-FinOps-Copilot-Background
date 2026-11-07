"""
CloudSage FOCUS 1.0 Specification Conformance & Validation Tests.
Validates required, conditional, and optional FOCUS columns, data types, and enum constraints.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from backend.app.models.billing import BillingRecord
from backend.app.normalization.focus.conformance import FocusConformanceEngine
from backend.app.normalization.focus.exporter import FocusExporter
from backend.app.normalization.focus.models import (
    Focus10Record,
    FocusChargeCategory,
    FocusPricingCategory,
    FocusServiceCategory,
)
from backend.app.normalization.focus.validator import Focus10Validator


def test_focus_valid_record_validation():
    """Verify that a compliant FOCUS 1.0 payload passes validation with 100% score."""
    record = {
        "BillingAccountId": "aws-acc-12345",
        "BillingAccountName": "Enterprise Master Billing",
        "BillingCurrency": "USD",
        "ChargeCategory": "Usage",
        "ChargePeriodStart": datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        "ChargePeriodEnd": datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
        "ConsumedQuantity": Decimal("1.0"),
        "ConsumedUnit": "HOURS",
        "BilledCost": Decimal("12.5000"),
        "EffectiveCost": Decimal("12.5000"),
        "ListCost": Decimal("15.0000"),
        "PricingCategory": "On-Demand",
        "ProviderName": "AWS",
        "RegionId": "us-east-1",
        "ResourceId": "arn:aws:ec2:us-east-1:12345:instance/i-0123",
        "ResourceName": "web-server-prod",
        "ResourceType": "aws:ec2:instance",
        "ServiceCategory": "Compute",
        "ServiceName": "AmazonEC2",
        "SubAccountId": "sub-12345",
        "SubAccountName": "Production Operations",
        "Tags": {"environment": "production", "owner": "devops"},
    }

    result = Focus10Validator.validate_record(record)
    assert result.is_compliant is True
    assert result.mandatory_columns_failed == 0
    assert result.compliance_score == Decimal("100.00")


def test_focus_missing_mandatory_field():
    """Verify that omitting a mandatory field flags non-compliance and reduces score."""
    record = {
        # BillingAccountId missing
        "BillingCurrency": "USD",
        "ChargeCategory": "Usage",
        "ChargePeriodStart": datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        "ChargePeriodEnd": datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
        "BilledCost": Decimal("10.00"),
        "EffectiveCost": Decimal("10.00"),
        "PricingCategory": "On-Demand",
        "ProviderName": "AWS",
        "ServiceCategory": "Compute",
        "ServiceName": "AmazonEC2",
    }

    result = Focus10Validator.validate_record(record)
    assert result.is_compliant is False
    assert result.mandatory_columns_failed >= 1
    assert result.compliance_score < Decimal("100.00")


def test_focus_invalid_enums():
    """Verify that invalid enum strings for ChargeCategory or ServiceCategory fail validation."""
    record = {
        "BillingAccountId": "aws-123",
        "BillingCurrency": "USD",
        "ChargeCategory": "InvalidFakeCategory",
        "ChargePeriodStart": datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        "ChargePeriodEnd": datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
        "BilledCost": Decimal("5.00"),
        "EffectiveCost": Decimal("5.00"),
        "PricingCategory": "UnknownPricing",
        "ProviderName": "AWS",
        "ServiceCategory": "FakeServiceCategory",
        "ServiceName": "AmazonEC2",
    }

    result = Focus10Validator.validate_record(record)
    assert result.is_compliant is False
    failing_fields = {d.column_name for d in result.field_details if not d.is_valid}
    assert "ChargeCategory" in failing_fields
    assert "PricingCategory" in failing_fields
    assert "ServiceCategory" in failing_fields


def test_focus_negative_monetary_value():
    """Verify that negative monetary values without adjustment classification are flagged."""
    record = {
        "BillingAccountId": "aws-123",
        "BillingCurrency": "USD",
        "ChargeCategory": "Usage",
        "ChargePeriodStart": datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        "ChargePeriodEnd": datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
        "BilledCost": Decimal("-25.50"),
        "EffectiveCost": Decimal("25.50"),
        "PricingCategory": "On-Demand",
        "ProviderName": "AWS",
        "ServiceCategory": "Compute",
        "ServiceName": "AmazonEC2",
    }

    result = Focus10Validator.validate_record(record)
    assert result.is_compliant is False
    billed_col = next(d for d in result.field_details if d.column_name == "BilledCost")
    assert billed_col.is_valid is False
    assert "cannot be negative" in billed_col.message


def test_focus_exporter_from_billing_record():
    """Verify that FocusExporter correctly maps an internal BillingRecord to FOCUS 1.0 schema."""
    db_rec = BillingRecord(
        provider="AWS",
        billing_account_id="111222333",
        subscription_id="sub-444",
        resource_id="arn:aws:s3:::enterprise-data-lake",
        resource_name="enterprise-data-lake",
        service_category="STORAGE",
        service_name="AmazonS3",
        region="us-west-2",
        usage_start_time=datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        usage_end_time=datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc),
        usage_quantity=Decimal("500.00"),
        usage_unit="GB_MONTH",
        unblended_cost=Decimal("11.5000"),
        blended_cost=Decimal("11.5000"),
        list_cost=Decimal("12.0000"),
        pricing_model="ON_DEMAND",
        currency="USD",
        tags={"environment": "production", "owner": "analytics"},
        raw_metadata={"original_cost": "11.5000", "original_currency": "USD"},
    )

    focus_rec = FocusExporter.from_billing_record(db_rec)
    assert focus_rec.BillingAccountId == "111222333"
    assert focus_rec.ServiceCategory == FocusServiceCategory.STORAGE
    assert focus_rec.PricingCategory == FocusPricingCategory.ON_DEMAND
    assert focus_rec.BilledCost == Decimal("11.5000")
    assert focus_rec.Tags["environment"] == "production"

    # Export dictionary
    focus_dict = FocusExporter.to_focus_dict(db_rec)
    assert focus_dict["ServiceCategory"] == "Storage"
    assert focus_dict["BilledCost"] == Decimal("11.5000")


def test_focus_conformance_matrix_summary():
    """Verify that FocusConformanceEngine accurately calculates summary percentages."""
    valid_record = {
        "BillingAccountId": "aws-acc-1",
        "BillingCurrency": "USD",
        "ChargeCategory": "Usage",
        "ChargePeriodStart": datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        "ChargePeriodEnd": datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
        "BilledCost": Decimal("5.00"),
        "EffectiveCost": Decimal("5.00"),
        "PricingCategory": "On-Demand",
        "ProviderName": "AWS",
        "ServiceCategory": "Compute",
        "ServiceName": "AmazonEC2",
    }
    r1 = Focus10Validator.validate_record(valid_record)
    r2 = Focus10Validator.validate_record(valid_record)

    summary = FocusConformanceEngine.generate_summary([r1, r2])
    assert summary.total_evaluated_records == 2
    assert summary.fully_compliant_count == 2
    assert summary.conformance_percentage >= Decimal("70.00")
    assert len(summary.fully_supported_columns) >= 20
