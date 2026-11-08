"""
CloudSage Multi-Cloud Resource Inventory & Intelligence API Endpoints.
FastAPI router providing 13 endpoints for resource import, live synchronization,
inventory querying, topological relationships, quality assessments, and cost correlation.
"""

import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_sync_db
from backend.app.inventory.correlation import BillingCorrelationEngine
from backend.app.inventory.quality import InventoryQualityEvaluator
from backend.app.inventory.schemas import (
    BillingCorrelationResponse,
    CloudResourceDetailResponse,
    CloudResourceListResponse,
    CloudResourceResponse,
    InventoryCoverageResponse,
    InventoryImportResponse,
    InventoryQualityReportResponse,
    InventorySummaryResponse,
    InventorySyncRunResponse,
    LiveDiscoveryRequest,
    ResourceRelationshipResponse,
)
from backend.app.inventory.service import InventoryService
from backend.app.models.inventory import InventoryQualityReport, InventorySyncRun, ResourceRelationship
from backend.app.models.resource import CloudResource

from backend.app.services.correlation import CorrelationService
from backend.app.services.telemetry import TelemetryService

router = APIRouter(prefix="/inventory", tags=["Resource Inventory & Intelligence"])

MAX_INVENTORY_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_INVENTORY_EXTENSIONS = {".json", ".jsonl", ".csv"}


def _save_and_process_upload(
    file: UploadFile,
    provider: str,
    db: Session,
) -> Dict[str, Any]:
    """Helper to safely stream and process uploaded inventory files."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No inventory file provided or filename is missing",
        )

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_INVENTORY_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Permitted extensions: {', '.join(ALLOWED_INVENTORY_EXTENSIONS)}",
        )

    temp_dir = tempfile.mkdtemp(prefix="cloudsage_inv_")
    safe_filename = os.path.basename(file.filename)
    temp_path = os.path.join(temp_dir, safe_filename)

    try:
        size = 0
        with open(temp_path, "wb") as f_out:
            while chunk := file.file.read(65536):
                size += len(chunk)
                if size > MAX_INVENTORY_FILE_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Uploaded file exceeds {MAX_INVENTORY_FILE_SIZE // (1024 * 1024)} MB limit",
                    )
                f_out.write(chunk)

        result = InventoryService.import_inventory_file(
            db=db,
            provider=provider,
            stream_or_path=temp_path,
            source_identifier=safe_filename,
            evaluate_quality=True,
        )
        return result
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


# 1. POST /api/v1/inventory/import/aws
@router.post("/import/aws", response_model=InventoryImportResponse, summary="Import AWS Inventory Export")
def import_aws_inventory(
    file: UploadFile = File(...),
    db: Session = Depends(get_sync_db),
):
    """Imports AWS resource inventory export file (EC2, EBS, S3, RDS, Lambda, Snapshots)."""
    return _save_and_process_upload(file=file, provider="AWS", db=db)


# 2. POST /api/v1/inventory/import/azure
@router.post("/import/azure", response_model=InventoryImportResponse, summary="Import Azure Inventory Export")
def import_azure_inventory(
    file: UploadFile = File(...),
    db: Session = Depends(get_sync_db),
):
    """Imports Azure resource inventory export file (VMs, Disks, Storage Accounts, SQL, VNETs)."""
    return _save_and_process_upload(file=file, provider="AZURE", db=db)


# 3. POST /api/v1/inventory/import/gcp
@router.post("/import/gcp", response_model=InventoryImportResponse, summary="Import GCP Inventory Export")
def import_gcp_inventory(
    file: UploadFile = File(...),
    db: Session = Depends(get_sync_db),
):
    """Imports GCP Cloud Asset Inventory export file (GCE, Disks, Cloud Storage, SQL, VPCs)."""
    return _save_and_process_upload(file=file, provider="GCP", db=db)


# 4. POST /api/v1/inventory/sync
@router.post("/sync", response_model=InventoryImportResponse, summary="Trigger Live Read-Only Cloud Discovery")
def sync_live_inventory(
    request: LiveDiscoveryRequest,
    db: Session = Depends(get_sync_db),
):
    """Triggers Mode B live discovery query against cloud provider APIs using read-only credentials."""
    return InventoryService.run_live_discovery(
        db=db,
        provider=request.provider,
        regions=request.regions,
        resource_types=request.resource_types,
        evaluate_quality=True,
    )


# 5. GET /api/v1/inventory/resources
@router.get("/resources", response_model=CloudResourceListResponse, summary="List Multi-Cloud Inventory Resources")
def list_resources(
    provider: Optional[str] = Query(None, description="AWS, AZURE, or GCP"),
    service_category: Optional[str] = Query(None, description="COMPUTE, STORAGE, DATABASE, etc."),
    environment: Optional[str] = Query(None, description="production, staging, development, test"),
    status: Optional[str] = Query(None, description="active, stopped, terminated, deleted, unknown"),
    owner: Optional[str] = Query(None, description="Owner email or identifier filter"),
    discovery_status: Optional[str] = Query(None, description="CONFIRMED, BILLING_ONLY, STALE"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
):
    """Retrieves paginated multi-cloud inventory resources with comprehensive filters."""
    result = InventoryService.list_resources(
        db=db,
        provider=provider,
        service_category=service_category,
        environment=environment,
        status=status,
        owner=owner,
        discovery_status=discovery_status,
        limit=limit,
        offset=offset,
    )
    return result


# 8. GET /api/v1/inventory/summary
@router.get("/summary", summary="Retrieve High-Level Inventory Summary")
def get_inventory_summary(
    db: Session = Depends(get_sync_db),
):
    """Returns aggregated summary metrics across providers, categories, statuses, and monthly cost."""
    return InventoryService.get_inventory_summary(db=db)


# 9. GET /api/v1/inventory/sync-runs
@router.get("/sync-runs", response_model=List[InventorySyncRunResponse], summary="List Inventory Synchronization Runs")
def list_sync_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
):
    """Lists audit records of historical inventory discovery and synchronization runs."""
    runs = (
        db.query(InventorySyncRun)
        .order_by(InventorySyncRun.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return runs


# 10. GET /api/v1/inventory/sync-runs/{run_id}
@router.get("/sync-runs/{run_id}", response_model=InventorySyncRunResponse, summary="Get Inventory Sync Run Details")
def get_sync_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_sync_db),
):
    """Retrieves specific inventory sync run audit details by UUID."""
    run = db.query(InventorySyncRun).filter(InventorySyncRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory sync run '{run_id}' not found",
        )
    return run


# 11. GET /api/v1/inventory/quality-report
@router.get("/quality-report", response_model=InventoryQualityReportResponse, summary="Get Inventory Quality Report")
def get_quality_report(
    provider: Optional[str] = Query(None, description="AWS, AZURE, GCP or ALL"),
    run_eval: bool = Query(False, description="Whether to trigger an immediate fresh evaluation"),
    db: Session = Depends(get_sync_db),
):
    """Retrieves latest inventory quality assessment or executes on-demand audit."""
    if run_eval:
        return InventoryQualityEvaluator.evaluate(db=db, provider=provider, persist=True)

    query = db.query(InventoryQualityReport)
    if provider:
        query = query.filter(InventoryQualityReport.provider == provider.upper())
    report = query.order_by(InventoryQualityReport.created_at.desc()).first()

    if not report:
        report = InventoryQualityEvaluator.evaluate(db=db, provider=provider, persist=True)
    return report


# 12. GET /api/v1/inventory/coverage
@router.get("/coverage", summary="Get Cost & Resource Coverage Metrics")
def get_inventory_coverage(
    provider: Optional[str] = Query(None, description="AWS, AZURE, or GCP"),
    db: Session = Depends(get_sync_db),
):
    """Evaluates cost reconciliation coverage comparing billing records to physical inventory."""
    return BillingCorrelationEngine.get_coverage_summary(db=db, provider=provider)


# 13. GET /api/v1/inventory/cost-correlation
@router.get("/cost-correlation", response_model=BillingCorrelationResponse, summary="Get Resource Financial Correlation")
def get_cost_correlation(
    resource_id: str = Query(..., description="Globally unique cloud resource ARN or URI"),
    db: Session = Depends(get_sync_db),
):
    """Correlates a specific cloud resource with its associated billing line items and total expenditure."""
    res = db.query(CloudResource).filter(CloudResource.resource_id == resource_id).first()
    corr = BillingCorrelationEngine.correlate_resource(db=db, resource_id=resource_id)
    if not corr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No correlation found for resource '{resource_id}'",
        )

    return BillingCorrelationResponse(
        resource_id=resource_id,
        provider=res.provider if res else "UNKNOWN",
        account_id=res.account_id if res else "UNKNOWN",
        resource_name=res.resource_name if res else resource_id,
        service_name=res.service_name if res else "Unknown",
        resource_type=res.resource_type if res else "Unknown",
        inventory_status=res.status if res else "UNKNOWN",
        discovery_status=res.discovery_status if res else "BILLING_ONLY",
        correlation_status=corr["correlation_status"],
        total_billed_cost=corr["total_billed_cost"],
        total_effective_cost=corr["total_effective_cost"],
        currency="USD",
        billing_record_count=corr["billing_record_count"],
        earliest_billing_date=corr["first_billed_at"],
        latest_billing_date=corr["last_billed_at"],
    )


# 7. GET /api/v1/inventory/resources/{resource_id}/relationships
# MUST be declared BEFORE /resources/{resource_id:path}
@router.get(
    "/resources/{resource_id:path}/relationships",
    response_model=List[ResourceRelationshipResponse],
    summary="Get Resource Topology Relationships",
)
def get_resource_relationships(
    resource_id: str,
    db: Session = Depends(get_sync_db),
):
    """Retrieves directional relationships (ATTACHED_TO, SNAPSHOT_OF) connected to a resource."""
    return InventoryService.get_resource_relationships(db=db, resource_id=resource_id)


# Telemetry and Correlations MUST be declared BEFORE /resources/{resource_id:path}
@router.get("/resources/{resource_id:path}/telemetry")
def get_resource_telemetry_endpoint(
    resource_id: str,
    days: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_sync_db),
):
    """
    Retrieves time-series metrics (CPU, Memory, Network, Disk) for a specific cloud resource.
    Never fabricates telemetry; returns explicit empty status if unmonitored.
    """
    return TelemetryService.get_resource_telemetry(db, resource_id=resource_id, days=days)


@router.get("/resources/{resource_id:path}/correlations")
def get_resource_correlations_endpoint(
    resource_id: str,
    db: Session = Depends(get_sync_db),
):
    """
    Retrieves unified entity correlation view linking the cloud resource to waste findings,
    recommendations, anomalies, billing records, and telemetry with anti-double-counting guarantees.
    """
    return CorrelationService.get_resource_correlations(db, resource_id=resource_id)


# 6. GET /api/v1/inventory/resources/{resource_id}
@router.get(
    "/resources/{resource_id:path}",
    response_model=CloudResourceDetailResponse,
    summary="Get Cloud Resource Details",
)
def get_resource_detail(
    resource_id: str,
    db: Session = Depends(get_sync_db),
):
    """Retrieves complete inventory detail, topology relationships, and financial metrics for a resource."""
    resource = InventoryService.get_resource_detail(db=db, resource_id=resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cloud resource '{resource_id}' not found in inventory",
        )

    relationships = InventoryService.get_resource_relationships(db=db, resource_id=resource_id)
    corr = BillingCorrelationEngine.correlate_resource(db=db, resource_id=resource_id)

    return CloudResourceDetailResponse(
        resource_id=resource.resource_id,
        provider=resource.provider,
        account_id=resource.account_id,
        resource_name=resource.resource_name,
        service_category=resource.service_category,
        service_name=resource.service_name,
        resource_type=resource.resource_type,
        region=resource.region,
        zone=resource.zone,
        status=resource.status,
        tags=resource.tags or {},
        raw_tags=resource.raw_tags or {},
        owner=resource.owner,
        department=resource.department,
        project=resource.project,
        environment=resource.environment,
        cost_center=resource.cost_center,
        tag_quality_score=resource.tag_quality_score,
        monthly_cost=resource.monthly_cost,
        resource_created_at=resource.resource_created_at,
        first_discovered_at=resource.first_discovered_at,
        last_seen_at=resource.last_seen_at,
        last_inventory_sync_at=resource.last_inventory_sync_at,
        discovery_source=resource.discovery_source,
        discovery_status=resource.discovery_status,
        resource_metadata=resource.resource_metadata or {},
        metadata_version=resource.metadata_version,
        relationships=relationships,
        total_billed_cost=corr["total_billed_cost"] if corr else Decimal("0.0000"),
        billing_records_count=corr["billing_record_count"] if corr else 0,
        latest_billing_period=corr["last_billed_at"] if corr else None,
    )

