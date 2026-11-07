"""
CloudSage Ingestion REST API Integration Tests.
Category G: File upload endpoints, extension validation, synthetic generation, and run tracking APIs.
"""

import io
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import Base, get_sync_db
from backend.app.main import app


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


def test_api_ingest_aws_success(client):
    csv_content = """identity/LineItemId,bill/PayerAccountId,lineItem/UsageAccountId,lineItem/LineItemType,lineItem/UsageStartDate,lineItem/UsageEndDate,lineItem/ProductCode,lineItem/UsageAmount,pricing/unit,lineItem/UnblendedCost,lineItem/CurrencyCode,lineItem/ResourceId,product/region
api-aws-01,112233445566,112233445566,Usage,2026-11-01T00:00:00Z,2026-11-01T01:00:00Z,AmazonEC2,1.0,HOURS,0.1920,USD,arn:aws:ec2:us-east-1:112233445566:instance/i-api,us-east-1
"""
    files = {"file": ("cur_sample.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/api/v1/ingestion/aws", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["provider"] == "AWS"
    assert data["ingested_records"] == 1
    assert data["total_records"] == 1


def test_api_ingest_azure_success(client):
    csv_content = """BillingAccountId,SubscriptionId,ResourceGroup,ResourceId,ResourceName,MeterCategory,MeterSubCategory,ConsumedService,Date,Quantity,UnitOfMeasure,CostInBillingCurrency,BillingCurrency,ResourceLocation
EA-999,sub-api,rg-api,/subscriptions/sub-api/resourceGroups/rg-api/providers/Microsoft.Compute/vm-api,vm-api,Virtual Machines,D Series,Virtual Machines,2026-11-01,1.0,Hours,0.1500,USD,eastus
"""
    files = {"file": ("azure_sample.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    response = client.post("/api/v1/ingestion/azure", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["provider"] == "AZURE"
    assert data["ingested_records"] == 1


def test_api_ingest_gcp_success(client):
    gcp_json = [
        {
            "billing_account_id": "01ABCD-23EFGH-45IJKL",
            "project": {"id": "gcp-api-project"},
            "service": {"description": "Compute Engine"},
            "usage_start_time": "2026-11-01T00:00:00Z",
            "cost": 1.2500,
            "currency": "USD",
            "usage": {"amount": 1.0, "unit": "hour"}
        }
    ]
    files = {"file": ("gcp_sample.json", io.BytesIO(json.dumps(gcp_json).encode("utf-8")), "application/json")}
    response = client.post("/api/v1/ingestion/gcp", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["provider"] == "GCP"
    assert data["ingested_records"] == 1


def test_api_unsupported_file_extension(client):
    """Verifies that non-permitted file extensions (e.g. .txt, .exe) are rejected with 400 Bad Request."""
    files = {"file": ("unsupported.txt", io.BytesIO(b"random content"), "text/plain")}
    response = client.post("/api/v1/ingestion/aws", files=files)

    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_api_synthetic_generation_endpoint(client):
    """Verifies that POST /api/v1/ingestion/synthetic/generate triggers dataset creation."""
    payload = {
        "record_count": 30,
        "seed": 42
    }
    response = client.post("/api/v1/ingestion/synthetic/generate", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "generated"
    assert data["total_records_generated"] == 30
    assert "aws" in data["files_created"]
    assert "azure" in data["files_created"]
    assert "gcp" in data["files_created"]


def test_api_ingestion_runs_and_summary(client):
    """Verifies historical run listing and global summary calculation."""
    # First ingest a record to populate runs
    csv_content = """identity/LineItemId,bill/PayerAccountId,lineItem/UsageAccountId,lineItem/LineItemType,lineItem/UsageStartDate,lineItem/UsageEndDate,lineItem/ProductCode,lineItem/UsageAmount,pricing/unit,lineItem/UnblendedCost,lineItem/CurrencyCode,lineItem/ResourceId,product/region
run-01,112233445566,112233445566,Usage,2026-11-01T00:00:00Z,2026-11-01T01:00:00Z,AmazonEC2,1.0,HOURS,1.5000,USD,arn:aws:ec2:us-east-1:112233445566:instance/i-run,us-east-1
"""
    files = {"file": ("run_test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    client.post("/api/v1/ingestion/aws", files=files)

    # Test GET /api/v1/ingestion/runs
    runs_res = client.get("/api/v1/ingestion/runs")
    assert runs_res.status_code == 200
    runs = runs_res.json()
    assert len(runs) >= 1
    run_id = runs[0]["id"]

    # Test GET /api/v1/ingestion/runs/{run_id}
    single_res = client.get(f"/api/v1/ingestion/runs/{run_id}")
    assert single_res.status_code == 200
    assert single_res.json()["id"] == run_id

    # Test GET /api/v1/ingestion/summary
    summary_res = client.get("/api/v1/ingestion/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_runs"] >= 1
    assert summary["total_records_ingested"] >= 1
    assert float(summary["total_cost_ingested_usd"]) > 0.0
