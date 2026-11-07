"""
CloudSage Inventory REST API Integration Tests.
Verifies all 13 REST endpoints: file uploads, live sync, resource listing, detail,
topology relationships, audit runs, quality assessments, coverage, and cost correlation.
"""

from datetime import datetime, timezone
from decimal import Decimal
import io
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base, get_sync_db
from backend.app.main import app
from backend.app.models.billing import BillingRecord
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource


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


def test_api_import_aws_inventory(client):
    payload = {
        "resources": [
            {
                "resource_id": "arn:aws:ec2:us-east-1:111222333444:instance/i-api-aws-01",
                "account_id": "111222333444",
                "resource_name": "api-aws-vm",
                "service_name": "AmazonEC2",
                "resource_type": "ec2:instance",
                "region": "us-east-1",
                "status": "running",
                "tags": {
                    "Owner": "apiuser@cloud.com",
                    "Environment": "production",
                    "CostCenter": "CC-101",
                },
                "attached_volume_ids": ["vol-api-01"],
            }
        ]
    }
    content = json.dumps(payload).encode("utf-8")
    files = {"file": ("aws_export.json", io.BytesIO(content), "application/json")}
    response = client.post("/api/v1/inventory/import/aws", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["provider"] == "AWS"
    assert data["total_discovered"] == 1
    assert data["new_resources"] == 1
    assert data["relationships_reconciled"] == 1


def test_api_import_azure_inventory(client):
    payload = [
        {
            "id": "/subscriptions/sub-az/resourceGroups/rg-az/providers/Microsoft.Compute/virtualMachines/vm-az-01",
            "name": "vm-az-01",
            "type": "Microsoft.Compute/virtualMachines",
            "location": "eastus",
            "power_state": "VM running",
            "tags": {
                "owner": "azadmin@cloud.com",
                "environment": "production",
            },
        }
    ]
    content = json.dumps(payload).encode("utf-8")
    files = {"file": ("azure_export.json", io.BytesIO(content), "application/json")}
    response = client.post("/api/v1/inventory/import/azure", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["provider"] == "AZURE"
    assert data["total_discovered"] == 1


def test_api_import_gcp_inventory(client):
    payload = {
        "assets": [
            {
                "name": "//compute.googleapis.com/projects/proj-gcp/zones/us-central1-a/instances/gce-01",
                "assetType": "compute.googleapis.com/Instance",
                "location": "us-central1",
                "status": "RUNNING",
                "labels": {
                    "owner": "gcpadmin@cloud.com",
                    "env": "production",
                },
            }
        ]
    }
    content = json.dumps(payload).encode("utf-8")
    files = {"file": ("gcp_export.json", io.BytesIO(content), "application/json")}
    response = client.post("/api/v1/inventory/import/gcp", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["provider"] == "GCP"
    assert data["total_discovered"] == 1


def test_api_sync_live_inventory(client):
    req = {
        "provider": "AWS",
        "regions": ["us-east-1"],
        "resource_types": ["ec2:instance"],
    }
    response = client.post("/api/v1/inventory/sync", json=req)
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "AWS"
    assert "sync_run_id" in data


def test_api_resources_listing_and_filtering(client):
    # Seed a resource first via import
    payload = {
        "resources": [
            {
                "resource_id": "arn:aws:ec2:us-east-1:111:instance/i-filter-test",
                "account_id": "111",
                "resource_name": "filter-test-vm",
                "service_name": "AmazonEC2",
                "resource_type": "ec2:instance",
                "region": "us-east-1",
                "status": "running",
                "tags": {"Environment": "production", "Owner": "dev@test.com"},
            }
        ]
    }
    files = {"file": ("test.json", io.BytesIO(json.dumps(payload).encode("utf-8")), "application/json")}
    client.post("/api/v1/inventory/import/aws", files=files)

    # Test list endpoint
    response = client.get("/api/v1/inventory/resources?provider=AWS&environment=production")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["items"][0]["resource_name"] == "filter-test-vm"


def test_api_resource_detail_and_relationships(client):
    res_id = "arn:aws:ec2:us-east-1:111:instance/i-rel-test"
    vol_id = "vol-rel-test"
    payload = {
        "resources": [
            {
                "resource_id": res_id,
                "account_id": "111",
                "resource_name": "rel-vm",
                "service_name": "AmazonEC2",
                "resource_type": "ec2:instance",
                "region": "us-east-1",
                "status": "running",
                "tags": {"Environment": "production", "Owner": "dev@test.com"},
                "attached_volume_ids": [vol_id],
            }
        ]
    }
    files = {"file": ("test.json", io.BytesIO(json.dumps(payload).encode("utf-8")), "application/json")}
    client.post("/api/v1/inventory/import/aws", files=files)

    # 1. Detail endpoint
    detail_res = client.get(f"/api/v1/inventory/resources/{res_id}")
    assert detail_res.status_code == 200
    d_data = detail_res.json()
    assert d_data["resource_id"] == res_id
    assert len(d_data["relationships"]) == 1

    # 2. Relationships endpoint
    rel_res = client.get(f"/api/v1/inventory/resources/{res_id}/relationships")
    assert rel_res.status_code == 200
    r_data = rel_res.json()
    assert len(r_data) == 1
    assert r_data[0]["target_resource_id"] == vol_id


def test_api_inventory_summary(client):
    response = client.get("/api/v1/inventory/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_resources" in data
    assert "total_monthly_cost" in data
    assert "by_provider" in data
    assert "by_category" in data


def test_api_sync_runs_list_and_detail(client):
    # Import to create a sync run
    payload = {"resources": []}
    files = {"file": ("test.json", io.BytesIO(json.dumps(payload).encode("utf-8")), "application/json")}
    import_resp = client.post("/api/v1/inventory/import/aws", files=files)
    run_id = import_resp.json()["sync_run_id"]

    # List runs
    list_resp = client.get("/api/v1/inventory/sync-runs")
    assert list_resp.status_code == 200
    runs = list_resp.json()
    assert len(runs) >= 1

    # Detail run
    detail_resp = client.get(f"/api/v1/inventory/sync-runs/{run_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["run_id"] == run_id


def test_api_quality_report_endpoint(client):
    response = client.get("/api/v1/inventory/quality-report?run_eval=true")
    assert response.status_code == 200
    data = response.json()
    assert "completeness_score" in data
    assert "tag_completeness_score" in data
    assert "inventory_confidence" in data


def test_api_coverage_endpoint(client):
    response = client.get("/api/v1/inventory/coverage")
    assert response.status_code == 200
    data = response.json()
    assert "total_billing_cost" in data
    assert "cost_coverage_percentage" in data


def test_api_cost_correlation_endpoint(client):
    res_id = "arn:aws:ec2:us-east-1:111:instance/i-corr-api"
    payload = {
        "resources": [
            {
                "resource_id": res_id,
                "account_id": "111",
                "resource_name": "corr-vm",
                "service_name": "AmazonEC2",
                "resource_type": "ec2:instance",
                "region": "us-east-1",
                "status": "running",
                "tags": {"Environment": "production", "Owner": "dev@test.com"},
            }
        ]
    }
    files = {"file": ("test.json", io.BytesIO(json.dumps(payload).encode("utf-8")), "application/json")}
    client.post("/api/v1/inventory/import/aws", files=files)

    response = client.get(f"/api/v1/inventory/cost-correlation?resource_id={res_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["resource_id"] == res_id
    assert "total_billed_cost" in data
    assert "correlation_status" in data
