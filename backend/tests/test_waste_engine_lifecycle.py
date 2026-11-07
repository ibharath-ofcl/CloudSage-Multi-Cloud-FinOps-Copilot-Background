"""
Tests for Waste Detection Engine Lifecycle and State Transitions.
Validates batch evaluation, deduplication, state transitions (ACTIVE, RESOLVED, REOPENED),
human review workflows (ACKNOWLEDGED, DISMISSED, SNOOZED), and audit run tracking.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from backend.app.core.enums import Severity, WasteStatus, WasteType
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection, WasteDetectionRun
from backend.app.waste_detection.engine import WasteDetectionEngine


def test_batch_waste_detection_and_deduplication(db_session: Session):
    """
    Verifies batch evaluation across multiple resources and guarantees
    that running detection repeatedly updates findings in-place with zero duplicates.
    """
    now = datetime.now(timezone.utc)

    # 1. Seed two unattached disks
    vol1 = CloudResource(
        resource_id="vol-test-dedup-01",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="STORAGE",
        service_name="AmazonEC2",
        resource_type="ec2:volume",
        resource_name="unattached-vol-1",
        status="available",
        monthly_cost=Decimal("50.0000"),
        first_discovered_at=now - timedelta(days=10),
        last_seen_at=now,
    )
    vol2 = CloudResource(
        resource_id="vol-test-dedup-02",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="STORAGE",
        service_name="AmazonEC2",
        resource_type="ec2:volume",
        resource_name="unattached-vol-2",
        status="available",
        monthly_cost=Decimal("75.0000"),
        first_discovered_at=now - timedelta(days=20),
        last_seen_at=now,
    )
    db_session.add_all([vol1, vol2])
    db_session.commit()

    # 2. First Run: Should create 2 findings
    run1 = WasteDetectionEngine.execute_detection_run(
        db=db_session,
        provider="AWS",
        lookback_days=7,
    )

    assert run1.status == "COMPLETED"
    assert run1.total_resources_evaluated >= 2
    assert run1.findings_created == 2
    assert run1.total_estimated_monthly_savings == Decimal("125.0000")

    total_findings = db_session.query(WasteDetection).count()
    assert total_findings == 2

    # 3. Second Run: Re-evaluate identical resources
    run2 = WasteDetectionEngine.execute_detection_run(
        db=db_session,
        provider="AWS",
        lookback_days=7,
    )

    assert run2.status == "COMPLETED"
    assert run2.findings_created == 0
    assert run2.findings_updated == 2

    # Findings in database must still be exactly 2 (zero duplicates!)
    total_findings_after = db_session.query(WasteDetection).count()
    assert total_findings_after == 2


def test_waste_lifecycle_resolution_and_reopening(db_session: Session):
    """
    Verifies that when a flagged resource becomes clean it transitions to RESOLVED,
    and if waste reappears it transitions to REOPENED.
    """
    now = datetime.now(timezone.utc)
    vol_id = "vol-lifecycle-01"
    vm_id = "i-worker-server-01"

    vol = CloudResource(
        resource_id=vol_id,
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="STORAGE",
        service_name="AmazonEC2",
        resource_type="ec2:volume",
        status="available",
        monthly_cost=Decimal("60.0000"),
        first_discovered_at=now - timedelta(days=15),
        last_seen_at=now,
    )
    vm = CloudResource(
        resource_id=vm_id,
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        status="running",
        monthly_cost=Decimal("150.0000"),
        first_discovered_at=now - timedelta(days=15),
        last_seen_at=now,
    )
    db_session.add_all([vol, vm])
    db_session.commit()

    # Step 1: Detect unattached volume -> ACTIVE
    WasteDetectionEngine.execute_detection_run(db=db_session, provider="AWS")
    finding = db_session.query(WasteDetection).filter(WasteDetection.resource_id == vol_id).first()
    assert finding is not None
    assert finding.status == "ACTIVE"

    # Step 2: Resource is attached to a VM -> Becomes clean -> RESOLVED
    rel = ResourceRelationship(
        source_resource_id=vm_id,
        target_resource_id=vol_id,
        relationship_type="ATTACHED_TO",
        provider="AWS",
    )
    db_session.add(rel)
    vol.status = "in-use"
    db_session.commit()

    WasteDetectionEngine.execute_detection_run(db=db_session, provider="AWS")
    finding_resolved = db_session.query(WasteDetection).filter(WasteDetection.resource_id == vol_id).first()
    assert finding_resolved.status == "RESOLVED"

    # Step 3: Resource is detached again -> Waste recurs -> REOPENED
    db_session.delete(rel)
    vol.status = "available"
    db_session.commit()

    WasteDetectionEngine.execute_detection_run(db=db_session, provider="AWS")
    finding_reopened = db_session.query(WasteDetection).filter(WasteDetection.resource_id == vol_id).first()
    assert finding_reopened.status == "REOPENED"


def test_human_review_status_updates(db_session: Session):
    """
    Tests reviewer actions: Acknowledge, Dismiss with reason/user, and Snooze with duration.
    """
    now = datetime.now(timezone.utc)
    finding = WasteDetection(
        resource_id="i-review-test-01",
        provider="AWS",
        account_id="112233445566",
        resource_type="ec2:instance",
        detector_id="idle_compute_detector",
        detector_version="1.0.0",
        waste_type=WasteType.IDLE_COMPUTE.value,
        finding_title="Idle Compute Test",
        severity=Severity.HIGH.value,
        status="ACTIVE",
        confidence_score=Decimal("0.8500"),
        estimated_monthly_waste=Decimal("150.0000"),
        currency="USD",
        observation_window_days=7,
        data_quality_status="VERIFIED",
        requires_human_review=True,
        first_detected_at=now,
        last_evaluated_at=now,
    )
    db_session.add(finding)
    db_session.commit()
    db_session.refresh(finding)

    # 1. Acknowledge
    ack = WasteDetectionEngine.update_finding_status(
        db=db_session,
        finding_id=finding.id,
        new_status="ACKNOWLEDGED",
        user="finops-lead@company.com",
    )
    assert ack.status == "ACKNOWLEDGED"

    # 2. Dismiss with rationale
    dismissed = WasteDetectionEngine.update_finding_status(
        db=db_session,
        finding_id=finding.id,
        new_status="DISMISSED",
        reason="Instance is a standby failover node for disaster recovery",
        user="devops-eng@company.com",
    )
    assert dismissed.status == "DISMISSED"
    assert dismissed.dismissal_reason == "Instance is a standby failover node for disaster recovery"
    assert dismissed.dismissed_by == "devops-eng@company.com"

    # 3. Snooze for 14 days
    snoozed = WasteDetectionEngine.update_finding_status(
        db=db_session,
        finding_id=finding.id,
        new_status="SNOOZED",
        reason="Evaluating decommissioning in next sprint",
        user="finops-lead@company.com",
        snooze_days=14,
    )
    assert snoozed.status == "SNOOZED"
    assert snoozed.snooze_until is not None
    snooze_dt = snoozed.snooze_until if snoozed.snooze_until.tzinfo else snoozed.snooze_until.replace(tzinfo=timezone.utc)
    assert snooze_dt > now + timedelta(days=13)


def test_waste_engine_listing_and_summary(db_session: Session):
    """
    Tests multi-faceted filtering in list_findings and executive summary aggregation.
    """
    now = datetime.now(timezone.utc)

    # Create associated cloud resource for join
    res_aws = CloudResource(
        resource_id="vol-summary-aws",
        provider="AWS",
        account_id="acc-aws-01",
        region="us-east-1",
        service_category="STORAGE",
        service_name="AmazonEC2",
        resource_type="ec2:volume",
        environment="production",
        owner="storage-team@company.com",
        monthly_cost=Decimal("100.0000"),
        first_discovered_at=now,
        last_seen_at=now,
    )
    res_gcp = CloudResource(
        resource_id="disk-summary-gcp",
        provider="GCP",
        account_id="proj-gcp-01",
        region="us-central1",
        service_category="STORAGE",
        service_name="ComputeEngine",
        resource_type="gcp:disk",
        environment="staging",
        owner="dev-team@company.com",
        monthly_cost=Decimal("40.0000"),
        first_discovered_at=now,
        last_seen_at=now,
    )
    db_session.add_all([res_aws, res_gcp])
    db_session.commit()

    f1 = WasteDetection(
        resource_id="vol-summary-aws",
        provider="AWS",
        account_id="acc-aws-01",
        resource_type="ec2:volume",
        detector_id="unattached_storage_detector",
        detector_version="1.0.0",
        waste_type=WasteType.UNATTACHED_STORAGE.value,
        finding_title="Unattached AWS Disk",
        severity=Severity.HIGH.value,
        status="ACTIVE",
        confidence_score=Decimal("0.9000"),
        estimated_monthly_waste=Decimal("100.0000"),
        currency="USD",
        observation_window_days=7,
        data_quality_status="VERIFIED",
        requires_human_review=False,
        first_detected_at=now,
        last_evaluated_at=now,
    )
    f2 = WasteDetection(
        resource_id="disk-summary-gcp",
        provider="GCP",
        account_id="proj-gcp-01",
        resource_type="gcp:disk",
        detector_id="unattached_storage_detector",
        detector_version="1.0.0",
        waste_type=WasteType.UNATTACHED_STORAGE.value,
        finding_title="Unattached GCP Disk",
        severity=Severity.MEDIUM.value,
        status="ACTIVE",
        confidence_score=Decimal("0.8500"),
        estimated_monthly_waste=Decimal("40.0000"),
        currency="USD",
        observation_window_days=7,
        data_quality_status="VERIFIED",
        requires_human_review=False,
        first_detected_at=now,
        last_evaluated_at=now,
    )
    db_session.add_all([f1, f2])
    db_session.commit()

    # 1. Filter by provider
    aws_list = WasteDetectionEngine.list_findings(db=db_session, provider="AWS")
    assert aws_list["total"] == 1
    assert aws_list["items"][0].resource_id == "vol-summary-aws"

    # 2. Filter by min_savings
    high_savings_list = WasteDetectionEngine.list_findings(db=db_session, min_savings=Decimal("50.0000"))
    assert high_savings_list["total"] == 1
    assert high_savings_list["items"][0].resource_id == "vol-summary-aws"

    # 3. Summary
    summary = WasteDetectionEngine.get_summary(db=db_session)
    assert summary["total_open_findings"] == 2
    assert summary["total_estimated_monthly_savings"] == Decimal("140.0000")
    assert summary["savings_by_provider"]["AWS"] == Decimal("100.0000")
    assert summary["savings_by_provider"]["GCP"] == Decimal("40.0000")
    assert summary["findings_by_severity"]["HIGH"] == 1
    assert summary["findings_by_severity"]["MEDIUM"] == 1
