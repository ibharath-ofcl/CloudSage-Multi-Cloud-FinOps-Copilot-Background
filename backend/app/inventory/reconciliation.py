"""
CloudSage Inventory Reconciliation Engine.
Intelligently reconciles discovered resources and directional relationships against
existing PostgreSQL database records with in-place updates, state transitions,
stale resource detection, and zero destructive actions.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session
from backend.app.models.inventory import InventorySyncRun, ResourceRelationship
from backend.app.models.resource import CloudResource
from backend.app.inventory.models import AdapterDiscoveryResult, DiscoveredRelationship, DiscoveredResource


class InventoryReconciliationEngine:
    """Reconciles inventory discovery with existing CloudSage inventory repository."""

    @classmethod
    def reconcile(
        cls,
        db: Session,
        discovery_result: AdapterDiscoveryResult,
        stale_days_threshold: int = 14,
        sync_run_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Executes idempotent reconciliation of discovered resources and relationships.
        Never executes DELETE statements.
        """
        now = datetime.now(timezone.utc)
        provider = discovery_result.provider.upper().strip()

        new_count = 0
        updated_count = 0
        stale_count = 0
        relationships_count = 0

        discovered_ids = set()

        # Step 1: Reconcile Resources
        for r in discovery_result.resources:
            discovered_ids.add(r.resource_id)
            existing: Optional[CloudResource] = (
                db.query(CloudResource)
                .filter(CloudResource.resource_id == r.resource_id)
                .first()
            )

            if existing:
                # In-place update preserving first_discovered_at
                existing.resource_name = r.resource_name or existing.resource_name
                existing.service_category = r.service_category
                existing.service_name = r.service_name
                existing.resource_type = r.resource_type
                existing.region = r.region
                if r.zone:
                    existing.zone = r.zone
                existing.status = r.status
                existing.tags = r.tags
                existing.raw_tags = r.raw_tags
                if r.owner:
                    existing.owner = r.owner
                if r.department:
                    existing.department = r.department
                if r.project:
                    existing.project = r.project
                if r.environment and r.environment != "unknown":
                    existing.environment = r.environment
                if r.cost_center:
                    existing.cost_center = r.cost_center
                existing.tag_quality_score = r.tag_quality_score
                existing.last_seen_at = now
                existing.last_inventory_sync_at = now

                # Transition from BILLING_INFERRED or STALE to CONFIRMED
                if existing.discovery_status in ("BILLING_INFERRED", "STALE", "UNRECONCILED"):
                    existing.discovery_status = "CONFIRMED"
                existing.discovery_source = r.discovery_source

                # Merge metadata
                merged_meta = dict(existing.resource_metadata or {})
                if r.resource_metadata:
                    merged_meta.update(r.resource_metadata)
                existing.resource_metadata = merged_meta

                # Increment version
                try:
                    current_v = float(existing.metadata_version or "1.0")
                    existing.metadata_version = f"{current_v + 0.1:.1f}"
                except Exception:
                    existing.metadata_version = "1.1"

                updated_count += 1
            else:
                # Create brand new inventory record
                new_resource = CloudResource(
                    resource_id=r.resource_id,
                    provider=r.provider,
                    account_id=r.account_id,
                    resource_name=r.resource_name,
                    service_category=r.service_category,
                    service_name=r.service_name,
                    resource_type=r.resource_type,
                    region=r.region,
                    zone=r.zone,
                    status=r.status,
                    tags=r.tags,
                    raw_tags=r.raw_tags,
                    owner=r.owner,
                    department=r.department,
                    project=r.project,
                    environment=r.environment,
                    cost_center=r.cost_center,
                    tag_quality_score=r.tag_quality_score,
                    monthly_cost=Decimal("0.0000"),
                    resource_created_at=r.resource_created_at,
                    first_discovered_at=now,
                    last_seen_at=now,
                    last_inventory_sync_at=now,
                    discovery_source=r.discovery_source,
                    discovery_status="CONFIRMED",
                    resource_metadata=r.resource_metadata or {},
                    metadata_version="1.0",
                )
                db.add(new_resource)
                new_count += 1

        # Flush resources to satisfy Foreign Keys for relationships
        db.flush()

        # Step 2: Stale Resource Policy
        # Check resources of the same provider that were not present in discovery
        if discovered_ids:
            cutoff = now - timedelta(days=stale_days_threshold)
            stale_candidates = (
                db.query(CloudResource)
                .filter(
                    CloudResource.provider == provider,
                    CloudResource.resource_id.notin_(discovered_ids),
                    CloudResource.discovery_status == "CONFIRMED",
                )
                .all()
            )

            for cand in stale_candidates:
                cand_sync = cand.last_inventory_sync_at
                if cand_sync and cand_sync.tzinfo is None:
                    cand_sync = cand_sync.replace(tzinfo=timezone.utc)
                if cand_sync and cand_sync < cutoff:
                    cand.discovery_status = "STALE"
                    stale_count += 1

        # Step 3: Reconcile Directional Relationships
        for rel in discovery_result.relationships:
            # Check source resource exists in DB to prevent foreign key constraint violation
            source_exists = (
                db.query(CloudResource.resource_id)
                .filter(CloudResource.resource_id == rel.source_resource_id)
                .first()
            )
            if not source_exists:
                continue

            existing_rel = (
                db.query(ResourceRelationship)
                .filter(
                    ResourceRelationship.source_resource_id == rel.source_resource_id,
                    ResourceRelationship.target_resource_id == rel.target_resource_id,
                    ResourceRelationship.relationship_type == rel.relationship_type,
                )
                .first()
            )

            if existing_rel:
                existing_rel.last_observed_at = now
                existing_rel.confidence = rel.confidence
                if rel.metadata:
                    m = dict(existing_rel.relationship_metadata or {})
                    m.update(rel.metadata)
                    existing_rel.relationship_metadata = m
            else:
                new_rel = ResourceRelationship(
                    source_resource_id=rel.source_resource_id,
                    target_resource_id=rel.target_resource_id,
                    relationship_type=rel.relationship_type,
                    provider=rel.provider,
                    discovery_source=rel.discovery_source,
                    confidence=rel.confidence,
                    first_observed_at=now,
                    last_observed_at=now,
                    relationship_metadata=rel.metadata or {},
                )
                db.add(new_rel)
            relationships_count += 1

        # Step 4: Update Sync Run if run_id provided
        if sync_run_id:
            sync_run = db.query(InventorySyncRun).filter(InventorySyncRun.run_id == sync_run_id).first()
            if sync_run:
                sync_run.total_discovered = len(discovery_result.resources)
                sync_run.new_resources = new_count
                sync_run.updated_resources = updated_count
                sync_run.stale_resources = stale_count
                sync_run.relationships_discovered = relationships_count
                sync_run.completed_at = now
                sync_run.status = "COMPLETED" if not discovery_result.errors else "PARTIAL_SUCCESS"
                if discovery_result.errors:
                    sync_run.error_details = discovery_result.errors

        db.commit()

        return {
            "total_discovered": len(discovery_result.resources),
            "new_resources": new_count,
            "updated_resources": updated_count,
            "stale_resources": stale_count,
            "relationships_reconciled": relationships_count,
            "errors": discovery_result.errors,
        }
