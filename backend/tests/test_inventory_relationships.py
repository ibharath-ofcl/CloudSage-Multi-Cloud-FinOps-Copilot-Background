"""
CloudSage Resource Relationship & Topology Tests.
Verifies directional relationship persistence, deduplication, and topological graph querying.
"""

from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from backend.app.inventory.models import AdapterDiscoveryResult, DiscoveredRelationship, DiscoveredResource
from backend.app.inventory.reconciliation import InventoryReconciliationEngine
from backend.app.inventory.service import InventoryService
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource


def test_relationship_persistence_and_querying(db_session: Session):
    vm_res = DiscoveredResource(
        resource_id="arn:aws:ec2:us-east-1:111:instance/i-master",
        provider="AWS",
        account_id="111",
        resource_name="master-node",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="active",
        tags={},
        environment="production",
    )
    vol_res = DiscoveredResource(
        resource_id="arn:aws:ec2:us-east-1:111:volume/vol-data",
        provider="AWS",
        account_id="111",
        resource_name="data-vol",
        service_category="STORAGE",
        service_name="AmazonEC2",
        resource_type="ec2:volume",
        region="us-east-1",
        status="in-use",
        tags={},
        environment="production",
    )
    snap_res = DiscoveredResource(
        resource_id="arn:aws:ec2:us-east-1:111:snapshot/snap-bkp",
        provider="AWS",
        account_id="111",
        resource_name="data-backup",
        service_category="STORAGE",
        service_name="AmazonEC2",
        resource_type="ec2:snapshot",
        region="us-east-1",
        status="active",
        tags={},
        environment="production",
    )

    relationships = [
        DiscoveredRelationship(
            source_resource_id=vm_res.resource_id,
            target_resource_id=vol_res.resource_id,
            relationship_type="ATTACHED_TO",
            provider="AWS",
            discovery_source="INVENTORY_EXPORT",
            confidence=Decimal("1.0000"),
            metadata={"device": "/dev/xvdf"},
        ),
        DiscoveredRelationship(
            source_resource_id=snap_res.resource_id,
            target_resource_id=vol_res.resource_id,
            relationship_type="SNAPSHOT_OF",
            provider="AWS",
            discovery_source="INVENTORY_EXPORT",
            confidence=Decimal("1.0000"),
        ),
    ]

    discovery_result = AdapterDiscoveryResult(
        provider="AWS",
        resources=[vm_res, vol_res, snap_res],
        relationships=relationships,
    )

    recon = InventoryReconciliationEngine.reconcile(db=db_session, discovery_result=discovery_result)
    assert recon["relationships_reconciled"] == 2

    # Query relationships connected to the volume
    vol_rels = InventoryService.get_resource_relationships(db=db_session, resource_id=vol_res.resource_id)
    assert len(vol_rels) == 2

    # Query relationships from the VM
    vm_rels = InventoryService.get_resource_relationships(db=db_session, resource_id=vm_res.resource_id)
    assert len(vm_rels) == 1
    assert vm_rels[0].target_resource_id == vol_res.resource_id
    assert vm_rels[0].relationship_type == "ATTACHED_TO"


def test_relationship_deduplication_on_repeated_reconciliation(db_session: Session):
    vm_res = DiscoveredResource(
        resource_id="arn:aws:ec2:us-east-1:111:instance/i-dedup",
        provider="AWS",
        account_id="111",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="active",
        tags={},
        environment="production",
    )
    rel = DiscoveredRelationship(
        source_resource_id=vm_res.resource_id,
        target_resource_id="vol-999",
        relationship_type="ATTACHED_TO",
        provider="AWS",
        confidence=Decimal("1.0000"),
    )

    discovery_result = AdapterDiscoveryResult(
        provider="AWS",
        resources=[vm_res],
        relationships=[rel],
    )

    # First reconciliation
    InventoryReconciliationEngine.reconcile(db=db_session, discovery_result=discovery_result)
    count1 = db_session.query(ResourceRelationship).count()
    assert count1 == 1

    # Second reconciliation with exact same relationship
    InventoryReconciliationEngine.reconcile(db=db_session, discovery_result=discovery_result)
    count2 = db_session.query(ResourceRelationship).count()
    assert count2 == 1  # No duplicate row created
