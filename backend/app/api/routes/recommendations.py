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
)
from backend.app.recommendations.engine import RecommendationEngine, get_recommendation_engine
from backend.app.recommendations.lifecycle import (
    InvalidStateTransitionError,
    RejectionReasonRequiredError,
    transition_recommendation_status,
)
from backend.app.recommendations.savings import calculate_roi, quantize_currency
from backend.app.schemas.recommendation import (
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
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_sync_db),
):
    """Lists optimization recommendations with rich filtering, search, and pagination."""
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
    if search:
        s = f"%{search}%"
        query = query.filter(
            or_(
                Recommendation.title.ilike(s),
                Recommendation.description.ilike(s),
                Recommendation.resource_id.ilike(s),
            )
        )

    query = query.order_by(
        Recommendation.priority_score.desc(),
        Recommendation.estimated_monthly_savings.desc(),
    )
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
