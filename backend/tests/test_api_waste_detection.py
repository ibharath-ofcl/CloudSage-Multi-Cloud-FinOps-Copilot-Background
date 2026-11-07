"""
CloudSage Waste Detection REST API Integration Tests.
Verifies all 13 REST API endpoints: execution runs, findings query, finding detail,
summaries, categories, provider/account breakdowns, historical runs, savings summary,
catalog of detectors, human-in-the-loop review actions, and telemetry proof inspection.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base, get_sync_db
from backend.app.core.enums import Severity, WasteType
from backend.app.main import app
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection, WasteDetectionRun


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


def _seed_test_data(engine):
    """Helper to populate test resources and findings."""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    res_aws = CloudResource(
        resource_id="arn:aws:ec2:us-east-1:112233445566:instance/i-api-test-01",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        resource_name="api-worker-vm",
        status="active",
        environment="production",
        owner="cloud-ops@company.com",
        monthly_cost=Decimal("150.0000"),
        first_discovered_at=now - timedelta(days=20),
        last_seen_at=now,
    )
    res_azure = CloudResource(
        resource_id="/subscriptions/sub-az-1/resourceGroups/rg-1/providers/Microsoft.Compute/disks/disk-api-01",
        provider="AZURE",
        account_id="sub-az-1",
        region="eastus",
        service_category="STORAGE",
        service_name="Azure Managed Disks",
        resource_type="Microsoft.Compute/disks",
        resource_name="disk-api-01",
        status="available",
        environment="dev",
        owner="dev-team@company.com",
        monthly_cost=Decimal("45.0000"),
        first_discovered_at=now - timedelta(days=15),
        last_seen_at=now,
    )
    db.add_all([res_aws, res_azure])
    db.commit()

    f1 = WasteDetection(
        resource_id=res_aws.resource_id,
        provider="AWS",
        account_id="112233445566",
        resource_type="ec2:instance",
        detector_id="idle_compute_detector",
        detector_version="1.0.0",
        waste_type=WasteType.IDLE_COMPUTE.value,
        finding_title="Idle EC2 Instance",
        explanation="Instance is underutilized over 7 days.",
        severity=Severity.HIGH.value,
        status="ACTIVE",
        confidence_score=Decimal("0.8500"),
        estimated_monthly_waste=Decimal("150.0000"),
        currency="USD",
        observation_window_days=7,
        data_quality_status="VERIFIED",
        requires_human_review=True,
        telemetry_proof={"avg_cpu": 2.1, "peak_cpu": 4.5},
        first_detected_at=now,
        last_evaluated_at=now,
    )
    f2 = WasteDetection(
        resource_id=res_azure.resource_id,
        provider="AZURE",
        account_id="sub-az-1",
        resource_type="Microsoft.Compute/disks",
        detector_id="unattached_storage_detector",
        detector_version="1.0.0",
        waste_type=WasteType.UNATTACHED_STORAGE.value,
        finding_title="Unattached Managed Disk",
        explanation="Disk is unattached for > 3 days.",
        severity=Severity.MEDIUM.value,
        status="ACTIVE",
        confidence_score=Decimal("0.9000"),
        estimated_monthly_waste=Decimal("45.0000"),
        currency="USD",
        observation_window_days=15,
        data_quality_status="VERIFIED",
        requires_human_review=False,
        telemetry_proof={"unattached_days": 15},
        first_detected_at=now,
        last_evaluated_at=now,
    )
    db.add_all([f1, f2])

    run = WasteDetectionRun(
        provider="ALL",
        status="COMPLETED",
        total_resources_evaluated=2,
        findings_created=2,
        findings_updated=0,
        findings_unchanged=0,
        total_estimated_monthly_savings=Decimal("195.0000"),
        started_at=now - timedelta(minutes=5),
        completed_at=now,
    )
    db.add(run)
    db.commit()
    finding_id = str(f1.id)
    run_id = str(run.run_id)
    db.close()
    return finding_id, run_id


def test_api_waste_detection_endpoints(client, engine):
    """Tests all 13 REST API endpoints end-to-end."""
    finding_id, run_id = _seed_test_data(engine)

    # 1. POST /api/v1/waste-detection/run
    resp_run = client.post("/api/v1/waste-detection/run", json={"provider": "AWS", "lookback_days": 7})
    assert resp_run.status_code == 200
    data_run = resp_run.json()
    assert "run_id" in data_run
    assert data_run["status"] in ("COMPLETED", "PARTIAL_SUCCESS")

    # 2. GET /api/v1/waste-detection/findings
    resp_findings = client.get("/api/v1/waste-detection/findings?limit=10")
    assert resp_findings.status_code == 200
    data_findings = resp_findings.json()
    assert data_findings["total"] >= 2
    assert len(data_findings["items"]) >= 2

    # 3. GET /api/v1/waste-detection/findings/{finding_id}
    resp_finding_detail = client.get(f"/api/v1/waste-detection/findings/{finding_id}")
    assert resp_finding_detail.status_code == 200
    data_detail = resp_finding_detail.json()
    assert data_detail["id"] == finding_id
    assert data_detail["waste_type"] == WasteType.IDLE_COMPUTE.value
    assert float(data_detail["estimated_monthly_savings"]) == 150.0

    # 4. GET /api/v1/waste-detection/summary
    resp_summary = client.get("/api/v1/waste-detection/summary")
    assert resp_summary.status_code == 200
    data_summary = resp_summary.json()
    assert data_summary["total_open_findings"] >= 2
    assert float(data_summary["total_estimated_monthly_savings"]) >= 195.0
    assert "findings_by_severity" in data_summary
    assert "findings_by_category" in data_summary
    assert "savings_by_provider" in data_summary

    # 5. GET /api/v1/waste-detection/categories
    resp_cats = client.get("/api/v1/waste-detection/categories")
    assert resp_cats.status_code == 200
    data_cats = resp_cats.json()
    assert data_cats["total_categories"] >= 2

    # 6. GET /api/v1/waste-detection/by-provider
    resp_prov = client.get("/api/v1/waste-detection/by-provider")
    assert resp_prov.status_code == 200
    data_prov = resp_prov.json()
    assert len(data_prov["providers"]) >= 2

    # 7. GET /api/v1/waste-detection/by-account
    resp_acc = client.get("/api/v1/waste-detection/by-account")
    assert resp_acc.status_code == 200
    data_acc = resp_acc.json()
    assert data_acc["total_accounts"] >= 2

    # 8. GET /api/v1/waste-detection/runs
    resp_runs = client.get("/api/v1/waste-detection/runs?limit=10")
    assert resp_runs.status_code == 200
    data_runs = resp_runs.json()
    assert len(data_runs) >= 1

    # 9. GET /api/v1/waste-detection/runs/{run_id}
    resp_run_detail = client.get(f"/api/v1/waste-detection/runs/{run_id}")
    assert resp_run_detail.status_code == 200
    data_run_item = resp_run_detail.json()
    assert data_run_item["run_id"] == run_id

    # 10. GET /api/v1/waste-detection/savings-summary
    resp_savings = client.get("/api/v1/waste-detection/savings-summary")
    assert resp_savings.status_code == 200
    data_savings = resp_savings.json()
    assert data_savings["currency"] == "USD"
    assert float(data_savings["total_estimated_monthly_savings"]) >= 195.0
    assert float(data_savings["total_estimated_annual_savings"]) >= 195.0 * 12.0

    # 11. GET /api/v1/waste-detection/detectors
    resp_dets = client.get("/api/v1/waste-detection/detectors")
    assert resp_dets.status_code == 200
    data_dets = resp_dets.json()
    assert len(data_dets) >= 7

    # 12. PATCH /api/v1/waste-detection/findings/{finding_id}/status
    resp_patch = client.patch(
        f"/api/v1/waste-detection/findings/{finding_id}/status",
        json={"status": "ACKNOWLEDGED", "user": "finops@company.com"},
    )
    assert resp_patch.status_code == 200
    data_patch = resp_patch.json()
    assert data_patch["status"] == "ACKNOWLEDGED"

    # Test invalid status returns 400
    resp_invalid = client.patch(
        f"/api/v1/waste-detection/findings/{finding_id}/status",
        json={"status": "INVALID_STATE"},
    )
    assert resp_invalid.status_code == 400

    # 13. GET /api/v1/waste-detection/findings/{finding_id}/evidence
    resp_ev = client.get(f"/api/v1/waste-detection/findings/{finding_id}/evidence")
    assert resp_ev.status_code == 200
    data_ev = resp_ev.json()
    assert data_ev["finding_id"] == finding_id
    assert "telemetry_proof" in data_ev
    assert data_ev["observation_window_days"] == 7
