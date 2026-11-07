"""
Unit Tests for CloudSage Root-Cause Attribution Engine.
Tests contributor ranking, inventory metadata enrichment, factual narrative generation,
and graceful fallback to ROOT_CAUSE_UNKNOWN.
"""

from datetime import date, datetime, time, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.attribution import attribute_anomaly, generate_attribution_narrative
from backend.app.anomaly_detection.models import AnomalyCandidate
from backend.app.core.enums import AnomalyCategory, DetectionMethod, Severity
from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource


def test_attribute_anomaly_dominant_resource(db_session: Session):
    """
    Validates attribution when a dominant resource accounts for > 80% of spend surge.
    Ensures CloudResource inventory tags and metadata are successfully correlated.
    """
    anom_date = date(2026, 10, 15)
    dt = datetime.combine(anom_date, time(12, 0), tzinfo=timezone.utc)

    # 1. Seed CloudResource in inventory
    res = CloudResource(
        resource_id="arn:aws:dynamodb:us-east-1:123456789012:table/OrderEvents",
        provider="AWS",
        account_id="123456789012",
        resource_name="OrderEventsTable",
        service_category="DATABASE",
        service_name="AmazonDynamoDB",
        resource_type="dynamodb:table",
        region="us-east-1",
        status="active",
        owner="payments-lead@company.com",
        environment="production",
        project="CheckoutService",
        cost_center="CC-PAYMENTS",
        tags={"owner": "payments-lead@company.com", "env": "production"},
    )
    db_session.add(res)

    # 2. Seed BillingRecord items for that date
    rec1 = BillingRecord(
        record_id=uuid.uuid4(),
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="123456789012",
        service_category="DATABASE",
        service_name="AmazonDynamoDB",
        region="us-east-1",
        resource_id="arn:aws:dynamodb:us-east-1:123456789012:table/OrderEvents",
        resource_name="OrderEventsTable",
        usage_start_time=dt,
        usage_end_time=dt,
        unblended_cost=Decimal("800.0000"),
        blended_cost=Decimal("800.0000"),
        usage_quantity=Decimal("10000.0000"),
        usage_unit="Requests",
        pricing_model="ON_DEMAND",
    )
    rec2 = BillingRecord(
        record_id=uuid.uuid4(),
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="123456789012",
        service_category="DATABASE",
        service_name="AmazonDynamoDB",
        region="us-east-1",
        resource_id="arn:aws:dynamodb:us-east-1:123456789012:table/UserSessions",
        resource_name="UserSessions",
        usage_start_time=dt,
        usage_end_time=dt,
        unblended_cost=Decimal("200.0000"),
        blended_cost=Decimal("200.0000"),
        usage_quantity=Decimal("1000.0000"),
        usage_unit="Requests",
        pricing_model="ON_DEMAND",
    )
    db_session.add(rec1)
    db_session.add(rec2)
    db_session.commit()

    candidate = AnomalyCandidate(
        detector_id="service_cost_spike_detector",
        detector_version="1.0.0",
        provider="AWS",
        account_id="123456789012",
        service_category="DATABASE",
        service_name="AmazonDynamoDB",
        region="us-east-1",
        anomaly_date=anom_date,
        observed_cost=Decimal("1000.0000"),
        expected_cost=Decimal("200.0000"),
        absolute_deviation=Decimal("800.0000"),
        percentage_deviation=Decimal("400.0000"),
        estimated_excess_cost=Decimal("800.0000"),
        projected_monthly_impact=Decimal("800.0000"),
    )

    attributed = attribute_anomaly(db_session, candidate)

    assert attributed.root_cause_analysis["status"] == "ATTRIBUTED"
    assert len(attributed.contributing_resources) == 2

    top_res = attributed.contributing_resources[0]
    assert top_res["resource_id"] == "arn:aws:dynamodb:us-east-1:123456789012:table/OrderEvents"
    assert top_res["resource_name"] == "OrderEventsTable"
    assert top_res["owner"] == "payments-lead@company.com"
    assert top_res["environment"] == "production"
    assert top_res["share_percentage"] == Decimal("80.0000")
    assert "OrderEventsTable" in attributed.explanation


def test_attribute_anomaly_distributed_unknown(db_session: Session):
    """Validates fallback to ROOT_CAUSE_UNKNOWN when spend is fragmented across many resources."""
    anom_date = date(2026, 10, 16)
    dt = datetime.combine(anom_date, time(12, 0), tzinfo=timezone.utc)

    # 10 small resources, each 10%
    for i in range(10):
        rec = BillingRecord(
            record_id=uuid.uuid4(),
            provider="AWS",
            billing_account_id="123456789012",
            subscription_id="123456789012",
            service_category="STORAGE",
            service_name="AmazonS3",
            region="us-east-1",
            resource_id=f"arn:aws:s3:::bucket-fragmented-{i}",
            usage_start_time=dt,
            usage_end_time=dt,
            unblended_cost=Decimal("50.0000"),
            usage_quantity=Decimal("10.0000"),
            usage_unit="GB",
            pricing_model="ON_DEMAND",
        )
        db_session.add(rec)
    db_session.commit()

    candidate = AnomalyCandidate(
        detector_id="service_cost_spike_detector",
        detector_version="1.0.0",
        provider="AWS",
        account_id="123456789012",
        service_category="STORAGE",
        service_name="AmazonS3",
        region="us-east-1",
        anomaly_date=anom_date,
        observed_cost=Decimal("500.0000"),
        expected_cost=Decimal("100.0000"),
        absolute_deviation=Decimal("400.0000"),
        percentage_deviation=Decimal("400.0000"),
        estimated_excess_cost=Decimal("400.0000"),
        projected_monthly_impact=Decimal("400.0000"),
    )

    attributed = attribute_anomaly(db_session, candidate)

    assert attributed.root_cause_analysis["status"] == "ROOT_CAUSE_UNKNOWN"
    assert "Root cause inconclusive" in attributed.explanation


def test_attribute_anomaly_no_records_fallback(db_session: Session):
    """Validates graceful handling when no underlying line items exist."""
    candidate = AnomalyCandidate(
        detector_id="statistical_ensemble_detector",
        detector_version="1.0.0",
        provider="GCP",
        account_id="prj-missing",
        service_category="COMPUTE",
        service_name="Compute Engine",
        region="us-central1",
        anomaly_date=date(2026, 10, 1),
        observed_cost=Decimal("200.0000"),
        expected_cost=Decimal("50.0000"),
        absolute_deviation=Decimal("150.0000"),
        percentage_deviation=Decimal("300.0000"),
        estimated_excess_cost=Decimal("150.0000"),
        projected_monthly_impact=Decimal("150.0000"),
    )

    attributed = attribute_anomaly(db_session, candidate)
    assert attributed.root_cause_analysis["status"] == "ROOT_CAUSE_UNKNOWN"
    assert attributed.root_cause_analysis["reason"] == "NO_UNDERLYING_BILLING_RECORDS_FOUND"
