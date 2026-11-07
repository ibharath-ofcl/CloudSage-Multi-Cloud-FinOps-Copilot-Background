"""
Test Suite: Dashboard REST API Endpoints.
Tests all 13 analytical endpoints, export formats (CSV/JSON), and HTML5 UI views.
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import get_sync_db
from backend.tests.test_dashboard_analytics import populated_dashboard_db


@pytest.fixture
def client(populated_dashboard_db: Session):
    """FastAPI test client with database dependency override."""
    def override_get_db():
        try:
            yield populated_dashboard_db
        finally:
            pass

    app.dependency_overrides[get_sync_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_api_dashboard_overview(client: TestClient):
    """Test GET /api/v1/dashboard/overview."""
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    assert "kpi" in data
    assert "provider_comparison" in data
    assert "cost_trends" in data
    assert "top_services" in data
    assert Decimal(str(data["kpi"]["total_spend"])) == Decimal("300.0000")


def test_api_dashboard_kpis(client: TestClient):
    """Test GET /api/v1/dashboard/kpis."""
    response = client.get("/api/v1/dashboard/kpis")
    assert response.status_code == 200
    data = response.json()
    assert Decimal(str(data["total_spend"])) == Decimal("300.0000")
    assert Decimal(str(data["identified_monthly_waste"])) == Decimal("45.0000")
    assert Decimal(str(data["potential_monthly_savings"])) == Decimal("95.0000")


def test_api_dashboard_trends_daily(client: TestClient):
    """Test GET /api/v1/dashboard/cost-trends?granularity=DAILY."""
    response = client.get("/api/v1/dashboard/cost-trends?granularity=DAILY")
    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "DAILY"
    assert len(data["points"]) >= 1


def test_api_dashboard_trends_monthly(client: TestClient):
    """Test GET /api/v1/dashboard/cost-trends?granularity=MONTHLY."""
    response = client.get("/api/v1/dashboard/cost-trends?granularity=MONTHLY")
    assert response.status_code == 200
    data = response.json()
    assert data["granularity"] == "MONTHLY"
    assert len(data["points"]) >= 1


def test_api_dashboard_provider_comparison(client: TestClient):
    """Test GET /api/v1/dashboard/provider-comparison."""
    response = client.get("/api/v1/dashboard/provider-comparison")
    assert response.status_code == 200
    data = response.json()
    assert len(data["providers"]) == 3
    providers = {p["provider"] for p in data["providers"]}
    assert providers == {"AWS", "AZURE", "GCP"}


def test_api_dashboard_service_breakdown(client: TestClient):
    """Test GET /api/v1/dashboard/service-breakdown."""
    response = client.get("/api/v1/dashboard/service-breakdown")
    assert response.status_code == 200
    data = response.json()
    assert len(data["services"]) == 3
    assert data["services"][0]["service_name"] == "Amazon Elastic Compute Cloud"


def test_api_dashboard_resource_costs(client: TestClient):
    """Test GET /api/v1/dashboard/resource-costs."""
    response = client.get("/api/v1/dashboard/resource-costs?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "resources" in data
    assert "total_spend" in data


def test_api_dashboard_anomalies(client: TestClient):
    """Test GET /api/v1/dashboard/anomaly-summary and alias /anomalies."""
    for path in ["/api/v1/dashboard/anomaly-summary", "/api/v1/dashboard/anomalies"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["total_active_anomalies"] == 1
        assert Decimal(str(data["total_excess_cost"])) == Decimal("60.0000")


def test_api_dashboard_waste(client: TestClient):
    """Test GET /api/v1/dashboard/waste-summary and alias /waste."""
    for path in ["/api/v1/dashboard/waste-summary", "/api/v1/dashboard/waste"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["total_active_waste_items"] == 1
        assert Decimal(str(data["total_monthly_waste"])) == Decimal("45.0000")


def test_api_dashboard_recommendations(client: TestClient):
    """Test GET /api/v1/dashboard/recommendation-summary and alias /recommendations."""
    for path in ["/api/v1/dashboard/recommendation-summary", "/api/v1/dashboard/recommendations"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["total_open_recommendations"] == 1
        assert Decimal(str(data["potential_monthly_savings"])) == Decimal("70.0000")


def test_api_dashboard_savings(client: TestClient):
    """Test GET /api/v1/dashboard/savings-summary and alias /savings."""
    for path in ["/api/v1/dashboard/savings-summary", "/api/v1/dashboard/savings"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert Decimal(str(data["potential_monthly_savings"])) == Decimal("95.0000")
        assert Decimal(str(data["verified_realized_savings"])) == Decimal("25.0000")


def test_api_dashboard_inventory(client: TestClient):
    """Test GET /api/v1/dashboard/inventory-summary and alias /inventory."""
    for path in ["/api/v1/dashboard/inventory-summary", "/api/v1/dashboard/inventory"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["total_resources"] == 2
        assert data["untagged_resources_count"] == 1


def test_api_dashboard_data_quality(client: TestClient):
    """Test GET /api/v1/dashboard/data-quality-summary and alias /data-quality."""
    for path in ["/api/v1/dashboard/data-quality-summary", "/api/v1/dashboard/data-quality"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert Decimal(str(data["focus_compliance_percentage"])) == Decimal("100.00")


def test_api_dashboard_export_csv(client: TestClient):
    """Test GET /api/v1/dashboard/export?format=csv."""
    response = client.get("/api/v1/dashboard/export?format=csv&section=overview")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert "Total Cloud Spend" in response.text


def test_api_dashboard_export_json(client: TestClient):
    """Test GET /api/v1/dashboard/export?format=json."""
    response = client.get("/api/v1/dashboard/export?format=json&section=overview")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    assert "total_spend" in response.text


def test_api_dashboard_ui_html(client: TestClient):
    """Test GET /api/v1/dashboard/ui HTML single page app view."""
    response = client.get("/api/v1/dashboard/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "CloudSage" in response.text
    assert "FinOps Command Center" in response.text
    assert "id=\"kpi-total-spend\"" in response.text


def test_api_dashboard_top_level_redirect(client: TestClient):
    """Test GET /dashboard redirecting to /api/v1/dashboard/ui."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code in (307, 302, 301)
    assert response.headers["location"] == "/api/v1/dashboard/ui"
