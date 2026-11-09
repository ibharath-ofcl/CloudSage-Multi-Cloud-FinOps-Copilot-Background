"""
Tests for Resource Topology, Telemetry Metrics, and Cross-Signal Correlation Engine.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest

from backend.app.investigation.resource_correlation import ResourceCorrelationEngine
from backend.app.models.alert import AlertInstance
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.models.waste import WasteDetection


def test_resource_topology_and_metrics(db_session):
    """Verifies that CloudResource, ResourceMetric, and ResourceRelationship are retrieved."""
    # Create Resource
    res = CloudResource(
        resource_id="i-prod-01",
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        environment="production",
        owner="core-infra",
        cost_center="CC-OPS",
        status="active",
        monthly_cost=Decimal("1200.0000"),
    )
    db_session.add(res)

    # Add Metrics
    m1 = ResourceMetric(
        id=uuid.uuid4(),
        resource_id="i-prod-01",
        metric_name="cpu_utilization_pct",
        timestamp=datetime.now(timezone.utc),
        average_value=Decimal("78.50"),
        peak_value=Decimal("85.50"),
    )
    m2 = ResourceMetric(
        id=uuid.uuid4(),
        resource_id="i-prod-01",
        metric_name="cpu_utilization_pct",
        timestamp=datetime.now(timezone.utc),
        average_value=Decimal("85.50"),
        peak_value=Decimal("92.00"),
    )
    db_session.add(m1)
    db_session.add(m2)

    # Add Relationship (EC2 -> EBS)
    rel = ResourceRelationship(
        id=uuid.uuid4(),
        source_resource_id="i-prod-01",
        target_resource_id="vol-0123456789abcdef0",
        relationship_type="ATTACHED_TO",
        provider="AWS",
        confidence=Decimal("1.0000"),
    )
    db_session.add(rel)

    # Anomaly
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        resource_id="i-prod-01",
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

    investigation = ResourceCorrelationEngine.get_resource_investigation(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    assert investigation.total_affected_resources == 1
    item = investigation.resources[0]
    assert item.resource_id == "i-prod-01"
    assert item.environment == "production"
    assert item.owner == "core-infra"

    # Verify metrics summary
    assert item.metrics_summary["sample_count"] == 2
    assert item.metrics_summary["avg_cpu_percent"] == 82.0

    # Verify topology relationships
    assert len(item.relationships) == 1
    assert item.relationships[0]["target"] == "vol-0123456789abcdef0"
    assert item.relationships[0]["type"] == "ATTACHED_TO"


def test_cross_signal_correlations(db_session):
    """Verifies correlation with Waste Detections, Recommendations, and Alert Instances."""
    res_id = "i-wasteful-instance"
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        resource_id=res_id,
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

    # 1. Add Waste Detection
    waste = WasteDetection(
        id=uuid.uuid4(),
        detector_id="idle_compute_detector",
        detector_version="1.0.0",
        provider="AWS",
        account_id="123456789012",
        resource_id=res_id,
        waste_type="IDLE_COMPUTE",
        estimated_monthly_waste=Decimal("500.0000"),
        severity="HIGH",
        status="ACTIVE",
    )
    db_session.add(waste)

    # 2. Add Recommendation
    rec = Recommendation(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        resource_id=res_id,
        action_type="RIGHTSIZE",
        strategy_id="compute_rightsizing",
        title="Rightsize overprovisioned EC2 instance",
        description="CPU utilization remains under 5%",
        remediation_guide="Select smaller instance type",
        estimated_monthly_savings=Decimal("450.0000"),
        priority="P1",
        status="PROPOSED",
    )
    db_session.add(rec)

    # 3. Add Alert Instance
    alert = AlertInstance(
        id=uuid.uuid4(),
        title="Critical EC2 Spend Alert",
        anomaly_id=anomaly.id,
        provider="AWS",
        account_id="123456789012",
        service_name="AmazonEC2",
        region="us-east-1",
        severity="HIGH",
        status="OPEN",
        excess_cost=Decimal("1000.0000"),
        dedup_key="dedup-hash-12345",
    )
    db_session.add(alert)
    db_session.commit()

    corr = ResourceCorrelationEngine.get_cross_signals(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    assert len(corr.correlated_waste_detections) == 1
    assert corr.correlated_waste_detections[0]["rule_name"] == "idle_compute_detector"

    assert len(corr.correlated_recommendations) == 1
    assert corr.correlated_recommendations[0]["title"] == "Rightsize overprovisioned EC2 instance"

    assert len(corr.correlated_alerts) == 1
    assert corr.correlated_alerts[0]["rule_name"] == "Critical EC2 Spend Alert"

    # High multi-signal correlation
    assert corr.correlation_confidence == "HIGH"
    assert "High multi-signal correlation" in corr.correlation_summary
