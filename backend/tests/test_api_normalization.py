"""
CloudSage Normalization API Endpoints Tests.
Tests all REST endpoints in /api/v1/normalization/ using FastAPI TestClient.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.app.core.database import get_sync_db
from backend.app.main import app
from backend.app.models.billing import BillingRecord


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_sync_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_api_normalization_currency_rates(client):
    """Verify GET /api/v1/normalization/currency-rates returns rates and base currency."""
    resp = client.get("/api/v1/normalization/currency-rates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["base_currency"] == "USD"
    assert "EUR" in data["rates_to_usd"]
    assert "GBP" in data["rates_to_usd"]
    assert data["total_currencies"] >= 7


def test_api_normalization_catalog_mappings(client):
    """Verify GET /api/v1/normalization/catalog returns catalog entries."""
    resp = client.get("/api/v1/normalization/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    assert any(m["service_code"] == "AmazonEC2" for m in data["mappings"])


def test_api_normalization_run_and_runs_list(client, db_session):
    """Verify triggering a normalization run and fetching it via GET /runs."""
    # Seed 1 record
    rec = BillingRecord(
        provider="AWS",
        billing_account_id="acc-1",
        subscription_id="sub-1",
        resource_id="res-1",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        region="us-east-1",
        usage_start_time=datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        usage_end_time=datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
        usage_quantity=Decimal("1.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("10.00"),
        currency="USD",
        tags={"owner": "alice", "environment": "production"},
    )
    db_session.add(rec)
    db_session.commit()

    # Trigger run
    run_resp = client.post(
        "/api/v1/normalization/run",
        json={"provider": "AWS", "reprocess_all": True, "batch_size": 100},
    )
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["status"] == "COMPLETED"
    assert run_data["total_records"] == 1
    run_id = run_data["run_id"]

    # List runs
    runs_resp = client.get("/api/v1/normalization/runs")
    assert runs_resp.status_code == 200
    runs_list = runs_resp.json()
    assert len(runs_list) >= 1
    assert any(r["run_id"] == run_id for r in runs_list)

    # Get single run
    single_resp = client.get(f"/api/v1/normalization/runs/{run_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["run_id"] == run_id


def test_api_normalization_quality_report(client, db_session):
    """Verify GET /api/v1/normalization/quality-report returns quality scoring."""
    resp = client.get("/api/v1/normalization/quality-report")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "total_records_evaluated" in data


def test_api_normalization_focus_validation(client, db_session):
    """Verify GET /api/v1/normalization/focus-validation returns conformance assessment."""
    resp = client.get("/api/v1/normalization/focus-validation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["focus_version"] == "1.0.0"
    assert "conformance_percentage" in data
    assert len(data["fully_supported_columns"]) > 0


def test_api_normalization_tag_quality(client, db_session):
    """Verify GET /api/v1/normalization/tag-quality returns tag quality evaluations."""
    resp = client.get("/api/v1/normalization/tag-quality")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
