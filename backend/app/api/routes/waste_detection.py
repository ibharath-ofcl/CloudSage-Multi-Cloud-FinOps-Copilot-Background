"""
CloudSage Multi-Cloud Waste Detection REST API Endpoints.
FastAPI router providing 13 endpoints for executing waste detection runs,
querying findings with multi-faceted filtering, human-in-the-loop review actions,
telemetry proof inspection, and executive financial summaries.
Strictly advisory and non-destructive.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.database import get_sync_db
from backend.app.core.enums import Severity, WasteStatus, WasteType
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection, WasteDetectionRun
from backend.app.waste_detection.engine import WasteDetectionEngine
from backend.app.waste_detection.registry import DetectorRegistry
from backend.app.waste_detection.schemas import (
    DetectorInfoResponse,
    FindingStatusUpdateRequest,
    WasteDetectionRunRequest,
    WasteDetectionRunResponse,
    WasteFindingListResponse,
    WasteFindingResponse,
    WasteSummaryResponse,
)

router = APIRouter(prefix="/waste-detection", tags=["Waste Detection Engine"])


@router.post("/run", response_model=WasteDetectionRunResponse, status_code=status.HTTP_200_OK)
def run_waste_detection(
    request: WasteDetectionRunRequest,
    db: Session = Depends(get_sync_db),
) -> WasteDetectionRunResponse:
    """
    Triggers an evidence-based multi-cloud waste detection run across inventoried resources.
    Evaluates resources against registered waste detectors, updates or creates findings,
    and returns audit execution metrics.
    """
    run = WasteDetectionEngine.execute_detection_run(
        db=db,
        provider=request.provider,
        account_id=request.account_id,
        detectors=request.detectors,
        categories=request.categories,
        lookback_days=request.lookback_days,
    )
    return WasteDetectionRunResponse.model_validate(run)


@router.get("/findings", response_model=WasteFindingListResponse)
def get_findings(
    provider: Optional[str] = Query(None, description="Filter by cloud provider: AWS, AZURE, GCP"),
    account_id: Optional[str] = Query(None, description="Filter by account/subscription/project ID"),
    waste_type: Optional[str] = Query(None, description="Filter by waste category/type"),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL"),
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, OPEN, ACKNOWLEDGED, SNOOZED, DISMISSED, RESOLVED, REOPENED"),
    min_savings: Optional[Decimal] = Query(None, description="Filter by minimum estimated monthly savings"),
    owner: Optional[str] = Query(None, description="Filter by resource owner tag"),
    environment: Optional[str] = Query(None, description="Filter by environment: prod, dev, staging, test"),
    limit: int = Query(50, ge=1, le=500, description="Page size limit"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_sync_db),
) -> WasteFindingListResponse:
    """
    Lists identified cloud waste findings with multi-dimensional filtering,
    conservative savings estimation, and pagination.
    """
    result = WasteDetectionEngine.list_findings(
        db=db,
        provider=provider,
        account_id=account_id,
        waste_type=waste_type,
        severity=severity,
        status=status,
        min_savings=min_savings,
        owner=owner,
        environment=environment,
        limit=limit,
        offset=offset,
    )
    return WasteFindingListResponse(
        total=result["total"],
        items=[WasteFindingResponse.model_validate(item) for item in result["items"]],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get("/findings/{finding_id}", response_model=WasteFindingResponse)
def get_finding_detail(
    finding_id: uuid.UUID,
    db: Session = Depends(get_sync_db),
) -> WasteFindingResponse:
    """
    Retrieves full details for a single waste finding including financial impact,
    confidence score, and evidence summary.
    """
    finding = db.query(WasteDetection).filter(WasteDetection.id == finding_id).first()
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Waste finding with id '{finding_id}' not found",
        )
    return WasteFindingResponse.model_validate(finding)


@router.get("/summary", response_model=WasteSummaryResponse)
def get_waste_summary(
    db: Session = Depends(get_sync_db),
) -> WasteSummaryResponse:
    """
    Returns executive KPI metrics across all active and open waste findings,
    including total potential monthly savings and breakdowns by provider, category, and severity.
    """
    summary = WasteDetectionEngine.get_summary(db)
    return WasteSummaryResponse(**summary)


@router.get("/categories")
def get_waste_by_category(
    db: Session = Depends(get_sync_db),
) -> Dict[str, Any]:
    """
    Returns waste finding counts, total estimated monthly savings, and average confidence
    aggregated across each waste category.
    """
    active_statuses = ["ACTIVE", "OPEN", "REOPENED", "ACKNOWLEDGED"]
    rows = (
        db.query(
            WasteDetection.waste_type,
            func.count(WasteDetection.id).label("count"),
            func.sum(WasteDetection.estimated_monthly_waste).label("total_savings"),
            func.avg(WasteDetection.confidence_score).label("avg_confidence"),
        )
        .filter(WasteDetection.status.in_(active_statuses))
        .group_by(WasteDetection.waste_type)
        .order_by(func.sum(WasteDetection.estimated_monthly_waste).desc())
        .all()
    )

    categories = [
        {
            "waste_category": row[0],
            "count": row[1],
            "total_monthly_savings": Decimal(str(row[2] or "0.0000")),
            "average_confidence": Decimal(str(round(row[3] or 0.0, 4))),
        }
        for row in rows
    ]

    return {
        "total_categories": len(categories),
        "categories": categories,
    }


@router.get("/by-provider")
def get_waste_by_provider(
    db: Session = Depends(get_sync_db),
) -> Dict[str, Any]:
    """
    Returns multi-cloud waste distribution and savings potential broken down by cloud provider (AWS, Azure, GCP).
    """
    active_statuses = ["ACTIVE", "OPEN", "REOPENED", "ACKNOWLEDGED"]
    rows = (
        db.query(
            WasteDetection.provider,
            func.count(WasteDetection.id).label("count"),
            func.sum(WasteDetection.estimated_monthly_waste).label("total_savings"),
        )
        .filter(WasteDetection.status.in_(active_statuses))
        .group_by(WasteDetection.provider)
        .order_by(func.sum(WasteDetection.estimated_monthly_waste).desc())
        .all()
    )

    providers = [
        {
            "provider": row[0],
            "findings_count": row[1],
            "total_monthly_savings": Decimal(str(row[2] or "0.0000")),
        }
        for row in rows
    ]

    return {
        "providers": providers,
    }


@router.get("/by-account")
def get_waste_by_account(
    db: Session = Depends(get_sync_db),
) -> Dict[str, Any]:
    """
    Returns waste finding counts and total savings aggregated by cloud account, subscription, or project.
    """
    active_statuses = ["ACTIVE", "OPEN", "REOPENED", "ACKNOWLEDGED"]
    rows = (
        db.query(
            WasteDetection.provider,
            WasteDetection.account_id,
            func.count(WasteDetection.id).label("count"),
            func.sum(WasteDetection.estimated_monthly_waste).label("total_savings"),
        )
        .filter(WasteDetection.status.in_(active_statuses))
        .group_by(WasteDetection.provider, WasteDetection.account_id)
        .order_by(func.sum(WasteDetection.estimated_monthly_waste).desc())
        .all()
    )

    accounts = [
        {
            "provider": row[0],
            "account_id": row[1] or "UNKNOWN",
            "findings_count": row[2],
            "total_monthly_savings": Decimal(str(row[3] or "0.0000")),
        }
        for row in rows
    ]

    return {
        "total_accounts": len(accounts),
        "accounts": accounts,
    }


@router.get("/runs", response_model=List[WasteDetectionRunResponse])
def list_detection_runs(
    limit: int = Query(50, ge=1, le=200, description="Number of runs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_sync_db),
) -> List[WasteDetectionRunResponse]:
    """
    Lists historical waste detection runs with execution status and audit statistics.
    """
    runs = (
        db.query(WasteDetectionRun)
        .order_by(WasteDetectionRun.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [WasteDetectionRunResponse.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=WasteDetectionRunResponse)
def get_detection_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_sync_db),
) -> WasteDetectionRunResponse:
    """
    Retrieves full execution audit details for a specific waste detection run.
    """
    run = db.query(WasteDetectionRun).filter(WasteDetectionRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection run with id '{run_id}' not found",
        )
    return WasteDetectionRunResponse.model_validate(run)


@router.get("/savings-summary")
def get_savings_summary(
    db: Session = Depends(get_sync_db),
) -> Dict[str, Any]:
    """
    Detailed savings intelligence including annualized projections, top savings opportunities,
    and provider/category distributions calculated with Decimal precision.
    """
    active_statuses = ["ACTIVE", "OPEN", "REOPENED", "ACKNOWLEDGED"]
    base_query = db.query(WasteDetection).filter(WasteDetection.status.in_(active_statuses))

    total_monthly = base_query.with_entities(func.sum(WasteDetection.estimated_monthly_waste)).scalar() or Decimal("0.0000")
    total_monthly_dec = Decimal(str(total_monthly))
    total_annual_dec = total_monthly_dec * Decimal("12")

    # Top 5 findings by savings
    top_findings = (
        base_query.order_by(WasteDetection.estimated_monthly_waste.desc())
        .limit(5)
        .all()
    )

    top_items = [
        {
            "id": f.id,
            "resource_id": f.resource_id,
            "provider": f.provider,
            "waste_type": f.waste_type,
            "finding_title": f.finding_title,
            "severity": f.severity,
            "estimated_monthly_savings": f.estimated_monthly_savings,
            "confidence_score": f.confidence_score,
        }
        for f in top_findings
    ]

    summary = WasteDetectionEngine.get_summary(db)

    return {
        "currency": "USD",
        "total_estimated_monthly_savings": total_monthly_dec,
        "total_estimated_annual_savings": total_annual_dec,
        "total_active_findings": summary["total_open_findings"],
        "savings_by_provider": summary["savings_by_provider"],
        "savings_by_category": summary["savings_by_category"],
        "findings_by_severity": summary["findings_by_severity"],
        "top_savings_opportunities": top_items,
    }


@router.get("/detectors", response_model=List[DetectorInfoResponse])
def list_detectors() -> List[DetectorInfoResponse]:
    """
    Returns catalog of registered waste detectors, supported cloud providers,
    and default operational threshold parameters.
    """
    detectors = DetectorRegistry.list_detectors()
    return [
        DetectorInfoResponse(
            detector_id=d.detector_id,
            detector_version=d.detector_version,
            waste_category=d.waste_category.value,
            description=d.description,
            supported_providers=d.supported_providers,
            default_thresholds=d.default_thresholds,
        )
        for d in detectors
    ]


@router.patch("/findings/{finding_id}/status", response_model=WasteFindingResponse)
def update_finding_status(
    finding_id: uuid.UUID,
    payload: FindingStatusUpdateRequest,
    db: Session = Depends(get_sync_db),
) -> WasteFindingResponse:
    """
    Human-in-the-loop review action: Acknowledge, Dismiss, Resolve, or Snooze a finding.
    Enforces valid lifecycle state transitions and records reviewer rationale.
    """
    valid_statuses = {"ACKNOWLEDGED", "DISMISSED", "RESOLVED", "SNOOZED", "ACTIVE", "OPEN"}
    status_upper = payload.status.upper().strip()
    if status_upper not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{payload.status}'. Permitted values: {', '.join(sorted(valid_statuses))}",
        )

    updated = WasteDetectionEngine.update_finding_status(
        db=db,
        finding_id=finding_id,
        new_status=status_upper,
        reason=payload.reason,
        user=payload.user,
        snooze_days=payload.snooze_days,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Waste finding with id '{finding_id}' not found",
        )

    return WasteFindingResponse.model_validate(updated)


@router.get("/findings/{finding_id}/evidence")
def get_finding_evidence(
    finding_id: uuid.UUID,
    db: Session = Depends(get_sync_db),
) -> Dict[str, Any]:
    """
    Retrieves the complete telemetry proof and observation evidence backing a waste finding.
    Used for human review, auditability, and validation before taking advisory action.
    """
    finding = db.query(WasteDetection).filter(WasteDetection.id == finding_id).first()
    if not finding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Waste finding with id '{finding_id}' not found",
        )

    return {
        "finding_id": finding.id,
        "resource_id": finding.resource_id,
        "provider": finding.provider,
        "waste_type": finding.waste_type,
        "detector_id": finding.detector_id,
        "detector_version": finding.detector_version,
        "finding_title": finding.finding_title,
        "explanation": finding.explanation,
        "confidence_score": finding.confidence_score,
        "observation_window_days": finding.observation_window_days,
        "data_quality_status": finding.data_quality_status,
        "requires_human_review": finding.requires_human_review,
        "telemetry_proof": finding.telemetry_proof,
        "first_detected_at": finding.first_detected_at,
        "last_evaluated_at": finding.last_evaluated_at,
    }
