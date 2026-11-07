"""
CloudSage Billing-to-Inventory Financial Correlation Tests.
Verifies multi-cloud cost association, ledger reconciliation, and coverage metrics.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from backend.app.inventory.correlation import BillingCorrelationEngine
from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource


def test_resource_cost_correlation(db_session: Session):
    res_id = "arn:aws:ec2:us-east-1:123456789012:instance/i-correlate"
    resource = CloudResource(
        resource_id=res_id,
        provider="AWS",
        account_id="123456789012",
        resource_name="test-instance",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="active",
        tags={},
        environment="production",
    )
    db_session.add(resource)

    # Add 2 billing records
    now = datetime.now(timezone.utc)
    b1 = BillingRecord(
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="123456789012",
        resource_id=res_id,
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        usage_start_time=now - timedelta(days=2),
        usage_end_time=now - timedelta(days=1),
        usage_quantity=Decimal("24.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("12.5000"),
        pricing_model="ON_DEMAND",
        currency="USD",
        tags={},
    )
    b2 = BillingRecord(
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="123456789012",
        resource_id=res_id,
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        usage_start_time=now - timedelta(days=1),
        usage_end_time=now,
        usage_quantity=Decimal("24.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("12.5000"),
        pricing_model="ON_DEMAND",
        currency="USD",
        tags={},
    )
    db_session.add_all([b1, b2])
    db_session.commit()

    corr = BillingCorrelationEngine.correlate_resource(db=db_session, resource_id=res_id)
    assert corr is not None
    assert corr["total_billed_cost"] == Decimal("25.0000")
    assert corr["billing_record_count"] == 2
    assert corr["correlation_status"] == "CONFIRMED_BILLED"


def test_coverage_summary_and_billing_only_detection(db_session: Session):
    now = datetime.now(timezone.utc)
    # Resource in inventory and billed
    res_in_both = "arn:aws:ec2:us-east-1:123456789012:instance/i-in-both"
    # Resource only in billing (missing from inventory)
    res_billing_only = "arn:aws:ec2:us-east-1:123456789012:instance/i-uninventoried"

    r = CloudResource(
        resource_id=res_in_both,
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="active",
        tags={},
        environment="production",
    )
    db_session.add(r)

    b1 = BillingRecord(
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="123456789012",
        resource_id=res_in_both,
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        usage_start_time=now - timedelta(hours=1),
        usage_end_time=now,
        usage_quantity=Decimal("1.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("80.0000"),
        currency="USD",
        tags={},
    )
    b2 = BillingRecord(
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="123456789012",
        resource_id=res_billing_only,
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        usage_start_time=now - timedelta(hours=1),
        usage_end_time=now,
        usage_quantity=Decimal("1.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("20.0000"),
        currency="USD",
        tags={},
    )
    db_session.add_all([b1, b2])
    db_session.commit()

    cov = BillingCorrelationEngine.get_coverage_summary(db=db_session, provider="AWS")
    assert cov["total_billing_cost"] == Decimal("100.0000")
    assert cov["correlated_billing_cost"] == Decimal("80.0000")
    assert cov["unreconciled_billing_cost"] == Decimal("20.0000")
    assert cov["cost_coverage_percentage"] == Decimal("80.00")
    assert cov["billing_only_resources_count"] == 1


def test_sync_resource_monthly_costs(db_session: Session):
    res_id = "arn:aws:ec2:us-east-1:123456789012:instance/i-monthly-sync"
    res = CloudResource(
        resource_id=res_id,
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="active",
        tags={},
        environment="production",
        monthly_cost=Decimal("0.0000"),
    )
    db_session.add(res)

    now = datetime.now(timezone.utc)
    # Record within 30 days
    b_recent = BillingRecord(
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="123456789012",
        resource_id=res_id,
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        usage_start_time=now - timedelta(days=10),
        usage_end_time=now - timedelta(days=9),
        usage_quantity=Decimal("24.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("45.5000"),
        currency="USD",
        tags={},
    )
    # Record older than 30 days
    b_old = BillingRecord(
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="123456789012",
        resource_id=res_id,
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        usage_start_time=now - timedelta(days=40),
        usage_end_time=now - timedelta(days=39),
        usage_quantity=Decimal("24.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("100.0000"),
        currency="USD",
        tags={},
    )
    db_session.add_all([b_recent, b_old])
    db_session.commit()

    updated = BillingCorrelationEngine.sync_resource_monthly_costs(db=db_session, lookback_days=30)
    assert updated == 1

    db_session.refresh(res)
    assert res.monthly_cost == Decimal("45.5000")
