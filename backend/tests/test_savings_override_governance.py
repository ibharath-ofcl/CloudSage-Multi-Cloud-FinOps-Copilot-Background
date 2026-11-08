"""
Tests for Savings Override Governance and Dual-Custody Review.
Verifies proposal, review, Decimal precision, audit logging, and rejection rules.
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import get_sync_db
from backend.app.core.enums import Priority, RecommendationStatus
from backend.app.main import app
from backend.app.models.recommendation import Recommendation, RecommendationHistory, RecommendationSavingsOverride
from backend.app.models.resource import CloudResource


@pytest.fixture
def override_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_sync_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_recommendation_for_override(db_session):
    res = CloudResource(
        resource_id="arn:aws:ec2:us-east-1:123456789012:instance/i-override01",
        provider="AWS",
        account_id="123456789012",
        region="us-east-1",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2_instance",
        status="active",
        monthly_cost=Decimal("500.0000"),
        first_discovered_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(res)
    db_session.commit()

    rec = Recommendation(
        id=uuid.uuid4(),
        recommendation_key="override-test-rec",
        resource_id=res.resource_id,
        provider="AWS",
        action_type="RIGHTSIZE",
        priority=Priority.P2.value,
        status=RecommendationStatus.PROPOSED.value,
        current_monthly_cost=Decimal("500.0000"),
        projected_monthly_cost=Decimal("300.0000"),
        estimated_monthly_savings=Decimal("200.0000"),
        estimated_annual_savings=Decimal("2400.0000"),
        title="Rightsize EC2 instance i-override01",
        description="Low CPU utilization detected.",
        remediation_guide="Downsize to m5.large.",
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)
    return rec


def test_propose_savings_override_success(override_client, test_recommendation_for_override, db_session):
    rec_id = str(test_recommendation_for_override.id)
    payload = {
        "proposed_monthly_savings": "175.5000",
        "reason": "Enterprise Discount Agreement reduces on-demand savings to $175.50.",
        "proposed_by": "lead.analyst@enterprise.com",
    }
    response = override_client.post(f"/api/v1/recommendations/{rec_id}/override", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["recommendation_id"] == rec_id
    assert Decimal(str(data["proposed_monthly_savings"])) == Decimal("175.5000")
    assert data["status"] == "PROPOSED"
    assert data["proposed_by"] == "lead.analyst@enterprise.com"

    # Verify audit history entry was created
    history = db_session.query(RecommendationHistory).filter(
        RecommendationHistory.recommendation_id == test_recommendation_for_override.id
    ).all()
    assert any(h.action == "SAVINGS_OVERRIDE_PROPOSED" for h in history)


def test_propose_savings_override_negative_rejected(override_client, test_recommendation_for_override):
    rec_id = str(test_recommendation_for_override.id)
    payload = {
        "proposed_monthly_savings": "-50.0000",
        "reason": "Invalid negative test",
        "proposed_by": "analyst@enterprise.com",
    }
    response = override_client.post(f"/api/v1/recommendations/{rec_id}/override", json=payload)
    assert response.status_code == 422 # Pydantic ge=0 validation


def test_approve_savings_override_flow(override_client, test_recommendation_for_override, db_session):
    rec_id = str(test_recommendation_for_override.id)

    # 1. Propose override
    prop_payload = {
        "proposed_monthly_savings": "180.2500",
        "reason": "Adjusted for reserved instance baseline.",
        "proposed_by": "engineer@enterprise.com",
    }
    prop_res = override_client.post(f"/api/v1/recommendations/{rec_id}/override", json=prop_payload)
    assert prop_res.status_code == 201
    override_id = prop_res.json()["id"]

    # 2. Approve override
    app_payload = {
        "approved": True,
        "approved_by": "finops.director@enterprise.com",
    }
    app_res = override_client.post(f"/api/v1/recommendations/{rec_id}/override/{override_id}/approve", json=app_payload)
    assert app_res.status_code == 200
    app_data = app_res.json()
    assert app_data["status"] == "APPROVED"
    assert app_data["approved_by"] == "finops.director@enterprise.com"

    # 3. Verify recommendation model updated
    db_session.refresh(test_recommendation_for_override)
    assert test_recommendation_for_override.is_savings_overridden is True
    assert test_recommendation_for_override.revised_monthly_savings == Decimal("180.2500")
    assert test_recommendation_for_override.estimated_annual_savings == Decimal("2163.0000")


def test_reject_savings_override_flow(override_client, test_recommendation_for_override, db_session):
    rec_id = str(test_recommendation_for_override.id)

    # 1. Propose override
    prop_payload = {
        "proposed_monthly_savings": "50.0000",
        "reason": "Aggressive estimate reduction.",
        "proposed_by": "junior@enterprise.com",
    }
    prop_res = override_client.post(f"/api/v1/recommendations/{rec_id}/override", json=prop_payload)
    override_id = prop_res.json()["id"]

    # 2. Reject override without reason -> fails
    bad_payload = {
        "approved": False,
        "approved_by": "manager@enterprise.com",
        "rejection_reason": "",
    }
    bad_res = override_client.post(f"/api/v1/recommendations/{rec_id}/override/{override_id}/approve", json=bad_payload)
    assert bad_res.status_code == 400

    # 3. Reject with valid reason
    good_payload = {
        "approved": False,
        "approved_by": "manager@enterprise.com",
        "rejection_reason": "Insufficient telemetry proof provided for reduction.",
    }
    good_res = override_client.post(f"/api/v1/recommendations/{rec_id}/override/{override_id}/approve", json=good_payload)
    assert good_res.status_code == 200
    assert good_res.json()["status"] == "REJECTED"


def test_list_overrides_endpoint(override_client, test_recommendation_for_override):
    rec_id = str(test_recommendation_for_override.id)
    response = override_client.get(f"/api/v1/recommendations/{rec_id}/overrides")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
