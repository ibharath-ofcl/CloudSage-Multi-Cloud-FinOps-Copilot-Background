"""
Tests for 10-Dimensional Cost Decomposition Engine.
Verifies complete coverage across:
Provider, Account, Region, Service, Resource ID, SKU, Environment, Owner, Cost Center, Billing Tags.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest

from backend.app.investigation.dimension_analysis import DimensionAnalysisEngine
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource


def _setup_anomaly_and_records(db_session):
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        resource_id="i-001",
        anomaly_category="SERVICE_SPIKE",
        anomaly_date=date(2026, 3, 15),
        actual_cost=Decimal("1500.0000"),
        expected_cost=Decimal("500.0000"),
        estimated_excess_cost=Decimal("1000.0000"),
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)

    # Add cloud resource
    res = CloudResource(
        resource_id="i-001",
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        environment="production",
        owner="data-platform",
        cost_center="CC-DATA-402",
        monthly_cost=Decimal("1500.0000"),
        status="active",
        tags={"environment": "production", "owner": "data-platform", "cost_center": "CC-DATA-402", "app": "data-lake"},
    )
    db_session.add(res)

    # Add billing records on anomaly date
    b1 = BillingRecord(
        record_id=uuid.uuid4(),
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="123456789012",
        resource_id="i-001",
        resource_name="prod-worker-1",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        usage_start_time=datetime(2026, 3, 15, 1, 0, 0, tzinfo=timezone.utc),
        usage_end_time=datetime(2026, 3, 15, 2, 0, 0, tzinfo=timezone.utc),
        usage_quantity=Decimal("100.0000"),
        usage_unit="HOURS",
        unblended_cost=Decimal("1000.0000"),
        pricing_model="ON_DEMAND",
        tags={"environment": "production", "owner": "data-platform", "cost_center": "CC-DATA-402", "app": "data-lake"},
        raw_metadata={"line_item_description": "c5.4xlarge compute instances"},
    )
    b2 = BillingRecord(
        record_id=uuid.uuid4(),
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="123456789012",
        resource_id="i-002",
        resource_name="prod-worker-2",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        usage_start_time=datetime(2026, 3, 15, 3, 0, 0, tzinfo=timezone.utc),
        usage_end_time=datetime(2026, 3, 15, 4, 0, 0, tzinfo=timezone.utc),
        usage_quantity=Decimal("50.0000"),
        usage_unit="HOURS",
        unblended_cost=Decimal("500.0000"),
        pricing_model="ON_DEMAND",
        tags={"environment": "production", "owner": "data-platform", "cost_center": "CC-DATA-402", "app": "data-lake"},
        raw_metadata={"line_item_description": "c5.2xlarge compute instances"},
    )
    db_session.add(b1)
    db_session.add(b2)
    db_session.commit()
    return anomaly


def test_ten_dimensions_present(db_session):
    """Verifies that all 10 canonical dimensions are analyzed and returned."""
    anomaly = _setup_anomaly_and_records(db_session)
    res = DimensionAnalysisEngine.analyze_dimensions(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    expected_dims = {
        "PROVIDER",
        "ACCOUNT",
        "REGION",
        "SERVICE",
        "RESOURCE_ID",
        "SKU",
        "ENVIRONMENT",
        "OWNER",
        "COST_CENTER",
        "BILLING_TAGS",
    }
    assert set(res.dimensions.keys()) == expected_dims
    assert res.total_excess_cost == Decimal("1000.0000")


def test_provider_and_service_decomposition(db_session):
    """Verifies provider and service dimensions aggregate billing correctly."""
    anomaly = _setup_anomaly_and_records(db_session)
    res = DimensionAnalysisEngine.analyze_dimensions(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    prov_contribs = res.dimensions["PROVIDER"]
    assert len(prov_contribs) >= 1
    assert prov_contribs[0].dimension_value == "AWS"
    assert prov_contribs[0].actual_cost == Decimal("1500.0000")

    srv_contribs = res.dimensions["SERVICE"]
    assert len(srv_contribs) >= 1
    assert srv_contribs[0].dimension_value == "AmazonEC2"


def test_resource_id_decomposition(db_session):
    """Verifies resource-level slice identifies individual instances."""
    anomaly = _setup_anomaly_and_records(db_session)
    res = DimensionAnalysisEngine.analyze_dimensions(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    res_contribs = res.dimensions["RESOURCE_ID"]
    assert len(res_contribs) == 2
    # First contributor is i-001 with 1000 USD
    assert res_contribs[0].dimension_value == "i-001"
    assert res_contribs[0].actual_cost == Decimal("1000.0000")
    # Second contributor is i-002 with 500 USD
    assert res_contribs[1].dimension_value == "i-002"
    assert res_contribs[1].actual_cost == Decimal("500.0000")


def test_environment_and_owner_tags(db_session):
    """Verifies tags like environment and owner are extracted and grouped."""
    anomaly = _setup_anomaly_and_records(db_session)
    res = DimensionAnalysisEngine.analyze_dimensions(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    env_contribs = res.dimensions["ENVIRONMENT"]
    assert len(env_contribs) >= 1
    assert env_contribs[0].dimension_value == "production"

    owner_contribs = res.dimensions["OWNER"]
    assert len(owner_contribs) >= 1
    assert owner_contribs[0].dimension_value == "data-platform"

    cc_contribs = res.dimensions["COST_CENTER"]
    assert len(cc_contribs) >= 1
    assert cc_contribs[0].dimension_value == "CC-DATA-402"


def test_dominant_dimension_selection(db_session):
    """Verifies dominant dimension corresponds to the axis with highest concentration."""
    anomaly = _setup_anomaly_and_records(db_session)
    res = DimensionAnalysisEngine.analyze_dimensions(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )
    assert res.dominant_dimension in DimensionAnalysisEngine.DIMENSIONS


def test_fallback_when_billing_records_sparse(db_session):
    """Verifies graceful fallback when no line-items exist in database."""
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="GCP",
        account_id="gcp-prod-analytics",
        service_category="DATABASE",
        service_name="BigQuery",
        region="us-central1",
        resource_id="bq-analytics-cluster",
        anomaly_category="SERVICE_SPIKE",
        anomaly_date=date(2026, 3, 10),
        actual_cost=Decimal("3000.0000"),
        expected_cost=Decimal("600.0000"),
        estimated_excess_cost=Decimal("2400.0000"),
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)
    db_session.commit()

    res = DimensionAnalysisEngine.analyze_dimensions(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    assert len(res.dimensions) == 10
    assert res.dimensions["PROVIDER"][0].dimension_value == "GCP"
    assert res.dimensions["SERVICE"][0].dimension_value == "BigQuery"
    assert res.dimensions["RESOURCE_ID"][0].dimension_value == "bq-analytics-cluster"
    assert res.total_excess_cost == Decimal("2400.0000")


def test_anti_double_counting(db_session):
    """Verifies each dimension independently sums to its total without double-counting."""
    anomaly = _setup_anomaly_and_records(db_session)
    res = DimensionAnalysisEngine.analyze_dimensions(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    for dim_name, contribs in res.dimensions.items():
        total_actual = sum((c.actual_cost for c in contribs), Decimal("0.0000"))
        assert total_actual == Decimal("1500.0000"), f"Dimension {dim_name} actual sum mismatch"
