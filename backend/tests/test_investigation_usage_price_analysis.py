"""
Tests for Economic Growth Accounting Usage vs. Price Cost Decomposition Engine.
Formula: Delta Cost = (Delta Q * P_0) + (Delta P * Q_0) + (Delta Q * Delta P).
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest

from backend.app.investigation.usage_price_analysis import UsagePriceAnalysisEngine
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord


def test_usage_volume_driven_surge(db_session):
    """When consumption quantity surges at steady rates, primary driver is USAGE_DRIVEN."""
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        resource_id="i-worker-cluster",
        anomaly_category="USAGE_SPIKE",
        anomaly_date=date(2026, 3, 15),
        actual_cost=Decimal("2000.0000"),
        expected_cost=Decimal("500.0000"),
        estimated_excess_cost=Decimal("1500.0000"),
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)

    # Billing record with 20000 hours at 0.10 USD/hr
    b = BillingRecord(
        record_id=uuid.uuid4(),
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="123456789012",
        resource_id="i-worker-cluster",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        usage_start_time=datetime(2026, 3, 15, 0, 0, 0, tzinfo=timezone.utc),
        usage_end_time=datetime(2026, 3, 15, 23, 59, 59, tzinfo=timezone.utc),
        usage_quantity=Decimal("20000.0000"),
        usage_unit="HOURS",
        unblended_cost=Decimal("2000.0000"),
        pricing_model="ON_DEMAND",
    )
    db_session.add(b)
    db_session.commit()

    res = UsagePriceAnalysisEngine.decompose(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    assert res.total_excess_cost == Decimal("1500.0000")
    assert res.primary_cost_driver == "USAGE_DRIVEN"
    assert res.usage_effect > res.price_effect
    # Sum of effects matches total excess cost
    total_decomposed = res.usage_effect + res.price_effect + res.mix_or_quantity_effect + res.unclassified_effect
    assert total_decomposed == res.total_excess_cost


def test_price_rate_driven_surge(db_session):
    """When SKU or rate-card changes with constant usage, primary driver is PRICE_DRIVEN."""
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="DATABASE",
        service_name="AmazonRDS",
        region="us-east-1",
        resource_id="rds-db-instance",
        anomaly_category="SKU_PRICE_CHANGE",
        anomaly_date=date(2026, 3, 15),
        actual_cost=Decimal("3000.0000"),
        expected_cost=Decimal("1000.0000"),
        estimated_excess_cost=Decimal("2000.0000"),
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)
    db_session.commit()

    res = UsagePriceAnalysisEngine.decompose(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    assert res.total_excess_cost == Decimal("2000.0000")
    assert res.primary_cost_driver == "PRICE_DRIVEN"
    assert res.price_effect > res.usage_effect


def test_net_new_resource_driver(db_session):
    """When expected cost is zero, primary driver is classified as NEW_RESOURCE."""
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AZURE",
        account_id="sub-prod-01",
        service_category="COMPUTE",
        service_name="VirtualMachines",
        region="eastus",
        resource_id="vm-new-cluster-01",
        anomaly_category="NEW_SPEND",
        anomaly_date=date(2026, 3, 15),
        actual_cost=Decimal("800.0000"),
        expected_cost=Decimal("0.0000"),
        estimated_excess_cost=Decimal("800.0000"),
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)
    db_session.commit()

    res = UsagePriceAnalysisEngine.decompose(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    assert res.primary_cost_driver == "NEW_RESOURCE"
    assert res.total_excess_cost == Decimal("800.0000")


def test_decomposition_categories_breakdown(db_session):
    """Verifies all 4 economic decomposition buckets are returned."""
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        resource_id="i-cluster",
        anomaly_category="SERVICE_SPIKE",
        anomaly_date=date(2026, 3, 15),
        actual_cost=Decimal("1200.0000"),
        expected_cost=Decimal("400.0000"),
        estimated_excess_cost=Decimal("800.0000"),
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)
    db_session.commit()

    res = UsagePriceAnalysisEngine.decompose(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    cats = [item.category for item in res.decomposition_breakdown]
    assert "USAGE_EFFECT" in cats
    assert "PRICE_EFFECT" in cats
    assert "MIX_OR_QUANTITY_EFFECT" in cats
    assert "UNCLASSIFIED_EFFECT" in cats
