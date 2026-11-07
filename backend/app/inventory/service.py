"""
CloudSage Inventory Service Facade.
High-level operational orchestrator managing resource discovery, reconciliation,
topological queries, financial correlation, quality reporting, and audit runs.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.models.inventory import (
    InventoryQualityReport,
    InventorySyncRun,
    ResourceRelationship,
)
from backend.app.models.resource import CloudResource
from backend.app.inventory.correlation import BillingCorrelationEngine
from backend.app.inventory.discovery import InventoryDiscoveryService
from backend.app.inventory.quality import InventoryQualityEvaluator
from backend.app.inventory.reconciliation import InventoryReconciliationEngine


class InventoryService:
    """Primary facade for CloudSage Inventory & Resource Intelligence operations."""

    @classmethod
    def import_inventory_file(
        cls,
        db: Session,
        provider: str,
        stream_or_path: Any,
        source_identifier: str = "export_file",
        evaluate_quality: bool = True,
    ) -> Dict[str, Any]:
        """Executes full Mode A inventory file import and reconciliation workflow."""
        now = datetime.now(timezone.utc)
        sync_run = InventorySyncRun(
            provider=provider.upper(),
            discovery_mode="EXPORT_BASED",
            status="RUNNING",
            source_identifier=source_identifier,
            started_at=now,
        )
        db.add(sync_run)
        db.commit()
        db.refresh(sync_run)

        # 1. Discover
        discovery_res = InventoryDiscoveryService.discover_from_export(
            stream_or_path=stream_or_path,
            provider=provider,
            source_identifier=source_identifier,
        )

        # 2. Reconcile
        recon_result = InventoryReconciliationEngine.reconcile(
            db=db,
            discovery_result=discovery_res,
            sync_run_id=sync_run.run_id,
        )

        # 3. Correlate monthly costs
        BillingCorrelationEngine.sync_resource_monthly_costs(db)

        # 4. Optional quality evaluation
        quality_rep = None
        if evaluate_quality:
            quality_rep = InventoryQualityEvaluator.evaluate(
                db=db,
                provider=provider,
                sync_run_id=sync_run.run_id,
                persist=True,
            )

        db.refresh(sync_run)
        return {
            "sync_run_id": str(sync_run.run_id),
            "status": sync_run.status,
            "provider": sync_run.provider,
            "total_discovered": recon_result["total_discovered"],
            "new_resources": recon_result["new_resources"],
            "updated_resources": recon_result["updated_resources"],
            "stale_resources": recon_result["stale_resources"],
            "relationships_reconciled": recon_result["relationships_reconciled"],
            "quality_score": float(quality_rep.completeness_score) if quality_rep else 100.0,
            "errors": recon_result["errors"],
        }

    @classmethod
    def run_live_discovery(
        cls,
        db: Session,
        provider: str,
        regions: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
        evaluate_quality: bool = True,
    ) -> Dict[str, Any]:
        """Executes read-only Mode B live discovery against hyperscaler APIs."""
        now = datetime.now(timezone.utc)
        sync_run = InventorySyncRun(
            provider=provider.upper(),
            discovery_mode="LIVE_CLOUD",
            status="RUNNING",
            source_identifier=f"{provider.lower()}_api_discovery",
            started_at=now,
        )
        db.add(sync_run)
        db.commit()
        db.refresh(sync_run)

        discovery_res = InventoryDiscoveryService.discover_live(
            provider=provider,
            regions=regions,
            resource_types=resource_types,
        )

        recon_result = InventoryReconciliationEngine.reconcile(
            db=db,
            discovery_result=discovery_res,
            sync_run_id=sync_run.run_id,
        )

        quality_rep = None
        if evaluate_quality and len(discovery_res.resources) > 0:
            quality_rep = InventoryQualityEvaluator.evaluate(
                db=db,
                provider=provider,
                sync_run_id=sync_run.run_id,
                persist=True,
            )

        db.refresh(sync_run)
        return {
            "sync_run_id": str(sync_run.run_id),
            "status": sync_run.status,
            "provider": sync_run.provider,
            "total_discovered": recon_result["total_discovered"],
            "new_resources": recon_result["new_resources"],
            "updated_resources": recon_result["updated_resources"],
            "stale_resources": recon_result["stale_resources"],
            "relationships_reconciled": recon_result["relationships_reconciled"],
            "quality_score": float(quality_rep.completeness_score) if quality_rep else 100.0,
            "errors": recon_result["errors"],
        }

    @classmethod
    def list_resources(
        cls,
        db: Session,
        provider: Optional[str] = None,
        service_category: Optional[str] = None,
        environment: Optional[str] = None,
        status: Optional[str] = None,
        owner: Optional[str] = None,
        discovery_status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Lists inventory resources with filtering and pagination."""
        query = db.query(CloudResource)

        if provider:
            query = query.filter(CloudResource.provider == provider.upper())
        if service_category:
            query = query.filter(CloudResource.service_category == service_category.upper())
        if environment:
            query = query.filter(CloudResource.environment == environment.lower())
        if status:
            query = query.filter(CloudResource.status == status.lower())
        if owner:
            query = query.filter(CloudResource.owner.ilike(f"%{owner}%"))
        if discovery_status:
            query = query.filter(CloudResource.discovery_status == discovery_status.upper())

        total = query.count()
        resources = query.order_by(CloudResource.monthly_cost.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "items": resources,
            "limit": limit,
            "offset": offset,
        }

    @classmethod
    def get_resource_detail(cls, db: Session, resource_id: str) -> Optional[CloudResource]:
        """Fetches full inventory details for a single resource."""
        return db.query(CloudResource).filter(CloudResource.resource_id == resource_id).first()

    @classmethod
    def get_resource_relationships(
        cls,
        db: Session,
        resource_id: str,
    ) -> List[ResourceRelationship]:
        """Fetches all inbound and outbound topological relationships for a resource."""
        return (
            db.query(ResourceRelationship)
            .filter(
                (ResourceRelationship.source_resource_id == resource_id)
                | (ResourceRelationship.target_resource_id == resource_id)
            )
            .all()
        )

    @classmethod
    def get_inventory_summary(cls, db: Session) -> Dict[str, Any]:
        """Aggregates multi-cloud inventory count, monthly expenditure, and status metrics."""
        total_resources = db.query(func.count(CloudResource.resource_id)).scalar() or 0
        total_cost = db.query(func.sum(CloudResource.monthly_cost)).scalar() or Decimal("0.0000")

        # Provider breakdown
        prov_rows = (
            db.query(
                CloudResource.provider,
                func.count(CloudResource.resource_id).label("count"),
                func.sum(CloudResource.monthly_cost).label("cost"),
            )
            .group_by(CloudResource.provider)
            .all()
        )
        by_provider = {
            row.provider: {
                "count": row.count,
                "cost": Decimal(str(row.cost or "0.0000")),
            }
            for row in prov_rows
        }

        # Category breakdown
        cat_rows = (
            db.query(
                CloudResource.service_category,
                func.count(CloudResource.resource_id).label("count"),
                func.sum(CloudResource.monthly_cost).label("cost"),
            )
            .group_by(CloudResource.service_category)
            .all()
        )
        by_category = {
            row.service_category: {
                "count": row.count,
                "cost": Decimal(str(row.cost or "0.0000")),
            }
            for row in cat_rows
        }

        # Status breakdown
        status_rows = (
            db.query(
                CloudResource.status,
                func.count(CloudResource.resource_id).label("count"),
            )
            .group_by(CloudResource.status)
            .all()
        )
        by_status = {row.status: row.count for row in status_rows}

        # Environment breakdown
        env_rows = (
            db.query(
                CloudResource.environment,
                func.count(CloudResource.resource_id).label("count"),
            )
            .group_by(CloudResource.environment)
            .all()
        )
        by_environment = {row.environment: row.count for row in env_rows}

        # Average tag quality
        avg_tag_score = db.query(func.avg(CloudResource.tag_quality_score)).scalar() or Decimal("0.00")

        # Stale resources count
        stale_count = (
            db.query(func.count(CloudResource.resource_id))
            .filter(CloudResource.discovery_status == "STALE")
            .scalar()
            or 0
        )

        return {
            "total_resources": total_resources,
            "total_monthly_cost": Decimal(str(total_cost)),
            "by_provider": by_provider,
            "by_category": by_category,
            "by_status": by_status,
            "by_environment": by_environment,
            "average_tag_quality_score": Decimal(str(avg_tag_score)).quantize(Decimal("0.01")),
            "stale_resources_count": stale_count,
        }
