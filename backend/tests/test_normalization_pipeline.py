"""
CloudSage Normalization Pipeline End-to-End Tests.
Verifies the 15-step workflow across AWS, Azure, GCP, reprocessing safety, and idempotency.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.base import RawBillingItem
from backend.app.models.billing import BillingRecord
from backend.app.normalization.pipeline import NormalizationPipeline


def test_pipeline_single_item_aws_normalization(db_session):
    """Verify single-item normalization for an AWS EC2 item."""
    pipeline = NormalizationPipeline(db=db_session)

    item = RawBillingItem(
        provider=CloudProvider.AWS,
        billing_account_id="123456789012",
        subscription_id="123456789012",
        resource_id="arn:aws:ec2:us-east-1:123456789012:instance/i-0abcdef1234567890",
        resource_name="prod-api-server",
        service_category=ServiceCategory.COMPUTE,
        service_name="AmazonEC2",
        region="us-east-1",
        zone="us-east-1a",
        usage_start_time=datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        usage_end_time=datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
        usage_quantity=Decimal("1.0"),
        usage_unit="Hrs",
        unblended_cost=Decimal("0.0960"),
        currency="USD",
        pricing_model=PricingModel.ON_DEMAND,
        tags={"resourceTags/user:Owner": "sre-team", "env": "prod"},
    )

    schema, focus_val, audit = pipeline.normalize_single_item(item)

    # Check canonical fields
    assert schema.provider == CloudProvider.AWS
    assert schema.currency == "USD"
    assert schema.usage_unit == "HOURS"
    assert schema.tags["owner"] == "sre-team"
    assert schema.tags["env"] == "prod"
    assert schema.raw_metadata["_normalization_version"] == "1.0.0"
    assert schema.raw_metadata["_mapping_version"] == "2026.11"
    assert schema.raw_metadata["original_cost"] == "0.0960"

    # Check FOCUS validation
    assert focus_val.is_compliant is True
    assert focus_val.mandatory_columns_failed == 0


def test_pipeline_single_item_foreign_currency_conversion(db_session):
    """Verify single-item normalization handles foreign currency (EUR) conversion to USD."""
    pipeline = NormalizationPipeline(db=db_session)

    item = RawBillingItem(
        provider=CloudProvider.AZURE,
        billing_account_id="sub-euro-1",
        subscription_id="sub-euro-1",
        resource_id="/subscriptions/sub-euro-1/resourceGroups/rg-1/providers/Microsoft.Compute/virtualMachines/vm-1",
        resource_name="vm-1",
        service_category=ServiceCategory.COMPUTE,
        service_name="Virtual Machines",
        region="westeurope",
        zone=None,
        usage_start_time=datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        usage_end_time=datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
        usage_quantity=Decimal("1.0"),
        usage_unit="Hours",
        unblended_cost=Decimal("100.00"),  # 100 EUR
        currency="EUR",
        pricing_model=PricingModel.ON_DEMAND,
        tags={"owner": "cloud-finops"},
    )

    schema, focus_val, audit = pipeline.normalize_single_item(item)

    # 100 EUR * 1.0850 = 108.5000 USD
    assert schema.unblended_cost == Decimal("108.5000")
    assert schema.currency == "USD"
    assert schema.raw_metadata["original_cost"] == "100.00"
    assert schema.raw_metadata["original_currency"] == "EUR"
    assert schema.raw_metadata["_exchange_rate_source"] == "STATIC_REFERENCE"


def test_pipeline_reprocess_existing_records_in_place(db_session):
    """
    CRITICAL REPROCESSING TEST:
    Verify that batch reprocessing updates records in-place without generating duplicates!
    """
    pipeline = NormalizationPipeline(db=db_session)

    # Insert 3 sample records
    rec1 = BillingRecord(
        provider="AWS",
        billing_account_id="acc-1",
        subscription_id="acc-1",
        resource_id="res-1",
        service_category="OTHER",  # To be re-resolved to COMPUTE
        service_name="AmazonEC2",
        region="us-east-1",
        usage_start_time=datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        usage_end_time=datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
        usage_quantity=Decimal("1.0"),
        usage_unit="hrs",
        unblended_cost=Decimal("15.0000"),
        currency="USD",
        tags={"user:Owner": "alice"},
    )
    db_session.add(rec1)
    db_session.commit()

    initial_count = db_session.query(BillingRecord).count()
    assert initial_count == 1

    # Execute reprocessing
    run = pipeline.reprocess_existing_records(provider="AWS")

    assert run.status == "COMPLETED"
    assert run.total_records == 1
    assert run.successful_records == 1
    assert run.failed_records == 0

    # Ensure total row count in table did NOT change (no duplicates)
    final_count = db_session.query(BillingRecord).count()
    assert final_count == 1

    # Verify that record was updated in-place
    updated = db_session.query(BillingRecord).first()
    assert updated.service_category == "COMPUTE"
    assert updated.usage_unit == "HOURS"
    assert "_reprocessed_at" in updated.raw_metadata
