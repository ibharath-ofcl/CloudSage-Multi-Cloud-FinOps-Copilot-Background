"""
Integration Tests for Advanced Anomaly Investigation & Multi-Dimensional Root Cause Analysis REST API.
Verifies all endpoints across:
1. /api/v1/investigations/stats
2. /api/v1/investigations (List, filters, search, pagination)
3. /api/v1/investigations (Create case)
4. /api/v1/investigations/{id} (Get detail, update)
5. /api/v1/investigations/{id}/assign
6. /api/v1/investigations/{id}/transition
7. /api/v1/investigations/{id}/close & /reopen
8. Analytical drill-down endpoints (/dimensions, /contributions, /usage-price-analysis, /timeline, /resources, /correlations, /root-causes)
9. Collaboration & findings (/evidence, /notes, /findings, /history)
10. Direct anomaly endpoints (/anomalies/{id}/investigate, /anomalies/{id}/investigation-summary)
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base, get_sync_db
from backend.app.core.enums import InvestigationPriority, InvestigationStatus
from backend.app.main import app
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.investigation import InvestigationCase


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


def _seed_anomaly(client):
    """Helper to seed an anomaly directly into the client's database."""
    session_gen = app.dependency_overrides[get_sync_db]()
    session = next(session_gen)
    session.expire_on_commit = False
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        resource_id="i-test-001",
        anomaly_category="SERVICE_SPIKE",
        anomaly_date=date(2026, 3, 15),
        actual_cost=Decimal("2500.0000"),
        expected_cost=Decimal("500.0000"),
        estimated_excess_cost=Decimal("2000.0000"),
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    session.add(anomaly)
    session.commit()
    session.expunge(anomaly)
    try:
        next(session_gen)
    except StopIteration:
        pass
    return anomaly


def test_api_stats_and_empty_list(client):
    """Verifies stats and listing when empty."""
    headers = {"X-User-Role": "FINOPS", "X-User-Email": "finops@cloudsage.com"}
    res = client.get("/api/v1/investigations/stats", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_investigations"] == 0

    res2 = client.get("/api/v1/investigations", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total"] == 0
    assert data2["items"] == []


def test_api_create_investigation(client):
    """Creates investigation case via POST /api/v1/investigations."""
    headers = {"X-User-Role": "ADMIN", "X-User-Email": "admin@cloudsage.com"}
    anomaly = _seed_anomaly(client)

    payload = {
        "anomaly_id": str(anomaly.id),
        "title": "EC2 Production Spike Investigation",
        "priority": "HIGH",
        "assigned_to": "lead@cloudsage.com",
        "initial_notes": "Opened investigation from dashboard alert.",
    }
    res = client.post("/api/v1/investigations", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["case_number"].startswith("INV-")
    assert data["title"] == "EC2 Production Spike Investigation"
    assert data["status"] == "ASSIGNED"
    assert data["priority"] == "HIGH"
    assert data["assigned_to"] == "lead@cloudsage.com"
    assert float(data["excess_cost"]) == 2000.0
    assert len(data["findings"]) > 0
    assert len(data["notes"]) == 1


def test_api_get_investigation_detail(client):
    """Retrieves full case details via GET /api/v1/investigations/{id}."""
    headers = {"X-User-Role": "FINOPS", "X-User-Email": "user@cloudsage.com"}
    anomaly = _seed_anomaly(client)

    create_res = client.post(
        "/api/v1/investigations",
        json={"anomaly_id": str(anomaly.id)},
        headers=headers,
    )
    case_id = create_res.json()["id"]

    res = client.get(f"/api/v1/investigations/{case_id}", headers=headers)
    assert res.status_code == 200
    detail = res.json()
    assert detail["id"] == case_id
    assert "findings" in detail
    assert "notes" in detail
    assert "evidence_links" in detail
    assert "history" in detail


def test_api_update_investigation(client):
    """Updates mutable fields via PUT /api/v1/investigations/{id}."""
    headers = {"X-User-Role": "FINOPS", "X-User-Email": "user@cloudsage.com"}
    anomaly = _seed_anomaly(client)

    create_res = client.post(
        "/api/v1/investigations",
        json={"anomaly_id": str(anomaly.id)},
        headers=headers,
    )
    case_id = create_res.json()["id"]

    update_payload = {
        "title": "Renamed Investigation Title",
        "priority": "CRITICAL",
        "root_cause_summary": "Updated summary from engineer triage.",
    }
    res = client.put(f"/api/v1/investigations/{case_id}", json=update_payload, headers=headers)
    assert res.status_code == 200
    updated = res.json()
    assert updated["title"] == "Renamed Investigation Title"
    assert updated["priority"] == "CRITICAL"
    assert updated["root_cause_summary"] == "Updated summary from engineer triage."


def test_api_assign_case(client):
    """Assigns case via POST /api/v1/investigations/{id}/assign."""
    headers = {"X-User-Role": "FINOPS", "X-User-Email": "user@cloudsage.com"}
    anomaly = _seed_anomaly(client)

    create_res = client.post(
        "/api/v1/investigations",
        json={"anomaly_id": str(anomaly.id)},
        headers=headers,
    )
    case_id = create_res.json()["id"]

    assign_res = client.post(
        f"/api/v1/investigations/{case_id}/assign",
        json={"assigned_to": "engineer@cloudsage.com", "notes": "Handing off to cloud ops."},
        headers=headers,
    )
    assert assign_res.status_code == 200
    assigned = assign_res.json()
    assert assigned["assigned_to"] == "engineer@cloudsage.com"
    assert assigned["status"] == "ASSIGNED"


def test_api_lifecycle_transitions(client):
    """Tests valid and invalid lifecycle transitions via API."""
    headers = {"X-User-Role": "FINOPS", "X-User-Email": "user@cloudsage.com"}
    anomaly = _seed_anomaly(client)

    create_res = client.post(
        "/api/v1/investigations",
        json={"anomaly_id": str(anomaly.id), "assigned_to": "user@test.com"},
        headers=headers,
    )
    case_id = create_res.json()["id"]

    # 1. Transition to INVESTIGATING
    res1 = client.post(
        f"/api/v1/investigations/{case_id}/transition",
        json={"status": "INVESTIGATING", "notes": "Actively investigating."},
        headers=headers,
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "INVESTIGATING"

    # 2. Transition to ROOT_CAUSE_IDENTIFIED without explanation -> 422
    res_fail = client.post(
        f"/api/v1/investigations/{case_id}/transition",
        json={"status": "ROOT_CAUSE_IDENTIFIED"},
        headers=headers,
    )
    assert res_fail.status_code == 422

    # 3. Transition to ROOT_CAUSE_IDENTIFIED with explanation -> 200
    res2 = client.post(
        f"/api/v1/investigations/{case_id}/transition",
        json={
            "status": "ROOT_CAUSE_IDENTIFIED",
            "verified_root_cause": "Misconfigured autoscaling scaling policy.",
        },
        headers=headers,
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "ROOT_CAUSE_IDENTIFIED"

    # 4. Transition to RESOLVED -> 200
    res3 = client.post(
        f"/api/v1/investigations/{case_id}/transition",
        json={"status": "RESOLVED", "notes": "Scale-in complete."},
        headers=headers,
    )
    assert res3.status_code == 200
    assert res3.json()["status"] == "RESOLVED"

    # 5. Invalid transition: directly to ASSIGNED from RESOLVED -> 400
    res_inv = client.post(
        f"/api/v1/investigations/{case_id}/transition",
        json={"status": "ASSIGNED"},
        headers=headers,
    )
    assert res_inv.status_code == 400


def test_api_close_and_reopen(client):
    """Tests convenience /close and /reopen endpoints."""
    headers = {"X-User-Role": "ADMIN", "X-User-Email": "admin@cloudsage.com"}
    anomaly = _seed_anomaly(client)

    create_res = client.post(
        "/api/v1/investigations",
        json={"anomaly_id": str(anomaly.id), "assigned_to": "admin@test.com"},
        headers=headers,
    )
    case_id = create_res.json()["id"]

    # Close case
    close_res = client.post(f"/api/v1/investigations/{case_id}/close", headers=headers)
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "CLOSED"

    # Reopen case
    reopen_res = client.post(f"/api/v1/investigations/{case_id}/reopen", headers=headers)
    assert reopen_res.status_code == 200
    assert reopen_res.json()["status"] == "INVESTIGATING"


def test_api_analytical_slices(client):
    """Verifies all analytical endpoints (/dimensions, /contributions, /usage-price-analysis, /timeline, /resources, /correlations)."""
    headers = {"X-User-Role": "FINOPS", "X-User-Email": "user@cloudsage.com"}
    anomaly = _seed_anomaly(client)

    create_res = client.post(
        "/api/v1/investigations",
        json={"anomaly_id": str(anomaly.id)},
        headers=headers,
    )
    case_id = create_res.json()["id"]

    # Dimensions
    dim_res = client.get(f"/api/v1/investigations/{case_id}/dimensions", headers=headers)
    assert dim_res.status_code == 200
    assert len(dim_res.json()["dimensions"]) == 10

    # Contributions
    contrib_res = client.get(f"/api/v1/investigations/{case_id}/contributions", headers=headers)
    assert contrib_res.status_code == 200
    assert "top_contributors" in contrib_res.json()

    # Usage Price
    up_res = client.get(f"/api/v1/investigations/{case_id}/usage-price-analysis", headers=headers)
    assert up_res.status_code == 200
    assert "usage_effect" in up_res.json()
    assert "price_effect" in up_res.json()

    # Timeline
    time_res = client.get(f"/api/v1/investigations/{case_id}/timeline", headers=headers)
    assert time_res.status_code == 200
    assert len(time_res.json()["data_points"]) > 0

    # Resources
    res_res = client.get(f"/api/v1/investigations/{case_id}/resources", headers=headers)
    assert res_res.status_code == 200
    assert "resources" in res_res.json()

    # Correlations
    corr_res = client.get(f"/api/v1/investigations/{case_id}/correlations", headers=headers)
    assert corr_res.status_code == 200
    assert "correlation_confidence" in corr_res.json()

    # Root Causes
    rc_res = client.get(f"/api/v1/investigations/{case_id}/root-causes", headers=headers)
    assert rc_res.status_code == 200
    assert isinstance(rc_res.json(), list)


def test_api_collaboration_notes_and_findings(client):
    """Tests /notes, /findings, /evidence, and /history endpoints."""
    headers = {"X-User-Role": "FINOPS", "X-User-Email": "analyst@cloudsage.com"}
    anomaly = _seed_anomaly(client)

    create_res = client.post(
        "/api/v1/investigations",
        json={"anomaly_id": str(anomaly.id)},
        headers=headers,
    )
    case_id = create_res.json()["id"]

    # Add Note
    note_res = client.post(
        f"/api/v1/investigations/{case_id}/notes",
        json={"content": "Reviewed CloudWatch metrics. High CPU load observed."},
        headers=headers,
    )
    assert note_res.status_code == 201
    assert note_res.json()["content"] == "Reviewed CloudWatch metrics. High CPU load observed."

    # Add Finding
    finding_res = client.post(
        f"/api/v1/investigations/{case_id}/findings",
        json={
            "finding_type": "CORRELATION",
            "title": "CPU spiked to 95% at 03:00 UTC",
            "explanation": "Traffic burst from marketing campaign coincident with cost surge.",
            "financial_impact": 500.0,
            "contribution_percentage": 25.0,
            "confidence_category": "HIGH",
            "confidence_score": 0.9,
            "evidence_source": "UTILIZATION_METRIC",
        },
        headers=headers,
    )
    assert finding_res.status_code == 201
    assert finding_res.json()["title"] == "CPU spiked to 95% at 03:00 UTC"

    # Evidence links
    ev_res = client.get(f"/api/v1/investigations/{case_id}/evidence", headers=headers)
    assert ev_res.status_code == 200
    assert len(ev_res.json()) > 0

    # History
    hist_res = client.get(f"/api/v1/investigations/{case_id}/history", headers=headers)
    assert hist_res.status_code == 200
    assert len(hist_res.json()) >= 3


def test_api_direct_anomaly_investigate_and_summary(client):
    """Tests POST /api/v1/anomalies/{id}/investigate and GET /api/v1/anomalies/{id}/investigation-summary."""
    headers = {"X-User-Role": "FINOPS", "X-User-Email": "user@cloudsage.com"}
    anomaly = _seed_anomaly(client)

    # 1. Summary before investigation
    sum1 = client.get(f"/api/v1/anomalies/{anomaly.id}/investigation-summary", headers=headers)
    assert sum1.status_code == 200
    assert sum1.json()["has_active_investigation"] is False

    # 2. Trigger investigation directly
    inv_res = client.post(f"/api/v1/anomalies/{anomaly.id}/investigate", headers=headers)
    assert inv_res.status_code == 201
    case_data = inv_res.json()
    assert case_data["case_number"].startswith("INV-")

    # 3. Summary after investigation
    sum2 = client.get(f"/api/v1/anomalies/{anomaly.id}/investigation-summary", headers=headers)
    assert sum2.status_code == 200
    s_data = sum2.json()
    assert s_data["has_active_investigation"] is True
    assert s_data["investigation_id"] == case_data["id"]
    assert s_data["finding_count"] > 0
