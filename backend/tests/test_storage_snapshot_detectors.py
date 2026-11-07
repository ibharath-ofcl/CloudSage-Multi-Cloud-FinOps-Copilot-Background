"""
Tests for Unattached Storage and Orphaned Snapshot Detectors.
Validates block storage topology, unattached age, snapshot parent relationships, and retention tag safeguards.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from backend.app.core.enums import Severity, WasteType
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource
from backend.app.waste_detection.detectors.orphaned_snapshots import OrphanedSnapshotsDetector
from backend.app.waste_detection.detectors.unattached_storage import UnattachedStorageDetector


def test_unattached_ebs_volume_flagged():
    """Available EBS volume unattached for > 3 days generates an unattached storage finding."""
    detector = UnattachedStorageDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="vol-0123456789abcdef0",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="STORAGE",
        service_name="AmazonEC2",
        resource_type="ec2:volume",
        resource_name="unused-data-disk",
        status="available",
        monthly_cost=Decimal("40.0000"),
        first_discovered_at=now - timedelta(days=15),
        last_seen_at=now,
        resource_metadata={"size_gb": 400},
    )

    result = detector.detect(resource=resource, metrics=[], relationships=[], billing_records=[])
    assert result.status == "DETECTED"
    assert result.finding is not None
    assert result.finding.waste_type == WasteType.UNATTACHED_STORAGE
    assert result.finding.estimated_monthly_savings == Decimal("40.0000")
    assert result.finding.confidence_score >= Decimal("0.7000")


def test_attached_storage_volume_clean():
    """Volume with active ATTACHED_TO relationship in topology graph is CLEAN."""
    detector = UnattachedStorageDetector()
    now = datetime.now(timezone.utc)

    volume_id = "vol-attached-001"
    vm_id = "i-app-server-01"

    resource = CloudResource(
        resource_id=volume_id,
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="STORAGE",
        service_name="AmazonEC2",
        resource_type="ec2:volume",
        status="in-use",
        monthly_cost=Decimal("25.0000"),
        first_discovered_at=now - timedelta(days=60),
        last_seen_at=now,
    )

    # Inbound relationship from compute VM to storage volume
    relationships = [
        ResourceRelationship(
            source_resource_id=vm_id,
            target_resource_id=volume_id,
            relationship_type="ATTACHED_TO",
        )
    ]

    result = detector.detect(resource=resource, metrics=[], relationships=relationships, billing_records=[])
    assert result.status == "CLEAN"
    assert result.finding is None


def test_unattached_volume_within_grace_period_clean():
    """Unattached disk created less than 3 days ago is in grace period and returns CLEAN."""
    detector = UnattachedStorageDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="vol-new-disk-99",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="STORAGE",
        service_name="AmazonEC2",
        resource_type="ec2:volume",
        status="available",
        monthly_cost=Decimal("30.0000"),
        first_discovered_at=now - timedelta(days=1),  # Only 1 day old
        last_seen_at=now,
    )

    result = detector.detect(resource=resource, metrics=[], relationships=[], billing_records=[])
    assert result.status == "CLEAN"
    assert result.finding is None


def test_orphaned_snapshot_flagged():
    """Snapshot > 30 days old with no active parent volume is flagged as orphaned snapshot."""
    detector = OrphanedSnapshotsDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="snap-0123456789abcdef0",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="STORAGE",
        service_name="AmazonEC2",
        resource_type="ec2:snapshot",
        resource_name="legacy-backup",
        status="completed",
        monthly_cost=Decimal("15.0000"),
        first_discovered_at=now - timedelta(days=45),
        last_seen_at=now,
        resource_metadata={"size_gb": 300},
        tags={},
    )

    result = detector.detect(resource=resource, metrics=[], relationships=[], billing_records=[])
    assert result.status == "DETECTED"
    assert result.finding is not None
    assert result.finding.waste_type == WasteType.ORPHANED_SNAPSHOT
    assert result.finding.estimated_monthly_savings == Decimal("15.0000")
    assert result.finding.confidence_score >= Decimal("0.7000")


def test_orphaned_snapshot_compliance_tag_safeguard():
    """Snapshot > 30 days old with compliance or retention tags is ignored as intentional backup."""
    detector = OrphanedSnapshotsDetector()
    now = datetime.now(timezone.utc)

    resource = CloudResource(
        resource_id="snap-audit-backup-01",
        provider="AWS",
        account_id="112233445566",
        region="us-east-1",
        service_category="STORAGE",
        service_name="AmazonEC2",
        resource_type="ec2:snapshot",
        resource_name="sox-compliance-snapshot",
        status="completed",
        monthly_cost=Decimal("50.0000"),
        first_discovered_at=now - timedelta(days=90),
        last_seen_at=now,
        tags={"compliance": "sox-audit", "retention": "7-years"},
    )

    result = detector.detect(resource=resource, metrics=[], relationships=[], billing_records=[])
    assert result.status == "CLEAN"
    assert result.finding is None
