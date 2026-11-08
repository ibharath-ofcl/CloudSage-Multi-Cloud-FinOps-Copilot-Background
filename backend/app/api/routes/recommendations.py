"""
CloudSage Recommendation REST API Endpoints.
Provides 16 enterprise endpoints for recommendation runs, lifecycle transitions,
evidence inspection, savings projections, filtering, and reporting.
"""

import csv
from datetime import datetime, timezone
import io
import json
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.app.core.database import get_sync_db
from backend.app.core.enums import CloudProvider, Priority, RecommendationAction, RecommendationStatus, RiskLevel
from backend.app.models.recommendation import (
    Recommendation,
    RecommendationEvidence,
    RecommendationHistory,
    RecommendationRun,
    RecommendationSavingsOverride,
)
from backend.app.recommendations.engine import RecommendationEngine, get_recommendation_engine
from backend.app.recommendations.lifecycle import (
    DualCustodyViolationError,
    InvalidStateTransitionError,
    RejectionReasonRequiredError,
    batch_transition_recommendations,
    propose_savings_override,
    review_savings_override,
    transition_recommendation_status,
)
from backend.app.recommendations.playbooks import RemediationPlaybookGenerator
from backend.app.recommendations.savings import calculate_roi, quantize_currency
from backend.app.services.correlation import CorrelationService
from backend.app.services.telemetry import TelemetryService
from backend.app.schemas.recommendation import (
    BatchRecommendationReviewRequest,
    BatchRecommendationReviewResponse,
    FinancialImpactResponse,
    OwnerImpactResponse,
    RecommendationCategoryBreakdown,
    RecommendationDetailResponse,
    RecommendationEvidenceResponse,
    RecommendationFeedback,
    RecommendationHistoryResponse,
    RecommendationPriorityBreakdown,
    RecommendationResponse,
    RecommendationRunRequest,
    RecommendationRunResponse,
    RecommendationSavingsDetail,
    RecommendationStatusUpdate,
    RecommendationSummaryResponse,
    RemediationPlaybookResponse,
    SavingsOverrideApproveRequest,
    SavingsOverrideProposeRequest,
    SavingsOverrideResponse,
)

router = APIRouter(prefix="/recommendations", tags=["Advisory Recommendations"])


@router.post("/run", response_model=RecommendationRunResponse, status_code=status.HTTP_201_CREATED)
def trigger_recommendation_run(
    payload: RecommendationRunRequest,
    db: Session = Depends(get_sync_db),
):
    """Triggers an advisory recommendation generation run across cloud resources."""
    engine = get_recommendation_engine()
    run = engine.execute_run(
        db=db,
        provider=payload.provider,
        strategies=payload.strategies,
        account_id=payload.account_id,
        service_name=payload.service_name,
        scope=payload.scope or "FULL",
    )
    return run


@router.post("/batch", response_model=BatchRecommendationReviewResponse)
def batch_review_recommendations(
    payload: BatchRecommendationReviewRequest,
    db: Session = Depends(get_sync_db),
):
    """
    Executes batch human-in-the-loop review operations (Approve, Reject, Dismiss, Snooze, Endorse)
    across multiple recommendations with transaction isolation.
    """
    action_map = {
        "APPROVE": RecommendationStatus.APPROVED,
        "APPROVED": RecommendationStatus.APPROVED,
        "ACCEPT": RecommendationStatus.ACCEPTED,
        "ACCEPTED": RecommendationStatus.ACCEPTED,
        "REJECT": RecommendationStatus.REJECTED,
        "REJECTED": RecommendationStatus.REJECTED,
        "DISMISS": RecommendationStatus.DISMISSED,
        "DISMISSED": RecommendationStatus.DISMISSED,
        "SNOOZE": RecommendationStatus.SNOOZED,
        "SNOOZED": RecommendationStatus.SNOOZED,
        "ENDORSE": RecommendationStatus.ENDORSED,
        "ENDORSED": RecommendationStatus.ENDORSED,
    }

    target_status = action_map.get(payload.action.upper().strip())
    if not target_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported batch action '{payload.action}'. Permitted: {', '.join(sorted(action_map.keys()))}",
        )

    result = batch_transition_recommendations(
        db=db,
        recommendation_ids=payload.recommendation_ids,
        new_status=target_status,
        actor=payload.actor_email,
        reason=payload.reason,
        snooze_days=payload.snooze_days,
        assigned_to=payload.assigned_to,
        external_ticket_ref=payload.external_ticket_ref,
    )
    return result


@router.get("/summary", response_model=RecommendationSummaryResponse)
def get_recommendation_summary(
    db: Session = Depends(get_sync_db),
):
    """Retrieves executive multi-cloud summary KPIs for recommendations."""
    return RecommendationEngine.get_summary(db)


@router.get("/priorities", response_model=List[RecommendationPriorityBreakdown])
def get_priority_breakdown(
    db: Session = Depends(get_sync_db),
):
    """Returns recommendation counts and savings grouped by priority tier (P1-P4)."""
    rows = (
        db.query(
            Recommendation.priority,
            func.count(Recommendation.id).label("count"),
            func.sum(Recommendation.estimated_monthly_savings).label("monthly_savings"),
            func.sum(Recommendation.estimated_annual_savings).label("annual_savings"),
        )
        .group_by(Recommendation.priority)
        .all()
    )

    results = []
    for r in rows:
        results.append(
            RecommendationPriorityBreakdown(
                priority=r.priority,
                count=r.count,
                monthly_savings=quantize_currency(Decimal(str(r.monthly_savings or "0.0000"))),
                annual_savings=quantize_currency(Decimal(str(r.annual_savings or "0.0000"))),
            )
        )
    return results


@router.get("/categories", response_model=List[RecommendationCategoryBreakdown])
def get_category_breakdown(
    db: Session = Depends(get_sync_db),
):
    """Returns recommendation counts and savings grouped by action type / category."""
    rows = (
        db.query(
            Recommendation.action_type,
            func.count(Recommendation.id).label("count"),
            func.sum(Recommendation.estimated_monthly_savings).label("monthly_savings"),
            func.sum(Recommendation.estimated_annual_savings).label("annual_savings"),
        )
        .group_by(Recommendation.action_type)
        .all()
    )

    results = []
    for r in rows:
        results.append(
            RecommendationCategoryBreakdown(
                action_type=r.action_type,
                count=r.count,
                monthly_savings=quantize_currency(Decimal(str(r.monthly_savings or "0.0000"))),
                annual_savings=quantize_currency(Decimal(str(r.annual_savings or "0.0000"))),
            )
        )
    return results


@router.get("/runs", response_model=List[RecommendationRunResponse])
def list_recommendation_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
):
    """Lists recent recommendation generation runs."""
    runs = (
        db.query(RecommendationRun)
        .order_by(RecommendationRun.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return runs


@router.get("/runs/{run_id}", response_model=RecommendationRunResponse)
def get_recommendation_run(
    run_id: UUID,
    db: Session = Depends(get_sync_db),
):
    """Retrieves execution details for a specific recommendation run."""
    run = db.query(RecommendationRun).filter(RecommendationRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation run '{run_id}' not found.",
        )
    return run


@router.get("/financial-impact", response_model=FinancialImpactResponse)
def get_financial_impact(
    db: Session = Depends(get_sync_db),
):
    """Calculates realized vs unrealized savings and realization rates."""
    return RecommendationEngine.get_financial_impact(db)


@router.get("/owners", response_model=List[OwnerImpactResponse])
def get_owner_impact(
    db: Session = Depends(get_sync_db),
):
    """Groups savings and pending recommendations by resource owner tag."""
    recs = db.query(Recommendation).all()
    owner_map: Dict[str, Dict[str, Any]] = {}

    for r in recs:
        tags = r.tags or {}
        owner = tags.get("owner", "Unassigned")
        if owner not in owner_map:
            owner_map[owner] = {
                "owner": owner,
                "count": 0,
                "monthly": Decimal("0.0000"),
                "annual": Decimal("0.0000"),
                "pending": 0,
            }
        owner_map[owner]["count"] += 1
        owner_map[owner]["monthly"] += r.estimated_monthly_savings
        owner_map[owner]["annual"] += r.estimated_annual_savings
        if r.status in ("PROPOSED", "NEW", "UNDER_REVIEW"):
            owner_map[owner]["pending"] += 1

    return [
        OwnerImpactResponse(
            owner=v["owner"],
            recommendation_count=v["count"],
            total_monthly_savings=quantize_currency(v["monthly"]),
            total_annual_savings=quantize_currency(v["annual"]),
            pending_approval_count=v["pending"],
        )
        for v in sorted(owner_map.values(), key=lambda x: x["monthly"], reverse=True)
    ]


@router.get("/export")
def export_recommendations(
    export_format: str = Query("json", pattern="^(json|csv)$"),
    provider: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_sync_db),
):
    """Exports filtered recommendations in JSON or CSV format."""
    query = db.query(Recommendation)
    if provider and provider != "ALL":
        query = query.filter(Recommendation.provider == provider.upper())
    if status_filter:
        query = query.filter(Recommendation.status == status_filter.upper())

    recs = query.all()

    if export_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Provider", "AccountID", "ResourceID", "ActionType",
            "Priority", "RiskLevel", "Status", "MonthlySavings", "AnnualSavings",
            "Title", "CreatedAt",
        ])
        for r in recs:
            writer.writerow([
                str(r.id), r.provider, r.account_id or "", r.resource_id or "",
                r.action_type, r.priority, r.risk_level, r.status,
                str(r.estimated_monthly_savings), str(r.estimated_annual_savings),
                r.title, r.created_at.isoformat() if r.created_at else "",
            ])
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=recommendations.csv"},
        )

    # JSON export
    data = [
        {
            "id": str(r.id),
            "recommendation_key": r.recommendation_key,
            "provider": r.provider,
            "account_id": r.account_id,
            "resource_id": r.resource_id,
            "action_type": r.action_type,
            "priority": r.priority,
            "risk_level": r.risk_level,
            "status": r.status,
            "estimated_monthly_savings": str(r.estimated_monthly_savings),
            "estimated_annual_savings": str(r.estimated_annual_savings),
            "title": r.title,
            "description": r.description,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in recs
    ]
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=recommendations.json"},
    )


@router.get("", response_model=List[RecommendationResponse])
def list_recommendations(
    provider: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = None,
    risk_level: Optional[str] = None,
    action_type: Optional[str] = None,
    service_name: Optional[str] = None,
    assigned_to: Optional[str] = None,
    min_savings: Optional[Decimal] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("priority", description="Sort by: priority, savings, risk, confidence, created_at"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_sync_db),
):
    """Lists optimization recommendations with rich filtering, search, multi-factor sort, and pagination."""
    query = db.query(Recommendation)

    if provider and provider != "ALL":
        query = query.filter(Recommendation.provider == provider.upper())
    if status_filter:
        query = query.filter(Recommendation.status == status_filter.upper())
    if priority:
        query = query.filter(Recommendation.priority == priority.upper())
    if risk_level:
        query = query.filter(Recommendation.risk_level == risk_level.upper())
    if action_type:
        query = query.filter(Recommendation.action_type == action_type.upper())
    if service_name:
        query = query.filter(Recommendation.service_name == service_name)
    if assigned_to:
        query = query.filter(Recommendation.assigned_to.ilike(f"%{assigned_to}%"))
    if min_savings is not None:
        query = query.filter(Recommendation.estimated_monthly_savings >= min_savings)
    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                Recommendation.title.ilike(s),
                Recommendation.description.ilike(s),
                Recommendation.resource_id.ilike(s),
                Recommendation.assigned_to.ilike(s),
                Recommendation.external_ticket_ref.ilike(s),
            )
        )

    # Sorting
    is_asc = sort_order and sort_order.lower() == "asc"
    sort_field = (sort_by or "priority").lower()

    if sort_field == "savings":
        primary = Recommendation.estimated_monthly_savings.asc() if is_asc else Recommendation.estimated_monthly_savings.desc()
        query = query.order_by(primary, Recommendation.priority_score.desc())
    elif sort_field == "risk":
        primary = Recommendation.risk_score.asc() if is_asc else Recommendation.risk_score.desc()
        query = query.order_by(primary, Recommendation.estimated_monthly_savings.desc())
    elif sort_field == "confidence":
        primary = Recommendation.confidence_score.asc() if is_asc else Recommendation.confidence_score.desc()
        query = query.order_by(primary, Recommendation.estimated_monthly_savings.desc())
    elif sort_field == "created_at":
        primary = Recommendation.created_at.asc() if is_asc else Recommendation.created_at.desc()
        query = query.order_by(primary)
    else:  # default "priority"
        primary = Recommendation.priority_score.asc() if is_asc else Recommendation.priority_score.desc()
        secondary = Recommendation.estimated_monthly_savings.asc() if is_asc else Recommendation.estimated_monthly_savings.desc()
        query = query.order_by(primary, secondary)

    return query.offset(skip).limit(limit).all()


@router.get("/{rec_id}", response_model=RecommendationDetailResponse)
def get_recommendation_details(
    rec_id: UUID,
    db: Session = Depends(get_sync_db),
):
    """Retrieves single recommendation with full guidance, assumptions, and evidence."""
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{rec_id}' not found.",
        )
    return rec


@router.get("/{rec_id}/evidence", response_model=List[RecommendationEvidenceResponse])
def get_recommendation_evidence(
    rec_id: UUID,
    db: Session = Depends(get_sync_db),
):
    """Retrieves all supporting evidence artifacts for a recommendation."""
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{rec_id}' not found.",
        )
    return rec.evidence_items


@router.get("/{rec_id}/history", response_model=List[RecommendationHistoryResponse])
def get_recommendation_history(
    rec_id: UUID,
    db: Session = Depends(get_sync_db),
):
    """Retrieves lifecycle transition audit history for a recommendation."""
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{rec_id}' not found.",
        )
    return rec.history_items


@router.get("/{rec_id}/savings", response_model=RecommendationSavingsDetail)
def get_recommendation_savings(
    rec_id: UUID,
    db: Session = Depends(get_sync_db),
):
    """Calculates granular financial breakdown, ROI, and percentage savings."""
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{rec_id}' not found.",
        )

    current = rec.current_monthly_cost
    projected = rec.projected_monthly_cost
    monthly_savings = rec.estimated_monthly_savings
    annual_savings = rec.estimated_annual_savings

    pct = Decimal("0.00")
    if current > Decimal("0.0000"):
        pct = ((monthly_savings / current) * Decimal("100.0")).quantize(Decimal("0.01"))

    return RecommendationSavingsDetail(
        recommendation_id=rec.id,
        current_monthly_cost=quantize_currency(current),
        projected_monthly_cost=quantize_currency(projected),
        monthly_savings=quantize_currency(monthly_savings),
        annual_savings=quantize_currency(annual_savings),
        savings_percentage=pct,
        currency=rec.currency,
        calculation_breakdown=rec.savings_calculation or {},
    )


@router.patch("/{rec_id}/status", response_model=RecommendationResponse)
def update_recommendation_status(
    rec_id: UUID,
    payload: RecommendationStatusUpdate,
    db: Session = Depends(get_sync_db),
):
    """Updates the lifecycle status of a recommendation following state machine rules."""
    reason = payload.reason or payload.notes
    try:
        updated = transition_recommendation_status(
            db=db,
            recommendation_id=rec_id,
            new_status=payload.status,
            actor=payload.actor_email,
            reason=reason,
        )
        return updated
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RejectionReasonRequiredError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{rec_id}/feedback", response_model=RecommendationHistoryResponse)
def submit_recommendation_feedback(
    rec_id: UUID,
    payload: RecommendationFeedback,
    db: Session = Depends(get_sync_db),
):
    """Submits engineer feedback, rating, or endorsement for a recommendation."""
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{rec_id}' not found.",
        )

    now = datetime.now(timezone.utc)
    hist = RecommendationHistory(
        id=uuid.uuid4(),
        recommendation_id=rec.id,
        from_status=rec.status,
        to_status=rec.status,
        actor=payload.actor_email,
        action="FEEDBACK_SUBMITTED",
        notes=payload.feedback_text,
        details={"rating": payload.rating, "action_type": payload.action_type},
        created_at=now,
    )
    db.add(hist)
    db.commit()
    db.refresh(hist)
    return hist


@router.post("/{rec_id}/override", response_model=SavingsOverrideResponse, status_code=status.HTTP_201_CREATED)
def propose_override(
    rec_id: UUID,
    payload: SavingsOverrideProposeRequest,
    db: Session = Depends(get_sync_db),
):
    """Proposes a revised savings figure for an optimization recommendation."""
    try:
        override = propose_savings_override(
            db=db,
            recommendation_id=rec_id,
            proposed_monthly_savings=payload.proposed_monthly_savings,
            reason=payload.reason,
            proposed_by=payload.proposed_by,
        )
        return override
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{rec_id}/overrides", response_model=List[SavingsOverrideResponse])
def list_overrides(
    rec_id: UUID,
    db: Session = Depends(get_sync_db),
):
    """Lists all historical savings overrides and proposals for a recommendation."""
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{rec_id}' not found.",
        )
    return rec.savings_overrides


@router.post("/{rec_id}/override/{override_id}/approve", response_model=SavingsOverrideResponse)
def approve_override(
    rec_id: UUID,
    override_id: UUID,
    payload: SavingsOverrideApproveRequest,
    db: Session = Depends(get_sync_db),
):
    """Formally approves or rejects a proposed savings override with audit history."""
    try:
        reviewed = review_savings_override(
            db=db,
            override_id=override_id,
            approved_by=payload.approved_by,
            approve=payload.approved,
            rejection_reason=payload.rejection_reason,
            enforce_dual_custody=False,
        )
        return reviewed
    except DualCustodyViolationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{rec_id}/playbook", response_model=RemediationPlaybookResponse)
def generate_recommendation_playbook(
    rec_id: UUID,
    format: str = Query("markdown", description="Format: terraform, cloudformation, aws_cli, azure_cli, gcp_cli, bicep, markdown"),
    db: Session = Depends(get_sync_db),
):
    """
    Generates deterministic, production-grade Infrastructure-as-Code or CLI remediation playbooks.
    STRICTLY ADVISORY: CloudSage never executes mutations autonomously.
    """
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{rec_id}' not found.",
        )

    res_id = rec.resource_id or f"{rec.provider.lower()}-{rec.service_name or 'resource'}"
    playbook = RemediationPlaybookGenerator.generate_playbook(
        provider=rec.provider,
        action_type=rec.action_type,
        resource_id=res_id,
        resource_name=rec.resource_name,
        region=rec.region,
        account_id=rec.account_id,
        service_name=rec.service_name,
        estimated_monthly_savings=rec.estimated_monthly_savings,
        details=rec.implementation_guidance or {},
        playbook_format=format,
    )
    return playbook


@router.get("/{rec_id}/playbook/download")
def download_recommendation_playbook(
    rec_id: UUID,
    format: str = Query("markdown", description="Format: terraform, cloudformation, aws_cli, azure_cli, gcp_cli, bicep, markdown"),
    db: Session = Depends(get_sync_db),
):
    """Downloads the advisory remediation playbook file directly."""
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{rec_id}' not found.",
        )

    res_id = rec.resource_id or f"{rec.provider.lower()}-{rec.service_name or 'resource'}"
    playbook = RemediationPlaybookGenerator.generate_playbook(
        provider=rec.provider,
        action_type=rec.action_type,
        resource_id=res_id,
        resource_name=rec.resource_name,
        region=rec.region,
        account_id=rec.account_id,
        service_name=rec.service_name,
        estimated_monthly_savings=rec.estimated_monthly_savings,
        details=rec.implementation_guidance or {},
        playbook_format=format,
    )

    return Response(
        content=playbook["content"],
        media_type=playbook["mime_type"],
        headers={"Content-Disposition": f"attachment; filename={playbook['filename']}"},
    )


@router.get("/{rec_id}/telemetry")
def get_recommendation_telemetry(
    rec_id: UUID,
    days: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_sync_db),
):
    """
    Retrieves real time-series metrics (CPU, Memory, Network, Disk) for the target resource.
    Never fabricates telemetry; returns explicit empty status if unmonitored.
    """
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{rec_id}' not found.",
        )

    if not rec.resource_id:
        return {
            "resource_id": None,
            "has_telemetry": False,
            "reason": "NO_RESOURCE_ID",
            "message": "This is an account/service-level recommendation without a singular resource.",
            "metrics": {},
            "summary": {},
        }

    return TelemetryService.get_resource_telemetry(db, resource_id=rec.resource_id, days=days)


@router.get("/{rec_id}/correlations")
def get_recommendation_correlations(
    rec_id: UUID,
    db: Session = Depends(get_sync_db),
):
    """
    Retrieves unified entity correlation view linking resource, waste findings,
    anomalies, billing records, and telemetry with strict anti-double-counting guarantees.
    """
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recommendation '{rec_id}' not found.",
        )

    if not rec.resource_id:
        return {
            "resource_id": None,
            "recommendation_id": str(rec.id),
            "has_resource": False,
            "message": "Recommendation is not mapped to an individual cloud resource ARN.",
        }

    return CorrelationService.get_resource_correlations(db, resource_id=rec.resource_id)

