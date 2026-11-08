"""
Tests for Waste Management Workspace.
Verifies triage lifecycle actions, batch operations, investigation, and reopen state machine.
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import get_sync_db
from backend.app.core.enums import Severity, WasteStatus, WasteType
from backend.app.main import app
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection


@pytest.fixture
def waste_workspace_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_sync_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_waste_finding(db_session):
    res = CloudResource(
        resource_id="arn:aws:ec2:us-east-1:123456789012:volume/vol-waste001",
        provider="AWS",
        account_id="123456789012",
        region="us-east-1",
        service_name="AmazonEC2",
        service_category="STORAGE",
        resource_type="ebs_volume",
        status="available",
        monthly_cost=Decimal("80.0000"),
        first_discovered_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(res)
    db_session.commit()

    finding = WasteDetection(
        id=uuid.uuid4(),
        resource_id=res.resource_id,
        provider="AWS",
        account_id="123456789012",
        waste_type=WasteType.UNATTACHED_DISK.value,
        detector_id="aws_unattached_ebs_volume",
        finding_title="Unattached EBS volume vol-waste001",
        explanation="Volume has not been attached to an EC2 instance for > 14 days.",
        severity=Severity.HIGH.value,
        status=WasteStatus.ACTIVE.value,
        estimated_monthly_waste=Decimal("80.0000"),
        first_detected_at=datetime.now(timezone.utc),
        last_evaluated_at=datetime.now(timezone.utc),
    )
    db_session.add(finding)
    db_session.commit()
    db_session.refresh(finding)
    return finding


def test_waste_action_acknowledge(waste_workspace_client, sample_waste_finding, db_session):
    f_id = str(sample_waste_finding.id)
    payload = {
        "action": "ACKNOWLEDGE",
        "actor": "devops.lead@enterprise.com",
    }
    response = waste_workspace_client.post(f"/api/v1/waste-detection/findings/{f_id}/action", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ACKNOWLEDGED"

    db_session.refresh(sample_waste_finding)
    assert sample_waste_finding.status == "ACKNOWLEDGED"


def test_waste_action_assign(waste_workspace_client, sample_waste_finding, db_session):
    f_id = str(sample_waste_finding.id)
    payload = {
        "action": "ASSIGN",
        "actor": "finops.lead@enterprise.com",
        "assigned_to": "infra.engineer@enterprise.com",
    }
    response = waste_workspace_client.post(f"/api/v1/waste-detection/findings/{f_id}/action", json=payload)
    assert response.status_code == 200
    assert response.json()["assigned_to"] == "infra.engineer@enterprise.com"

    db_session.refresh(sample_waste_finding)
    assert sample_waste_finding.assigned_to == "infra.engineer@enterprise.com"


def test_waste_action_snooze(waste_workspace_client, sample_waste_finding, db_session):
    f_id = str(sample_waste_finding.id)
    payload = {
        "action": "SNOOZE",
        "actor": "engineer@enterprise.com",
        "reason": "Volume is kept for legal retention audit.",
        "snooze_days": 30,
    }
    response = waste_workspace_client.post(f"/api/v1/waste-detection/findings/{f_id}/action", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "SNOOZED"

    db_session.refresh(sample_waste_finding)
    assert sample_waste_finding.status == "SNOOZED"
    assert sample_waste_finding.snooze_until is not None


def test_waste_action_resolve_requires_reason(waste_workspace_client, sample_waste_finding):
    f_id = str(sample_waste_finding.id)
    payload = {
        "action": "RESOLVE",
        "actor": "engineer@enterprise.com",
        "reason": "", # Empty reason
    }
    response = waste_workspace_client.post(f"/api/v1/waste-detection/findings/{f_id}/action", json=payload)
    assert response.status_code == 400


def test_waste_action_resolve_and_reopen(waste_workspace_client, sample_waste_finding, db_session):
    f_id = str(sample_waste_finding.id)

    # 1. Resolve
    resolve_payload = {
        "action": "RESOLVE",
        "actor": "ops@enterprise.com",
        "reason": "Volume safely removed via Terraform decommission.",
    }
    res = waste_workspace_client.post(f"/api/v1/waste-detection/findings/{f_id}/action", json=resolve_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"

    # 2. Reopen
    reopen_payload = {
        "action": "REOPEN",
        "actor": "finops@enterprise.com",
        "reason": "Re-detected after deployment rollback.",
    }
    reopen_res = waste_workspace_client.post(f"/api/v1/waste-detection/findings/{f_id}/action", json=reopen_payload)
    assert reopen_res.status_code == 200
    assert reopen_res.json()["status"] == "REOPENED"


def test_batch_waste_action_success(waste_workspace_client, sample_waste_finding):
    f_id = str(sample_waste_finding.id)
    payload = {
        "finding_ids": [f_id],
        "action": "ACKNOWLEDGE",
        "actor": "lead@enterprise.com",
    }
    response = waste_workspace_client.post("/api/v1/waste-detection/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_successful"] == 1
    assert data["total_failed"] == 0


def test_get_finding_investigation(waste_workspace_client, sample_waste_finding):
    f_id = str(sample_waste_finding.id)
    response = waste_workspace_client.get(f"/api/v1/waste-detection/findings/{f_id}/investigation")
    assert response.status_code == 200
    data = response.json()
    assert "finding" in data
    assert "correlations" in data
    assert data["correlations"]["resource_id"] == sample_waste_finding.resource_id
