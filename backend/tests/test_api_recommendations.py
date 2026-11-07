"""
CloudSage Advisory Recommendation REST API Integration Tests.
Verifies all 16 REST API endpoints: execution runs, listing with filters/search,
summary KPIs, priority breakdown, category breakdown, runs audit, financial impact,
owner grouping, export (CSV/JSON), detail view, evidence inspection, history audit,
savings breakdown, lifecycle transitions, and feedback submission.
"""

from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base, get_sync_db
from backend.app.core.enums import CloudProvider, Priority, RecommendationAction, RecommendationStatus, RiskLevel
from backend.app.main import app
from backend.app.models.recommendation import Recommendation, RecommendationEvidence, RecommendationRun
from backend.app.models.resource import CloudResource
from backend.app.recommendations.synthetic import seed_synthetic_recommendation_scenarios


@pytest.fixture
def client(engine):
    """Yield TestClient with overridden database session and thread-safe engine."""
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_sync_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def seeded_db(engine):
    """Seeds synthetic recommendations and returns a session."""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    recs = seed_synthetic_recommendation_scenarios(db)
    db.close()
    return recs


def test_api_trigger_recommendation_run(client):
    """POST /api/v1/recommendations/run triggers execution run."""
    resp = client.post("/api/v1/recommendations/run", json={"provider": "ALL", "scope": "FULL"})
    assert resp.status_code == 201
    data = resp.json()
    assert "run_id" in data
    assert data["status"] in ("COMPLETED", "PARTIAL_SUCCESS")
    assert "total_monthly_savings" in data


def test_api_list_recommendations(client, seeded_db):
    """GET /api/v1/recommendations returns list with pagination and filtering."""
    resp = client.get("/api/v1/recommendations?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10

    # Filter by provider
    resp_aws = client.get("/api/v1/recommendations?provider=AWS")
    assert resp_aws.status_code == 200
    aws_data = resp_aws.json()
    assert all(r["provider"] == "AWS" for r in aws_data)

    # Search filter
    resp_search = client.get("/api/v1/recommendations?search=Glacier")
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert len(search_data) >= 1
    assert any("Glacier" in r["title"] for r in search_data)


def test_api_recommendation_summary(client, seeded_db):
    """GET /api/v1/recommendations/summary returns multi-cloud executive KPIs."""
    resp = client.get("/api/v1/recommendations/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_recommendations"] == 20
    assert float(data["total_monthly_savings"]) > 0.0
    assert "AWS" in data["by_provider"]
    assert "AZURE" in data["by_provider"]
    assert "GCP" in data["by_provider"]
    assert "P1" in data["by_priority"]


def test_api_priorities_breakdown(client, seeded_db):
    """GET /api/v1/recommendations/priorities returns tier statistics."""
    resp = client.get("/api/v1/recommendations/priorities")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    priorities = {d["priority"] for d in data}
    assert "P1" in priorities or "P2" in priorities


def test_api_categories_breakdown(client, seeded_db):
    """GET /api/v1/recommendations/categories returns category statistics."""
    resp = client.get("/api/v1/recommendations/categories")
    assert resp.status_code == 200
    data = resp.json()
    actions = {d["action_type"] for d in data}
    assert "TERMINATE" in actions
    assert "RIGHTSIZE" in actions


def test_api_runs_and_run_detail(client):
    """GET /api/v1/recommendations/runs and GET /api/v1/recommendations/runs/{id}."""
    run_resp = client.post("/api/v1/recommendations/run", json={"provider": "AWS"})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["run_id"]

    runs_resp = client.get("/api/v1/recommendations/runs")
    assert runs_resp.status_code == 200
    runs = runs_resp.json()
    assert len(runs) >= 1

    detail_resp = client.get(f"/api/v1/recommendations/runs/{run_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["run_id"] == run_id


def test_api_financial_impact(client, seeded_db):
    """GET /api/v1/recommendations/financial-impact."""
    resp = client.get("/api/v1/recommendations/financial-impact")
    assert resp.status_code == 200
    data = resp.json()
    assert float(data["total_identified_monthly_savings"]) > 0.0
    assert "savings_by_provider" in data
    assert "AWS" in data["savings_by_provider"]


def test_api_owners_impact(client, seeded_db):
    """GET /api/v1/recommendations/owners."""
    resp = client.get("/api/v1/recommendations/owners")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    owners = {d["owner"] for d in data}
    assert len(owners) >= 1


def test_api_export_json_and_csv(client, seeded_db):
    """GET /api/v1/recommendations/export for JSON and CSV."""
    resp_json = client.get("/api/v1/recommendations/export?export_format=json")
    assert resp_json.status_code == 200
    assert resp_json.headers["content-type"] == "application/json"
    data = resp_json.json()
    assert len(data) == 20

    resp_csv = client.get("/api/v1/recommendations/export?export_format=csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert "ID,Provider,AccountID" in resp_csv.text


def test_api_single_recommendation_details_evidence_history_savings(client, seeded_db):
    """GET /{id}, /{id}/evidence, /{id}/history, /{id}/savings."""
    list_resp = client.get("/api/v1/recommendations")
    assert list_resp.status_code == 200
    recs = list_resp.json()
    assert len(recs) >= 1
    rec_id = recs[0]["id"]

    # Detail
    detail_resp = client.get(f"/api/v1/recommendations/{rec_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == rec_id
    assert "implementation_guidance" in detail_resp.json()

    # Evidence
    ev_resp = client.get(f"/api/v1/recommendations/{rec_id}/evidence")
    assert ev_resp.status_code == 200
    ev_data = ev_resp.json()
    assert len(ev_data) >= 1

    # History
    hist_resp = client.get(f"/api/v1/recommendations/{rec_id}/history")
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) >= 1

    # Savings
    savings_resp = client.get(f"/api/v1/recommendations/{rec_id}/savings")
    assert savings_resp.status_code == 200
    s_data = savings_resp.json()
    assert float(s_data["monthly_savings"]) > 0.0
    assert "calculation_breakdown" in s_data


def test_api_status_update_lifecycle_and_validation(client, seeded_db):
    """PATCH /api/v1/recommendations/{id}/status."""
    list_resp = client.get("/api/v1/recommendations")
    recs = list_resp.json()
    rec_id = recs[0]["id"]

    # Valid: PROPOSED -> UNDER_REVIEW
    update_resp = client.patch(
        f"/api/v1/recommendations/{rec_id}/status",
        json={"status": "UNDER_REVIEW", "actor_email": "finops@enterprise.com"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "UNDER_REVIEW"

    # Invalid jump: UNDER_REVIEW -> VERIFIED (must raise 400)
    invalid_resp = client.patch(
        f"/api/v1/recommendations/{rec_id}/status",
        json={"status": "VERIFIED", "actor_email": "finops@enterprise.com"},
    )
    assert invalid_resp.status_code == 400

    # Dismissal without reason raises 422
    missing_reason_resp = client.patch(
        f"/api/v1/recommendations/{rec_id}/status",
        json={"status": "DISMISSED", "actor_email": "finops@enterprise.com", "notes": ""},
    )
    assert missing_reason_resp.status_code == 422


def test_api_submit_feedback(client, seeded_db):
    """POST /api/v1/recommendations/{id}/feedback."""
    list_resp = client.get("/api/v1/recommendations")
    recs = list_resp.json()
    rec_id = recs[0]["id"]

    feedback_resp = client.post(
        f"/api/v1/recommendations/{rec_id}/feedback",
        json={
            "actor_email": "engineer@enterprise.com",
            "rating": 5,
            "feedback_text": "Great suggestion, planned for next sprint release window.",
        },
    )
    assert feedback_resp.status_code == 200
    assert feedback_resp.json()["action"] == "FEEDBACK_SUBMITTED"
