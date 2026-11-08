"""
Tests for Resource Telemetry Analytics and Grounded Visualization.
Verifies metric time-series queries, statistical aggregates, and strict non-fabrication guarantees.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import get_sync_db
from backend.app.main import app
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.models.waste import WasteDetection
from backend.app.services.telemetry import TelemetryService


@pytest.fixture
def telemetry_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_sync_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def resource_with_telemetry(db_session):
    res = CloudResource(
        resource_id="arn:aws:ec2:us-east-1:123456789012:instance/i-telemetry01",
        provider="AWS",
        account_id="123456789012",
        region="us-east-1",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2_instance",
        status="active",
        monthly_cost=Decimal("150.0000"),
        first_discovered_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(res)
    db_session.commit()

    now = datetime.now(timezone.utc)
    # Add 5 metric points for CPU and 5 for Memory
    for i in range(5):
        m_cpu = ResourceMetric(
            id=uuid.uuid4(),
            resource_id=res.resource_id,
            metric_name="cpu_utilization_pct",
            timestamp=now - timedelta(days=i),
            average_value=Decimal(str(2.0 + i * 0.5)),
            peak_value=Decimal(str(4.0 + i * 0.5)),
            sample_count=60,
        )
        m_mem = ResourceMetric(
            id=uuid.uuid4(),
            resource_id=res.resource_id,
            metric_name="memory_utilization_pct",
            timestamp=now - timedelta(days=i),
            average_value=Decimal("15.5000"),
            peak_value=Decimal("20.0000"),
            sample_count=60,
        )
        db_session.add_all([m_cpu, m_mem])
    db_session.commit()
    return res


@pytest.fixture
def resource_without_telemetry(db_session):
    res = CloudResource(
        resource_id="arn:aws:s3:::unmonitored-bucket-01",
        provider="AWS",
        account_id="123456789012",
        region="us-east-1",
        service_category="STORAGE",
        service_name="AmazonS3",
        resource_type="s3_bucket",
        status="active",
        monthly_cost=Decimal("25.0000"),
        first_discovered_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(res)
    db_session.commit()
    return res


def test_telemetry_service_aggregates_computation(db_session, resource_with_telemetry):
    res = TelemetryService.get_resource_telemetry(db_session, resource_id=resource_with_telemetry.resource_id)
    assert res["has_telemetry"] is True
    assert "cpu_utilization_pct" in res["metrics"]
    assert "cpu_utilization_pct" in res["summary"]

    cpu_stats = res["summary"]["cpu_utilization_pct"]
    assert cpu_stats["min"] == 2.0
    assert cpu_stats["max"] == 6.0
    assert cpu_stats["total_points"] == 5


def test_telemetry_service_empty_state_guarantee(db_session, resource_without_telemetry):
    res = TelemetryService.get_resource_telemetry(db_session, resource_id=resource_without_telemetry.resource_id)
    assert res["has_telemetry"] is False
    assert res["reason"] == "NO_TELEMETRY_RECORDED"
    assert "No telemetry observations" in res["message"]
    # Ensure no fabricated points
    assert len(res["metrics"]) == 0


def test_telemetry_endpoint_on_inventory(telemetry_client, resource_with_telemetry):
    res_id = resource_with_telemetry.resource_id
    response = telemetry_client.get(f"/api/v1/inventory/resources/{res_id}/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert data["has_telemetry"] is True
    assert data["resource_id"] == res_id


def test_telemetry_endpoint_on_recommendations(telemetry_client, db_session, resource_with_telemetry):
    rec = Recommendation(
        id=uuid.uuid4(),
        recommendation_key="rec-tel-test",
        resource_id=resource_with_telemetry.resource_id,
        provider="AWS",
        action_type="RIGHTSIZE",
        priority="P2",
        status="PROPOSED",
        estimated_monthly_savings=Decimal("50.0000"),
        estimated_annual_savings=Decimal("600.0000"),
        title="Test Tel Rec",
        description="Desc",
        remediation_guide="Guide",
    )
    db_session.add(rec)
    db_session.commit()

    response = telemetry_client.get(f"/api/v1/recommendations/{rec.id}/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert data["has_telemetry"] is True
    assert "cpu_utilization_pct" in data["metrics"]


def test_telemetry_endpoint_on_waste_finding(telemetry_client, db_session, resource_with_telemetry):
    finding = WasteDetection(
        id=uuid.uuid4(),
        resource_id=resource_with_telemetry.resource_id,
        provider="AWS",
        waste_type="IDLE_VM",
        severity="MEDIUM",
        status="ACTIVE",
        estimated_monthly_waste=Decimal("50.0000"),
        first_detected_at=datetime.now(timezone.utc),
        last_evaluated_at=datetime.now(timezone.utc),
    )
    db_session.add(finding)
    db_session.commit()

    response = telemetry_client.get(f"/api/v1/waste-detection/findings/{finding.id}/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert data["has_telemetry"] is True
