"""
CloudSage Inventory Reconciliation Engine Tests.
Verifies insertion, in-place updates, state transitions, stale asset handling,
and strict non-destructive persistence guarantees.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from backend.app.inventory.models import AdapterDiscoveryResult, DiscoveredRelationship, DiscoveredResource
from backend.app.inventory.reconciliation import InventoryReconciliationEngine
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource


def test_reconciliation_new_resource_insertion(db_session: Session):
    res = DiscoveredResource(
        resource_id="arn:aws:ec2:us-east-1:111:instance/i-new",
        provider="AWS",
        account_id="111",
        resource_name="web-new",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        zone="us-east-1a",
        status="active",
        tags={"environment": "production", "owner": "admin@cloud.com"},
        raw_tags={"Environment": "production", "Owner": "admin@cloud.com"},
        owner="admin@cloud.com",
        department="Platform",
        project="Migration",
        environment="production",
        cost_center="CC-99",
        tag_quality_score=Decimal("100.00"),
        discovery_source="INVENTORY_EXPORT",
        discovery_status="CONFIRMED",
        resource_metadata={"instance_type": "t3.large"},
    )
    discovery_result = AdapterDiscoveryResult(
        provider="AWS",
        resources=[res],
        relationships=[],
    )

    result = InventoryReconciliationEngine.reconcile(db=db_session, discovery_result=discovery_result)
    assert result["new_resources"] == 1
    assert result["updated_resources"] == 0

    saved = db_session.query(CloudResource).filter(CloudResource.resource_id == res.resource_id).first()
    assert saved is not None
    assert saved.resource_name == "web-new"
    assert saved.discovery_status == "CONFIRMED"
    assert saved.discovery_source == "INVENTORY_EXPORT"
    assert saved.metadata_version == "1.0"
    assert saved.resource_metadata["instance_type"] == "t3.large"


def test_reconciliation_in_place_update_preserves_first_discovered(db_session: Session):
    old_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    initial_res = CloudResource(
        resource_id="arn:aws:ec2:us-east-1:111:instance/i-existing",
        provider="AWS",
        account_id="111",
        resource_name="old-name",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="active",
        tags={},
        environment="development",
        first_discovered_at=old_time,
        last_seen_at=old_time,
        discovery_source="BILLING_INFERRED",
        discovery_status="BILLING_INFERRED",
        metadata_version="1.0",
    )
    db_session.add(initial_res)
    db_session.commit()

    # Reconcile with updated inventory data
    updated_discovered = DiscoveredResource(
        resource_id="arn:aws:ec2:us-east-1:111:instance/i-existing",
        provider="AWS",
        account_id="111",
        resource_name="new-renamed-vm",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        zone="us-east-1b",
        status="stopped",
        tags={"environment": "production", "owner": "newowner@enterprise.com"},
        owner="newowner@enterprise.com",
        environment="production",
        tag_quality_score=Decimal("80.00"),
        discovery_source="INVENTORY_EXPORT",
        discovery_status="CONFIRMED",
        resource_metadata={"instance_type": "m5.large"},
    )
    discovery_result = AdapterDiscoveryResult(
        provider="AWS",
        resources=[updated_discovered],
        relationships=[],
    )

    recon = InventoryReconciliationEngine.reconcile(db=db_session, discovery_result=discovery_result)
    assert recon["new_resources"] == 0
    assert recon["updated_resources"] == 1

    refreshed = db_session.query(CloudResource).filter(CloudResource.resource_id == initial_res.resource_id).first()
    assert refreshed.resource_name == "new-renamed-vm"
    assert refreshed.status == "stopped"
    assert refreshed.discovery_status == "CONFIRMED"  # Transitioned from BILLING_INFERRED
    first_disc = refreshed.first_discovered_at if refreshed.first_discovered_at.tzinfo else refreshed.first_discovered_at.replace(tzinfo=timezone.utc)
    assert first_disc == old_time  # STRICT PRESERVATION!
    last_sync = refreshed.last_inventory_sync_at if refreshed.last_inventory_sync_at.tzinfo else refreshed.last_inventory_sync_at.replace(tzinfo=timezone.utc)
    assert last_sync > old_time
    assert refreshed.metadata_version == "1.1"


def test_reconciliation_stale_policy_no_deletion(db_session: Session):
    now = datetime.now(timezone.utc)
    twenty_days_ago = now - timedelta(days=20)

    # Resource that hasn't been seen for 20 days
    stale_resource = CloudResource(
        resource_id="arn:aws:ec2:us-east-1:111:instance/i-disappeared",
        provider="AWS",
        account_id="111",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="active",
        tags={},
        environment="production",
        first_discovered_at=twenty_days_ago,
        last_seen_at=twenty_days_ago,
        last_inventory_sync_at=twenty_days_ago,
        discovery_source="INVENTORY_EXPORT",
        discovery_status="CONFIRMED",
    )
    db_session.add(stale_resource)
    db_session.commit()

    # Reconcile an export that does NOT include i-disappeared
    active_resource = DiscoveredResource(
        resource_id="arn:aws:ec2:us-east-1:111:instance/i-current",
        provider="AWS",
        account_id="111",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="active",
        tags={},
        environment="production",
        discovery_source="INVENTORY_EXPORT",
        discovery_status="CONFIRMED",
    )
    discovery_result = AdapterDiscoveryResult(
        provider="AWS",
        resources=[active_resource],
        relationships=[],
    )

    recon = InventoryReconciliationEngine.reconcile(
        db=db_session,
        discovery_result=discovery_result,
        stale_days_threshold=14,
    )
    assert recon["stale_resources"] == 1

    # Verify resource was NOT deleted from DB, but marked STALE
    all_resources = db_session.query(CloudResource).all()
    assert len(all_resources) == 2

    stale_record = db_session.query(CloudResource).filter(CloudResource.resource_id == stale_resource.resource_id).first()
    assert stale_record is not None
    assert stale_record.discovery_status == "STALE"
