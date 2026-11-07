"""
CloudSage Cost Anomaly Detection REST API Integration Tests.
Verifies all 14 REST API endpoints: execution runs, anomaly queries, anomaly details,
summaries, baselines, trends, contributors, evidence, run history, detection methods,
financial impact, and status updates.
"""

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base, get_sync_db
from backend.app.core.enums import AnomalyCategory, AnomalyStatus, Severity
from backend.app.main import app
from backend.app.models.anomaly import CostAnomaly, CostBaseline
from backend.app.models.billing import BillingRecord
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


def _seed_api_anomaly_data(engine) -> uuid.UUID:
    """Helper to populate test anomaly, baseline, and billing records."""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    anom_date = date(2026, 10, 15)
    anom_id = uuid.uuid4()
    base_id = uuid.uuid4()

    # 1. CloudResource
    res = CloudResource(
        resource_id="arn:aws:dynamodb:us-east-1:111122223333:table/Orders",
        provider="AWS",
        account_id="111122223333",
        resource_name="OrdersTable",
        service_category="DATABASE",
        service_name="AmazonDynamoDB",
        resource_type="dynamodb:table",
        region="us-east-1",
        status="active",
        owner="orders-team@company.com",
        environment="production",
        project="ECommerce",
        cost_center="CC-ORDERS",
        tags={"owner": "orders-team@company.com", "env": "production"},
    )
    db.add(res)

    # 2. BillingRecord
    dt = datetime.combine(anom_date, time(12, 0), tzinfo=timezone.utc)
    rec = BillingRecord(
        record_id=uuid.uuid4(),
        provider="AWS",
        billing_account_id="111122223333",
        subscription_id="111122223333",
        service_category="DATABASE",
        service_name="AmazonDynamoDB",
        region="us-east-1",
        resource_id="arn:aws:dynamodb:us-east-1:111122223333:table/Orders",
        resource_name="OrdersTable",
        usage_start_time=dt,
        usage_end_time=dt,
        unblended_cost=Decimal("750.0000"),
        blended_cost=Decimal("750.0000"),
        usage_quantity=Decimal("10000.0000"),
        usage_unit="Requests",
        pricing_model="ON_DEMAND",
    )
    db.add(rec)

    # 3. CostAnomaly
    anom = CostAnomaly(
        id=anom_id,
        detector_id="service_cost_spike_detector",
        detector_version="1.0.0",
        provider="AWS",
        account_id="111122223333",
        service_category="DATABASE",
        service_name="AmazonDynamoDB",
        region="us-east-1",
        resource_id="arn:aws:dynamodb:us-east-1:111122223333:table/Orders",
        anomaly_category=AnomalyCategory.SERVICE_SPIKE,
        anomaly_date=anom_date,
        detection_method="Z_SCORE",
        title="Spike on AmazonDynamoDB",
        explanation="Sudden surge in provisioned throughput.",
        actual_cost=Decimal("750.0000"),
        expected_cost=Decimal("150.0000"),
        absolute_deviation=Decimal("600.0000"),
        spike_percentage=Decimal("400.0000"),
        z_score=Decimal("4.5000"),
        estimated_excess_cost=Decimal("600.0000"),
        projected_monthly_impact=Decimal("600.0000"),
        currency="USD",
        status=AnomalyStatus.DETECTED,
        severity=Severity.HIGH,
        confidence_score=Decimal("0.9500"),
        baseline_window_days=30,
        observation_window_days=1,
        baseline_metrics={"mean": "150.0000", "stddev": "20.0000", "median": "150.0000"},
        root_cause_analysis={"status": "ATTRIBUTED", "primary_contributor_type": "RESOURCE"},
        contributing_resources=[
            {
                "resource_id": "arn:aws:dynamodb:us-east-1:111122223333:table/Orders",
                "cost": "750.0000",
                "share_percentage": "100.0000",
                "resource_name": "OrdersTable",
                "owner": "orders-team@company.com",
            }
        ],
        source_billing_references=[str(rec.record_id)],
        first_detected_at=now,
        last_detected_at=now,
    )
    db.add(anom)

    # 4. CostBaseline
    base = CostBaseline(
        id=base_id,
        dimension_type="SERVICE",
        dimension_key="AWS/111122223333/AmazonDynamoDB",
        provider="AWS",
        account_id="111122223333",
        service_name="AmazonDynamoDB",
        region="us-east-1",
        window_days=30,
        start_date=anom_date - timedelta(days=30),
        end_date=anom_date - timedelta(days=1),
        mean=Decimal("150.0000"),
        stddev=Decimal("20.0000"),
        median=Decimal("150.0000"),
        mad=Decimal("15.0000"),
        q1=Decimal("135.0000"),
        q3=Decimal("165.0000"),
        iqr=Decimal("30.0000"),
        min_value=Decimal("110.0000"),
        max_value=Decimal("190.0000"),
        sample_count=30,
        zero_count=0,
        currency="USD",
        version="1.0",
        calculated_at=now,
    )
    db.add(base)

    db.commit()
    db.close()
    return anom_id


def test_api_anomalies_and_detail(client: TestClient, engine):
    """Tests GET /anomalies and GET /anomalies/{id}."""
    anom_id = _seed_api_anomaly_data(engine)

    # 1. List anomalies
    res = client.get("/api/v1/anomaly-detection/anomalies")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["provider"] == "AWS"
    assert data["items"][0]["service_name"] == "AmazonDynamoDB"

    # 2. Get anomaly by ID
    res2 = client.get(f"/api/v1/anomaly-detection/anomalies/{anom_id}")
    assert res2.status_code == 200
    detail = res2.json()
    assert detail["id"] == str(anom_id)
    assert Decimal(detail["actual_cost"]) == Decimal("750.0000")
    assert Decimal(detail["estimated_excess_cost"]) == Decimal("600.0000")


def test_api_summary_and_financial_impact(client: TestClient, engine):
    """Tests GET /summary and GET /financial-impact."""
    _seed_api_anomaly_data(engine)

    # 1. Executive Summary
    res = client.get("/api/v1/anomaly-detection/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_open_anomalies"] == 1
    assert Decimal(summary["total_excess_cost_usd"]) == Decimal("600.0000")
    assert summary["anomalies_by_severity"]["HIGH"] == 1

    # 2. Financial Impact
    res2 = client.get("/api/v1/anomaly-detection/financial-impact")
    assert res2.status_code == 200
    fi = res2.json()
    assert fi["active_anomalies_count"] == 1
    assert Decimal(fi["total_excess_expenditure"]) == Decimal("600.0000")
    assert len(fi["top_cost_spikes"]) == 1


def test_api_baselines_endpoints(client: TestClient, engine):
    """Tests GET /baselines and GET /baselines/{id}."""
    _seed_api_anomaly_data(engine)

    # List baselines
    res = client.get("/api/v1/anomaly-detection/baselines")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    base_item = data["items"][0]
    base_id = base_item["id"]

    # Get baseline by ID
    res2 = client.get(f"/api/v1/anomaly-detection/baselines/{base_id}")
    assert res2.status_code == 200
    detail = res2.json()
    assert detail["service_name"] == "AmazonDynamoDB"
    assert Decimal(detail["mean"]) == Decimal("150.0000")


def test_api_trends_contributors_evidence(client: TestClient, engine):
    """Tests GET /trends/{id}, GET /contributors/{id}, and GET /evidence/{id}."""
    anom_id = _seed_api_anomaly_data(engine)

    # 1. Contributors
    res_contrib = client.get(f"/api/v1/anomaly-detection/contributors/{anom_id}")
    assert res_contrib.status_code == 200
    contrib_data = res_contrib.json()
    assert contrib_data["service_name"] == "AmazonDynamoDB"
    assert len(contrib_data["contributors"]) >= 1

    # 2. Evidence
    res_evidence = client.get(f"/api/v1/anomaly-detection/evidence/{anom_id}")
    assert res_evidence.status_code == 200
    ev = res_evidence.json()
    assert ev["provider"] == "AWS"
    assert ev["detection_method"] == "Z_SCORE"
    assert len(ev["source_billing_references"]) >= 1

    # 3. Trends
    res_trend = client.get(f"/api/v1/anomaly-detection/trends/{anom_id}")
    assert res_trend.status_code == 200
    trend = res_trend.json()
    assert trend["dimension_type"] == "RESOURCE"
    assert len(trend["points"]) >= 1


def test_api_status_update_lifecycle(client: TestClient, engine):
    """Tests PATCH /anomalies/{id}/status for human review transitions."""
    anom_id = _seed_api_anomaly_data(engine)

    # Acknowledge
    res1 = client.patch(
        f"/api/v1/anomaly-detection/anomalies/{anom_id}/status",
        json={"status": "ACKNOWLEDGED", "user": "analyst1", "investigation_notes": "Noted spike."},
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "ACKNOWLEDGED"

    # Dismiss without reason -> 400
    res_bad = client.patch(
        f"/api/v1/anomaly-detection/anomalies/{anom_id}/status",
        json={"status": "DISMISSED", "user": "analyst1"},
    )
    assert res_bad.status_code == 400

    # Dismiss with reason -> 200
    res2 = client.patch(
        f"/api/v1/anomaly-detection/anomalies/{anom_id}/status",
        json={"status": "DISMISSED", "user": "architect1", "reason": "Expected performance test."},
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "DISMISSED"
    assert res2.json()["dismissal_reason"] == "Expected performance test."


def test_api_methods_and_run(client: TestClient, engine):
    """Tests GET /methods and POST /run."""
    # 1. Methods
    res_methods = client.get("/api/v1/anomaly-detection/methods")
    assert res_methods.status_code == 200
    methods = res_methods.json()
    assert len(methods) >= 5

    # 2. Trigger detection run
    res_run = client.post(
        "/api/v1/anomaly-detection/run",
        json={"provider": "ALL", "baseline_window_days": 14},
    )
    assert res_run.status_code == 200
    run_data = res_run.json()
    assert run_data["status"] in ("COMPLETED", "PARTIAL_SUCCESS")
    assert "run_id" in run_data

    # 3. List runs
    res_runs = client.get("/api/v1/anomaly-detection/runs")
    assert res_runs.status_code == 200
    runs = res_runs.json()
    assert len(runs) >= 1

    # 4. Get run by ID
    run_id = run_data["run_id"]
    res_run_detail = client.get(f"/api/v1/anomaly-detection/runs/{run_id}")
    assert res_run_detail.status_code == 200
    assert res_run_detail.json()["run_id"] == run_id
