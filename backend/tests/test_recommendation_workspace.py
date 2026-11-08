"""
Tests for Recommendation Management Workspace.
Covers listing, search, multi-factor sorting, filtering, detail retrieval, and correlations.
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.core.database import Base, get_sync_db
from backend.app.core.enums import CloudProvider, Priority, RecommendationAction, RecommendationStatus, RiskLevel
from backend.app.main import app
from backend.app.models.recommendation import Recommendation, RecommendationEvidence, RecommendationHistory
from backend.app.models.resource import CloudResource


@pytest.fixture
def workspace_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_sync_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_recommendations(db_session):
    # Setup resources
    res1 = CloudResource(
        resource_id="arn:aws:ec2:us-east-1:123456789012:instance/i-0aaa111",
        provider="AWS",
        account_id="123456789012",
        region="us-east-1",
        service_name="AmazonEC2",
        service_category="COMPUTE",
        resource_type="ec2_instance",
        status="active",
        monthly_cost=Decimal("250.0000"),
        first_discovered_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    res2 = CloudResource(
        resource_id="/subscriptions/sub-123/resourceGroups/rg-1/providers/Microsoft.Compute/virtualMachines/vm-prod-db",
        provider="AZURE",
        account_id="sub-123",
        region="eastus",
        service_name="VirtualMachines",
        service_category="COMPUTE",
        resource_type="virtual_machine",
        status="active",
        monthly_cost=Decimal("450.0000"),
        first_discovered_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add_all([res1, res2])
    db_session.commit()

    # Setup recommendations
    rec1 = Recommendation(
        id=uuid.uuid4(),
        recommendation_key="rec-key-1",
        resource_id=res1.resource_id,
        provider="AWS",
        account_id="123456789012",
        region="us-east-1",
        service_name="AmazonEC2",
        action_type="RIGHTSIZE",
        priority=Priority.P1.value,
        priority_score=Decimal("0.9000"),
        risk_level=RiskLevel.LOW.value,
        risk_score=Decimal("0.1000"),
        confidence_score=Decimal("0.9500"),
        status=RecommendationStatus.PROPOSED.value,
        current_monthly_cost=Decimal("250.0000"),
        projected_monthly_cost=Decimal("100.0000"),
        estimated_monthly_savings=Decimal("150.0000"),
        estimated_annual_savings=Decimal("1800.0000"),
        title="Rightsize overprovisioned EC2 instance i-0aaa111",
        description="EC2 instance has averaged < 5% CPU utilization over 14 days.",
        remediation_guide="Modify instance type from c5.2xlarge to c5.large.",
        assigned_to="alice@enterprise.com",
        external_ticket_ref="FIN-101",
    )

    rec2 = Recommendation(
        id=uuid.uuid4(),
        recommendation_key="rec-key-2",
        resource_id=res2.resource_id,
        provider="AZURE",
        account_id="sub-123",
        region="eastus",
        service_name="VirtualMachines",
        action_type="TERMINATE",
        priority=Priority.P2.value,
        priority_score=Decimal("0.7000"),
        risk_level=RiskLevel.MEDIUM.value,
        risk_score=Decimal("0.4000"),
        confidence_score=Decimal("0.8500"),
        status=RecommendationStatus.UNDER_REVIEW.value,
        current_monthly_cost=Decimal("450.0000"),
        projected_monthly_cost=Decimal("0.0000"),
        estimated_monthly_savings=Decimal("450.0000"),
        estimated_annual_savings=Decimal("5400.0000"),
        title="Decommission stopped Azure VM vm-prod-db",
        description="Virtual machine has been powered off with attached managed disks.",
        remediation_guide="az vm delete --ids ...",
        assigned_to="bob@enterprise.com",
        external_ticket_ref="FIN-202",
    )

    db_session.add_all([rec1, rec2])
    db_session.commit()
    return [rec1, rec2]


def test_list_recommendations_default(workspace_client, sample_recommendations):
    response = workspace_client.get("/api/v1/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_list_recommendations_filter_by_provider(workspace_client, sample_recommendations):
    response = workspace_client.get("/api/v1/recommendations?provider=AWS")
    assert response.status_code == 200
    data = response.json()
    assert all(r["provider"] == "AWS" for r in data)
    assert any(r["id"] == str(sample_recommendations[0].id) for r in data)


def test_list_recommendations_filter_by_status(workspace_client, sample_recommendations):
    response = workspace_client.get("/api/v1/recommendations?status=UNDER_REVIEW")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_recommendations[1].id)


def test_list_recommendations_filter_by_priority(workspace_client, sample_recommendations):
    response = workspace_client.get("/api/v1/recommendations?priority=P1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_recommendations[0].id)


def test_list_recommendations_filter_by_min_savings(workspace_client, sample_recommendations):
    response = workspace_client.get("/api/v1/recommendations?min_savings=300")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_recommendations[1].id)


def test_list_recommendations_search_title(workspace_client, sample_recommendations):
    response = workspace_client.get("/api/v1/recommendations?search=Decommission")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_recommendations[1].id)


def test_list_recommendations_search_ticket(workspace_client, sample_recommendations):
    response = workspace_client.get("/api/v1/recommendations?search=FIN-101")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(sample_recommendations[0].id)


def test_list_recommendations_sort_by_savings_desc(workspace_client, sample_recommendations):
    response = workspace_client.get("/api/v1/recommendations?sort_by=savings&sort_order=desc")
    assert response.status_code == 200
    data = response.json()
    assert float(data[0]["estimated_monthly_savings"]) >= float(data[1]["estimated_monthly_savings"])


def test_list_recommendations_sort_by_savings_asc(workspace_client, sample_recommendations):
    response = workspace_client.get("/api/v1/recommendations?sort_by=savings&sort_order=asc")
    assert response.status_code == 200
    data = response.json()
    assert float(data[0]["estimated_monthly_savings"]) <= float(data[1]["estimated_monthly_savings"])


def test_get_recommendation_detail_found(workspace_client, sample_recommendations):
    rec_id = str(sample_recommendations[0].id)
    response = workspace_client.get(f"/api/v1/recommendations/{rec_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rec_id
    assert data["title"] == sample_recommendations[0].title
    assert data["assigned_to"] == "alice@enterprise.com"


def test_get_recommendation_detail_not_found(workspace_client):
    fake_id = str(uuid.uuid4())
    response = workspace_client.get(f"/api/v1/recommendations/{fake_id}")
    assert response.status_code == 404


def test_get_recommendation_correlations(workspace_client, sample_recommendations):
    rec_id = str(sample_recommendations[0].id)
    response = workspace_client.get(f"/api/v1/recommendations/{rec_id}/correlations")
    assert response.status_code == 200
    data = response.json()
    assert data["resource_id"] == sample_recommendations[0].resource_id
    assert "financial_taxonomy" in data
    assert data["financial_taxonomy"]["currency"] == "USD"
    assert "anti_double_counting_note" in data["financial_taxonomy"]
