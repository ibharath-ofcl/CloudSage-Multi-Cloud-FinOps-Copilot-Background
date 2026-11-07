"""
CloudSage Database Models Unit Tests.
Validates table creation, field mappings, relationships, and constraints.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest
from backend.app.models import (
    BillingRecord,
    CloudResource,
    ResourceMetric,
    WasteDetection,
    Recommendation,
    CostAnomaly,
    User,
    AuditLog,
    AlertRule,
    NotificationLog,
)
from backend.app.core.enums import (
    CloudProvider,
    ServiceCategory,
    WasteType,
    Severity,
    WasteStatus,
    RecommendationAction,
    Priority,
    RiskLevel,
    RecommendationStatus,
    ImplementationEffort,
    UserRole,
    AuditAction,
    AlertType,
    NotificationChannel,
)


def test_billing_record_creation(db_session):
    record = BillingRecord(
        provider=CloudProvider.AWS.value,
        billing_account_id="112233445566",
        subscription_id="112233445566",
        resource_id="arn:aws:ec2:us-east-1:112233445566:instance/i-0a1b2c3d4e5f",
        resource_name="prod-checkout-worker-01",
        service_category=ServiceCategory.COMPUTE.value,
        service_name="AmazonEC2",
        region="us-east-1",
        zone="us-east-1a",
        usage_start_time=datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
        usage_end_time=datetime(2026, 11, 1, 1, 0, 0, tzinfo=timezone.utc),
        usage_quantity=Decimal("1.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("0.1920"),
        blended_cost=Decimal("0.1920"),
        list_cost=Decimal("0.1920"),
        currency="USD",
        tags={"owner": "checkout-team", "environment": "production"},
        raw_metadata={"line_item_type": "Usage"}
    )
    db_session.add(record)
    db_session.commit()

    saved = db_session.query(BillingRecord).filter_by(resource_id=record.resource_id).first()
    assert saved is not None
    assert saved.provider == "AWS"
    assert saved.unblended_cost == Decimal("0.1920")
    assert saved.tags["owner"] == "checkout-team"
    assert saved.record_id is not None


def test_cloud_resource_and_metrics_relationship(db_session):
    resource = CloudResource(
        resource_id="arn:aws:ec2:us-east-1:112233445566:instance/i-idle-001",
        provider=CloudProvider.AWS.value,
        account_id="112233445566",
        resource_name="dev-test-instance",
        service_category=ServiceCategory.COMPUTE.value,
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="running",
        tags={"owner": "dev-team", "environment": "dev"},
        owner="dev-team",
        environment="dev",
        cost_center="ENG-101",
        monthly_cost=Decimal("144.0000")
    )
    db_session.add(resource)
    db_session.commit()

    metric = ResourceMetric(
        resource_id=resource.resource_id,
        metric_name="cpu_utilization_pct",
        timestamp=datetime.now(timezone.utc),
        average_value=Decimal("2.4500"),
        peak_value=Decimal("4.8000"),
        sample_count=1440
    )
    db_session.add(metric)
    db_session.commit()

    saved_res = db_session.query(CloudResource).filter_by(resource_id=resource.resource_id).first()
    assert len(saved_res.metrics) == 1
    assert saved_res.metrics[0].average_value == Decimal("2.4500")


def test_waste_detection_and_recommendation_flow(db_session):
    res_id = "arn:aws:ec2:us-east-1:112233445566:instance/i-waste-999"
    resource = CloudResource(
        resource_id=res_id,
        provider=CloudProvider.AWS.value,
        account_id="112233445566",
        service_category=ServiceCategory.COMPUTE.value,
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="running",
        monthly_cost=Decimal("280.0000")
    )
    db_session.add(resource)
    db_session.commit()

    waste = WasteDetection(
        resource_id=res_id,
        provider=CloudProvider.AWS.value,
        waste_type=WasteType.IDLE_VM.value,
        severity=Severity.HIGH.value,
        status=WasteStatus.ACTIVE.value,
        estimated_monthly_waste=Decimal("280.0000"),
        telemetry_proof={"avg_cpu_pct": 1.8, "network_io_mb_day": 0.4}
    )
    db_session.add(waste)
    db_session.commit()

    rec = Recommendation(
        waste_detection_id=waste.id,
        resource_id=res_id,
        provider=CloudProvider.AWS.value,
        action_type=RecommendationAction.SCHEDULE_SHUTDOWN.value,
        priority=Priority.P1.value,
        risk_level=RiskLevel.LOW.value,
        status=RecommendationStatus.PROPOSED.value,
        estimated_monthly_savings=Decimal("196.0000"),
        estimated_annual_savings=Decimal("2352.0000"),
        implementation_effort=ImplementationEffort.LOW.value,
        title="Schedule Nightly Shutdown for Idle Dev Instance",
        description="Instance runs 24x7 with average CPU < 2.0%. Stop instances outside business hours.",
        remediation_guide="aws ec2 stop-instances --instance-ids i-waste-999"
    )
    db_session.add(rec)
    db_session.commit()

    saved_rec = db_session.query(Recommendation).filter_by(id=rec.id).first()
    assert saved_rec is not None
    assert saved_rec.waste_detection.id == waste.id
    assert saved_rec.estimated_annual_savings == Decimal("2352.0000")
    assert saved_rec.status == "PROPOSED"


def test_cost_anomaly_creation(db_session):
    anomaly = CostAnomaly(
        provider=CloudProvider.GCP.value,
        service_category=ServiceCategory.ANALYTICS.value,
        service_name="BigQuery",
        account_id="gcp-analytics-prod",
        region="us-central1",
        anomaly_date=date(2026, 11, 5),
        actual_cost=Decimal("845.5000"),
        expected_cost=Decimal("120.0000"),
        baseline_mean=Decimal("118.2500"),
        baseline_stddev=Decimal("14.5000"),
        z_score=Decimal("50.1500"),
        spike_percentage=Decimal("604.58"),
        severity=Severity.CRITICAL.value,
        status="OPEN",
        root_cause_analysis={"driver": "unpartitioned_query_scan", "slot_hours": 1200}
    )
    db_session.add(anomaly)
    db_session.commit()

    saved = db_session.query(CostAnomaly).filter_by(id=anomaly.id).first()
    assert saved is not None
    assert saved.severity == "CRITICAL"
    assert saved.z_score == Decimal("50.1500")


def test_user_and_audit_log_creation(db_session):
    user = User(
        email="finops.lead@enterprise.com",
        full_name="Alex Mercer",
        hashed_password="argon2_hashed_secret",
        role=UserRole.FINOPS_ENGINEER.value,
        department="Cloud Architecture"
    )
    db_session.add(user)
    db_session.commit()

    audit = AuditLog(
        user_id=user.id,
        user_email=user.email,
        action_type=AuditAction.RECOMMENDATION_APPROVE.value,
        resource_type="recommendation",
        resource_id=str(uuid.uuid4()),
        before_state={"status": "UNDER_REVIEW"},
        after_state={"status": "APPROVED"},
        client_ip="10.0.1.42",
        status="SUCCESS"
    )
    db_session.add(audit)
    db_session.commit()

    saved_audit = db_session.query(AuditLog).filter_by(id=audit.id).first()
    assert saved_audit is not None
    assert saved_audit.user_id == user.id
    assert saved_audit.action_type == "RECOMMENDATION_APPROVE"
