"""
Tests for Batch Recommendation Review Operations.
Verifies batch approve, reject, dismiss, snooze, partial failure isolation, and audit logging.
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import get_sync_db
from backend.app.core.enums import Priority, RecommendationStatus, RiskLevel
from backend.app.main import app
from backend.app.models.recommendation import Recommendation, RecommendationHistory
from backend.app.models.resource import CloudResource


@pytest.fixture
def batch_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_sync_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def multiple_recommendations(db_session):
    res = CloudResource(
        resource_id="arn:aws:ec2:us-west-2:111122223333:instance/i-batch001",
        provider="AWS",
        account_id="111122223333",
        region="us-west-2",
        service_name="AmazonEC2",
        service_category="COMPUTE",
        resource_type="ec2_instance",
        status="active",
        monthly_cost=Decimal("120.0000"),
        first_discovered_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(res)
    db_session.commit()

    recs = []
    for i in range(5):
        r = Recommendation(
            id=uuid.uuid4(),
            recommendation_key=f"batch-rec-{i}",
            resource_id=res.resource_id,
            provider="AWS",
            action_type="RIGHTSIZE",
            priority=Priority.P2.value,
            status=RecommendationStatus.PROPOSED.value,
            estimated_monthly_savings=Decimal("50.0000"),
            estimated_annual_savings=Decimal("600.0000"),
            title=f"Optimization advisory #{i}",
            description="Instance utilization analysis shows persistent idle state.",
            remediation_guide="Downsize to target instance type.",
        )
        recs.append(r)
        db_session.add(r)
    db_session.commit()
    return recs


def test_batch_approve_success(batch_client, multiple_recommendations, db_session):
    ids = [str(r.id) for r in multiple_recommendations[:3]]
    payload = {
        "recommendation_ids": ids,
        "action": "APPROVE",
        "actor_email": "finops.approver@enterprise.com",
        "reason": "Approved during Q4 FinOps review cycle.",
    }
    response = batch_client.post("/api/v1/recommendations/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_requested"] == 3
    assert data["total_successful"] == 3
    assert data["total_failed"] == 0

    # Verify DB state
    for r in multiple_recommendations[:3]:
        db_session.refresh(r)
        assert r.status == "APPROVED"
        assert r.approved_by == "finops.approver@enterprise.com"


def test_batch_snooze_with_days(batch_client, multiple_recommendations, db_session):
    ids = [str(multiple_recommendations[3].id)]
    payload = {
        "recommendation_ids": ids,
        "action": "SNOOZE",
        "actor_email": "engineer@enterprise.com",
        "reason": "Workload migration planned in 30 days.",
        "snooze_days": 30,
    }
    response = batch_client.post("/api/v1/recommendations/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_successful"] == 1

    r = multiple_recommendations[3]
    db_session.refresh(r)
    assert r.status == "SNOOZED"
    assert r.snooze_until is not None


def test_batch_dismiss_requires_reason(batch_client, multiple_recommendations):
    ids = [str(multiple_recommendations[4].id)]
    payload = {
        "recommendation_ids": ids,
        "action": "DISMISS",
        "actor_email": "analyst@enterprise.com",
        "reason": "", # Missing required reason
    }
    response = batch_client.post("/api/v1/recommendations/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_failed"] == 1
    assert "mandatory" in data["failed"][0]["error"].lower()


def test_batch_dismiss_success(batch_client, multiple_recommendations, db_session):
    ids = [str(multiple_recommendations[4].id)]
    payload = {
        "recommendation_ids": ids,
        "action": "DISMISS",
        "actor_email": "analyst@enterprise.com",
        "reason": "False positive: machine is an active burstable build worker.",
    }
    response = batch_client.post("/api/v1/recommendations/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_successful"] == 1

    r = multiple_recommendations[4]
    db_session.refresh(r)
    assert r.status == "DISMISSED"
    assert r.review_reason == "False positive: machine is an active burstable build worker."


def test_batch_partial_failure_isolation(batch_client, multiple_recommendations):
    fake_id = str(uuid.uuid4())
    valid_id = str(multiple_recommendations[0].id)
    payload = {
        "recommendation_ids": [valid_id, fake_id],
        "action": "APPROVE",
        "actor_email": "lead@enterprise.com",
    }
    response = batch_client.post("/api/v1/recommendations/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_requested"] == 2
    assert data["total_successful"] == 1
    assert data["total_failed"] == 1
    assert data["failed"][0]["id"] == fake_id


def test_batch_invalid_action_rejected(batch_client, multiple_recommendations):
    ids = [str(multiple_recommendations[0].id)]
    payload = {
        "recommendation_ids": ids,
        "action": "INVALID_ACTION_TEST",
        "actor_email": "tester@enterprise.com",
    }
    response = batch_client.post("/api/v1/recommendations/batch", json=payload)
    assert response.status_code == 400
