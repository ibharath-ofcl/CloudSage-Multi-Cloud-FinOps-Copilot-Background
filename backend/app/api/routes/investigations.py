"""
CloudSage Advanced Anomaly Investigation & Multi-Dimensional Root Cause Analysis Endpoints.
FastAPI router providing:
1. Investigation Case Management (CRUD, lifecycle state machine, assignments)
2. 10-Dimensional Cost Decomposition (Provider, Account, Region, Service, Resource ID, SKU, Environment, Owner, Cost Center, Billing Tags)
3. Pareto 80/20 Contribution Ranking
4. Usage vs. Price Growth Accounting Decomposition
5. Time-Series Historical Timeline & Moving Averages
6. Resource Topology & Telemetry Metrics
7. Cross-Signal Correlation (Waste, Recommendations, Alerts)
8. Collaboration Notes, Findings & Immutable Audit History
9. Direct Anomaly Investigation Links
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.alerts.security import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
)
from backend.app.core.database import get_sync_db
from backend.app.core.enums import (
    ConfidenceCategory,
    InvestigationPriority,
    InvestigationStatus,
)
from backend.app.investigation.service import (
    InvalidTransitionError,
    InvestigationService,
    MissingJustificationError,
)
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.investigation import (
    InvestigationCase,
    InvestigationEvidenceLink,
    InvestigationFinding,
    InvestigationHistory,
    InvestigationNote,
)
from backend.app.schemas.investigation import (
    AnomalyInvestigationSummaryResponse,
    ContributionRankingResponse,
    CrossSignalCorrelationResponse,
    InvestigationAssignRequest,
    InvestigationCaseCreate,
    InvestigationCaseDetailResponse,
    InvestigationCaseListResponse,
    InvestigationCaseResponse,
    InvestigationCaseUpdate,
    InvestigationEvidenceLinkResponse,
    InvestigationFindingCreate,
    InvestigationFindingResponse,
    InvestigationHistoryResponse,
    InvestigationNoteCreate,
    InvestigationNoteResponse,
    InvestigationStatsResponse,
    InvestigationTransitionRequest,
    MultiDimensionalAnalysisResponse,
    ResourceInvestigationResponse,
    TimelineAnalysisResponse,
    UsagePriceAnalysisResponse,
)


def get_current_principal(
    request: Request,
    db: Session = Depends(get_sync_db),
) -> AuthenticatedPrincipal:
    """FastAPI dependency resolving server-side authenticated principal."""
    return get_authenticated_principal(request, db)


router = APIRouter(tags=["Investigation Workspace & Root Cause Analysis"])


# ============================================================================
# 1. INVESTIGATION CASES MANAGEMENT & STATS
# ============================================================================

@router.get("/investigations/stats", response_model=InvestigationStatsResponse, status_code=status.HTTP_200_OK)
def get_investigation_stats(
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationStatsResponse:
    """Retrieves global KPI metrics for the investigation workspace."""
    service = InvestigationService(db)
    return service.get_stats()


@router.get("/investigations", response_model=InvestigationCaseListResponse, status_code=status.HTTP_200_OK)
def list_investigations(
    provider: Optional[str] = Query(None, description="Cloud provider (AWS, AZURE, GCP, ALL)"),
    status: Optional[str] = Query(None, description="Case lifecycle status"),
    priority: Optional[str] = Query(None, description="Priority tier: CRITICAL, HIGH, MEDIUM, LOW"),
    assigned_to: Optional[str] = Query(None, description="Assigned principal or 'unassigned'"),
    service_name: Optional[str] = Query(None, description="Service name filter"),
    search: Optional[str] = Query(None, description="Search by case number, title, service, or resource"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationCaseListResponse:
    """Lists investigation cases with multi-dimensional filtering and pagination."""
    service = InvestigationService(db)
    return service.list_cases(
        provider=provider,
        status=status,
        priority=priority,
        assigned_to=assigned_to,
        service_name=service_name,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("/investigations", response_model=InvestigationCaseDetailResponse, status_code=status.HTTP_201_CREATED)
def create_investigation(
    case_in: InvestigationCaseCreate,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationCaseDetailResponse:
    """Opens a new investigation case for a cost anomaly and initiates root-cause analysis."""
    service = InvestigationService(db)
    try:
        return service.create_case(case_in=case_in, actor=principal.email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/investigations/{investigation_id}", response_model=InvestigationCaseDetailResponse, status_code=status.HTTP_200_OK)
def get_investigation_detail(
    investigation_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationCaseDetailResponse:
    """Retrieves full investigation case details, findings, notes, evidence, and history."""
    service = InvestigationService(db)
    try:
        return service.get_case_detail(investigation_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/investigations/{investigation_id}", response_model=InvestigationCaseDetailResponse, status_code=status.HTTP_200_OK)
def update_investigation_case(
    investigation_id: UUID,
    case_update: InvestigationCaseUpdate,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationCaseDetailResponse:
    """Updates mutable metadata on an existing investigation case."""
    case = db.query(InvestigationCase).filter(InvestigationCase.id == investigation_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation case not found")

    if case_update.title is not None:
        case.title = case_update.title
    if case_update.priority is not None:
        case.priority = case_update.priority.upper()
    if case_update.assigned_to is not None:
        case.assigned_to = case_update.assigned_to
        case.assigned_at = datetime.now(timezone.utc)
    if case_update.root_cause_summary is not None:
        case.root_cause_summary = case_update.root_cause_summary
    if case_update.verified_root_cause is not None:
        case.verified_root_cause = case_update.verified_root_cause
    if case_update.suspected_category is not None:
        case.suspected_category = case_update.suspected_category
    if case_update.resolution_notes is not None:
        case.resolution_notes = case_update.resolution_notes

    case.updated_by = principal.email
    case.updated_at = datetime.now(timezone.utc)
    db.commit()

    service = InvestigationService(db)
    return service.get_case_detail(investigation_id)


# ============================================================================
# 2. LIFECYCLE & ASSIGNMENT WORKFLOWS
# ============================================================================

@router.post("/investigations/{investigation_id}/assign", response_model=InvestigationCaseDetailResponse, status_code=status.HTTP_200_OK)
def assign_investigation_case(
    investigation_id: UUID,
    assign_req: InvestigationAssignRequest,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationCaseDetailResponse:
    """Assigns an investigation case to a designated FinOps analyst or team owner."""
    service = InvestigationService(db)
    try:
        return service.assign_case(
            case_id=investigation_id,
            assigned_to=assign_req.assigned_to,
            actor=principal.email,
            notes=assign_req.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/investigations/{investigation_id}/transition", response_model=InvestigationCaseDetailResponse, status_code=status.HTTP_200_OK)
def transition_investigation_status(
    investigation_id: UUID,
    transition_req: InvestigationTransitionRequest,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationCaseDetailResponse:
    """Executes a formal lifecycle status transition with validation."""
    service = InvestigationService(db)
    try:
        return service.transition_status(
            case_id=investigation_id,
            target_status=transition_req.status,
            actor=principal.email,
            notes=transition_req.notes,
            verified_root_cause=transition_req.verified_root_cause,
        )
    except InvalidTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except MissingJustificationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/investigations/{investigation_id}/close", response_model=InvestigationCaseDetailResponse, status_code=status.HTTP_200_OK)
def close_investigation_case(
    investigation_id: UUID,
    notes: Optional[str] = Query(None, description="Optional closure justification"),
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationCaseDetailResponse:
    """Closes an investigation case."""
    service = InvestigationService(db)
    try:
        return service.transition_status(
            case_id=investigation_id,
            target_status=InvestigationStatus.CLOSED.value,
            actor=principal.email,
            notes=notes or "Investigation closed.",
        )
    except (InvalidTransitionError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/investigations/{investigation_id}/reopen", response_model=InvestigationCaseDetailResponse, status_code=status.HTTP_200_OK)
def reopen_investigation_case(
    investigation_id: UUID,
    notes: Optional[str] = Query(None, description="Optional reopening notes"),
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationCaseDetailResponse:
    """Reopens a resolved or closed investigation case."""
    service = InvestigationService(db)
    try:
        return service.transition_status(
            case_id=investigation_id,
            target_status=InvestigationStatus.INVESTIGATING.value,
            actor=principal.email,
            notes=notes or "Investigation reopened for further analysis.",
        )
    except (InvalidTransitionError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# 3. ANALYTICAL DRILL-DOWN ENDPOINTS
# ============================================================================

@router.get("/investigations/{investigation_id}/dimensions", response_model=MultiDimensionalAnalysisResponse, status_code=status.HTTP_200_OK)
def get_investigation_dimensions(
    investigation_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> MultiDimensionalAnalysisResponse:
    """Returns 10-dimensional cost decomposition across all provider and architectural axes."""
    service = InvestigationService(db)
    try:
        return service.get_dimensional_analysis(investigation_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/investigations/{investigation_id}/contributions", response_model=ContributionRankingResponse, status_code=status.HTTP_200_OK)
def get_investigation_contributions(
    investigation_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> ContributionRankingResponse:
    """Returns Pareto 80/20 ranked contributors and cumulative percentage curves."""
    service = InvestigationService(db)
    try:
        return service.get_contribution_ranking(investigation_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/investigations/{investigation_id}/usage-price-analysis", response_model=UsagePriceAnalysisResponse, status_code=status.HTTP_200_OK)
def get_investigation_usage_price(
    investigation_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> UsagePriceAnalysisResponse:
    """Separates volumetric usage change from rate/pricing tier escalation."""
    service = InvestigationService(db)
    try:
        return service.get_usage_price_analysis(investigation_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/investigations/{investigation_id}/timeline", response_model=TimelineAnalysisResponse, status_code=status.HTTP_200_OK)
def get_investigation_timeline(
    investigation_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> TimelineAnalysisResponse:
    """Returns contiguous daily cost timeline with baseline, moving averages, and DoD/WoW/MoM metrics."""
    service = InvestigationService(db)
    try:
        return service.get_timeline_analysis(investigation_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/investigations/{investigation_id}/resources", response_model=ResourceInvestigationResponse, status_code=status.HTTP_200_OK)
def get_investigation_resources(
    investigation_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> ResourceInvestigationResponse:
    """Returns inventory status, telemetry metrics, and topology relationships for affected resources."""
    service = InvestigationService(db)
    try:
        return service.get_resource_investigation(investigation_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/investigations/{investigation_id}/correlations", response_model=CrossSignalCorrelationResponse, status_code=status.HTTP_200_OK)
def get_investigation_correlations(
    investigation_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> CrossSignalCorrelationResponse:
    """Discovers matching waste detections, recommendations, and alert instances."""
    service = InvestigationService(db)
    try:
        return service.get_cross_signals(investigation_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/investigations/{investigation_id}/root-causes", response_model=List[InvestigationFindingResponse], status_code=status.HTTP_200_OK)
def get_investigation_root_causes(
    investigation_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> List[InvestigationFindingResponse]:
    """Returns all structured findings categorized by FACT, CORRELATION, HYPOTHESIS, VERIFIED_CAUSE."""
    findings = (
        db.query(InvestigationFinding)
        .filter(InvestigationFinding.investigation_id == investigation_id)
        .order_by(InvestigationFinding.financial_impact.desc(), InvestigationFinding.created_at.asc())
        .all()
    )
    return [InvestigationFindingResponse.model_validate(f) for f in findings]


# ============================================================================
# 4. COLLABORATION, NOTES, FINDINGS & EVIDENCE
# ============================================================================

@router.get("/investigations/{investigation_id}/evidence", response_model=List[InvestigationEvidenceLinkResponse], status_code=status.HTTP_200_OK)
def get_investigation_evidence(
    investigation_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> List[InvestigationEvidenceLinkResponse]:
    """Retrieves immutable evidence links supporting the investigation."""
    links = (
        db.query(InvestigationEvidenceLink)
        .filter(InvestigationEvidenceLink.investigation_id == investigation_id)
        .order_by(InvestigationEvidenceLink.created_at.asc())
        .all()
    )
    return [InvestigationEvidenceLinkResponse.model_validate(l) for l in links]


@router.post("/investigations/{investigation_id}/notes", response_model=InvestigationNoteResponse, status_code=status.HTTP_201_CREATED)
def add_investigation_note(
    investigation_id: UUID,
    note_in: InvestigationNoteCreate,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationNoteResponse:
    """Adds a collaboration or diagnostic note to the investigation case."""
    service = InvestigationService(db)
    try:
        return service.add_note(
            case_id=investigation_id,
            content=note_in.content,
            actor=principal.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/investigations/{investigation_id}/findings", response_model=InvestigationFindingResponse, status_code=status.HTTP_201_CREATED)
def add_investigation_finding(
    investigation_id: UUID,
    finding_in: InvestigationFindingCreate,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationFindingResponse:
    """Adds a verified root-cause finding or analyst hypothesis to the investigation."""
    service = InvestigationService(db)
    try:
        return service.add_finding(
            case_id=investigation_id,
            finding_in=finding_in,
            actor=principal.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/investigations/{investigation_id}/history", response_model=List[InvestigationHistoryResponse], status_code=status.HTTP_200_OK)
def get_investigation_history(
    investigation_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> List[InvestigationHistoryResponse]:
    """Retrieves immutable audit history of all status changes and assignments."""
    records = (
        db.query(InvestigationHistory)
        .filter(InvestigationHistory.investigation_id == investigation_id)
        .order_by(InvestigationHistory.created_at.desc())
        .all()
    )
    return [InvestigationHistoryResponse.model_validate(r) for r in records]


# ============================================================================
# 5. DIRECT ANOMALY INTEGRATION ENDPOINTS
# ============================================================================

@router.post("/anomalies/{anomaly_id}/investigate", response_model=InvestigationCaseDetailResponse, status_code=status.HTTP_201_CREATED)
def trigger_anomaly_investigation(
    anomaly_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> InvestigationCaseDetailResponse:
    """Directly triggers or opens an investigation case from an anomaly card or detail view."""
    service = InvestigationService(db)
    try:
        case_in = InvestigationCaseCreate(
            anomaly_id=anomaly_id,
            priority="HIGH",
            assigned_to=principal.email,
            initial_notes=f"Investigation initiated from Anomaly Detection Hub by {principal.email}.",
        )
        return service.create_case(case_in=case_in, actor=principal.email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/anomalies/{anomaly_id}/investigation-summary", response_model=AnomalyInvestigationSummaryResponse, status_code=status.HTTP_200_OK)
def get_anomaly_investigation_summary(
    anomaly_id: UUID,
    db: Session = Depends(get_sync_db),
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> AnomalyInvestigationSummaryResponse:
    """Retrieves investigation summary status and verified root cause for an anomaly."""
    service = InvestigationService(db)
    try:
        return service.get_anomaly_summary(anomaly_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
