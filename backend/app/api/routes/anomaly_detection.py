"""
CloudSage Cost Anomaly Detection REST API Endpoints.
FastAPI router providing 14 endpoints for running anomaly detection scans,
querying multi-dimensional anomalies, inspecting statistical baselines and evidence,
analyzing contributors and trends, and managing human-in-the-loop lifecycle states.
Advisory and non-destructive.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.engine import AnomalyDetectionEngine
from backend.app.anomaly_detection.impact import DAYS_PER_MONTH, DAYS_PER_YEAR
from backend.app.anomaly_detection.lifecycle import update_anomaly_status
from backend.app.anomaly_detection.schemas import (
    AnomalyContributorResponse,
    AnomalyEvidenceResponse,
    AnomalyRunRequest,
    AnomalyRunResponse,
    AnomalyStatusUpdateRequest,
    AnomalySummaryResponse,
    CostAnomalyListResponse,
    CostAnomalyResponse,
    CostBaselineListResponse,
    CostBaselineResponse,
    DetectionMethodInfoResponse,
    FinancialImpactSummaryResponse,
    TrendPointResponse,
    TrendResponse,
)
from backend.app.core.database import get_sync_db
from backend.app.core.enums import AnomalyCategory, AnomalyStatus, Severity
from backend.app.models.anomaly import CostAnomaly, CostBaseline

router = APIRouter(prefix="/anomaly-detection", tags=["Cost Anomaly Detection Engine"])
engine = AnomalyDetectionEngine()


@router.post("/run", response_model=AnomalyRunResponse, status_code=status.HTTP_200_OK)
def run_anomaly_detection(
    request: AnomalyRunRequest,
    db: Session = Depends(get_sync_db),
) -> AnomalyRunResponse:
    """
    Triggers an evidence-based multi-cloud cost anomaly detection run.
    Aggregates time-series, computes baselines, runs ensemble and change-point detectors,
    attributes root causes, and persists findings.
    """
    prov = None if request.provider == "ALL" else request.provider
    run = engine.execute_detection_run(
        db=db,
        provider=prov,
        account_id=request.account_id,
        service_name=request.service_name,
        start_date=request.start_date,
        end_date=request.end_date,
        baseline_window_days=request.baseline_window_days,
        scope="FULL" if not prov else f"PROVIDER_{prov}",
    )
    return AnomalyRunResponse.model_validate(run)


@router.get("/anomalies", response_model=CostAnomalyListResponse)
def list_anomalies(
    provider: Optional[str] = Query(None, description="Filter by cloud provider: AWS, AZURE, GCP"),
    account_id: Optional[str] = Query(None, description="Filter by account/subscription/project ID"),
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    status: Optional[str] = Query(None, description="Filter by status: DETECTED, INVESTIGATING, ACKNOWLEDGED, RESOLVED, DISMISSED, REOPENED"),
    severity: Optional[str] = Query(None, description="Filter by severity: LOW, MEDIUM, HIGH, CRITICAL"),
    category: Optional[str] = Query(None, description="Filter by anomaly category"),
    start_date: Optional[date] = Query(None, description="Filter anomalies on or after this date"),
    end_date: Optional[date] = Query(None, description="Filter anomalies on or before this date"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
) -> CostAnomalyListResponse:
    """Lists cost anomalies with multi-faceted filtering and pagination."""
    items = engine.list_anomalies(
        db=db,
        provider=provider,
        account_id=account_id,
        service_name=service_name,
        status=status,
        severity=severity,
        category=category,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    total = engine.count_anomalies(
        db=db,
        provider=provider,
        account_id=account_id,
        service_name=service_name,
        status=status,
        severity=severity,
        category=category,
        start_date=start_date,
        end_date=end_date,
    )
    return CostAnomalyListResponse(
        total=total,
        items=[CostAnomalyResponse.model_validate(i) for i in items],
        limit=limit,
        offset=offset,
    )


@router.get("/anomalies/{anomaly_id}", response_model=CostAnomalyResponse)
def get_anomaly_by_id(
    anomaly_id: uuid.UUID,
    db: Session = Depends(get_sync_db),
) -> CostAnomalyResponse:
    """Retrieves full details of a specific cost anomaly finding."""
    anomaly = engine.get_anomaly_by_id(db, anomaly_id)
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CostAnomaly with id {anomaly_id} not found",
        )
    return CostAnomalyResponse.model_validate(anomaly)


@router.get("/summary", response_model=AnomalySummaryResponse)
def get_anomaly_summary(
    provider: Optional[str] = Query(None, description="Filter by provider"),
    account_id: Optional[str] = Query(None, description="Filter by account"),
    db: Session = Depends(get_sync_db),
) -> AnomalySummaryResponse:
    """Returns high-level executive and operational summary metrics."""
    query = db.query(CostAnomaly)
    if provider:
        query = query.filter(CostAnomaly.provider == provider)
    if account_id:
        query = query.filter(CostAnomaly.account_id == account_id)

    anomalies = query.all()
    open_statuses = {"DETECTED", "INVESTIGATING", "ACKNOWLEDGED", "REOPENED", "OPEN"}

    open_anoms = [a for a in anomalies if (a.status or "DETECTED") in open_statuses]
    total_excess = sum((a.estimated_excess_cost or Decimal("0.0000") for a in open_anoms), Decimal("0.0000"))
    total_monthly = sum((a.projected_monthly_impact or Decimal("0.0000") for a in open_anoms), Decimal("0.0000"))

    by_sev = {s.value: 0 for s in Severity}
    by_prov: Dict[str, int] = {}
    by_cat = {c.value: 0 for c in AnomalyCategory}
    cost_by_prov: Dict[str, Decimal] = {}
    cost_by_srv: Dict[str, Decimal] = {}

    for a in open_anoms:
        s = a.severity or Severity.MEDIUM.value
        p = a.provider
        c = a.anomaly_category or AnomalyCategory.SERVICE_SPIKE.value
        srv = a.service_name or "Unknown"
        excess = a.estimated_excess_cost or Decimal("0.0000")

        by_sev[s] = by_sev.get(s, 0) + 1
        by_prov[p] = by_prov.get(p, 0) + 1
        by_cat[c] = by_cat.get(c, 0) + 1
        cost_by_prov[p] = cost_by_prov.get(p, Decimal("0.0000")) + excess
        cost_by_srv[srv] = cost_by_srv.get(srv, Decimal("0.0000")) + excess

    return AnomalySummaryResponse(
        total_open_anomalies=len(open_anoms),
        total_excess_cost_usd=total_excess,
        total_projected_monthly_impact_usd=total_monthly,
        anomalies_by_severity=by_sev,
        anomalies_by_provider=by_prov,
        anomalies_by_category=by_cat,
        excess_cost_by_provider=cost_by_prov,
        excess_cost_by_service=cost_by_srv,
    )


@router.get("/baselines", response_model=CostBaselineListResponse)
def list_baselines(
    provider: Optional[str] = Query(None, description="Filter by cloud provider"),
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
) -> CostBaselineListResponse:
    """Lists statistical expenditure baselines computed for cloud dimensions."""
    query = db.query(CostBaseline)
    if provider:
        query = query.filter(CostBaseline.provider == provider)
    if service_name:
        query = query.filter(CostBaseline.service_name == service_name)

    total = query.count()
    items = query.order_by(CostBaseline.calculated_at.desc()).offset(offset).limit(limit).all()

    return CostBaselineListResponse(
        total=total,
        items=[CostBaselineResponse.model_validate(b) for b in items],
        limit=limit,
        offset=offset,
    )


@router.get("/baselines/{baseline_id}", response_model=CostBaselineResponse)
def get_baseline_by_id(
    baseline_id: uuid.UUID,
    db: Session = Depends(get_sync_db),
) -> CostBaselineResponse:
    """Retrieves a specific statistical baseline distribution."""
    baseline = engine.get_baseline_by_id(db, baseline_id)
    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CostBaseline with id {baseline_id} not found",
        )
    return CostBaselineResponse.model_validate(baseline)


@router.get("/trends/{anomaly_id}", response_model=TrendResponse)
def get_anomaly_trend(
    anomaly_id: uuid.UUID,
    days_before: int = Query(14, ge=3, le=60),
    days_after: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_sync_db),
) -> TrendResponse:
    """Returns historical daily time-series surrounding an anomaly for charting."""
    trend_data = engine.get_trend(db, anomaly_id, days_before=days_before, days_after=days_after)
    if not trend_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CostAnomaly with id {anomaly_id} not found",
        )

    raw_pts = trend_data["points"]
    pts: List[TrendPointResponse] = []
    base_mean = trend_data["baseline_mean"]
    up_fence = trend_data["upper_fence"]

    for rp in raw_pts:
        pts.append(
            TrendPointResponse(
                date=rp["date"],
                observed_cost=rp["cost"],
                expected_cost=base_mean,
                upper_threshold=up_fence,
                lower_threshold=Decimal("0.0000"),
                is_anomaly=rp["is_anomaly_date"],
            )
        )

    start_d = pts[0].date if pts else date.today()
    end_d = pts[-1].date if pts else date.today()

    return TrendResponse(
        dimension_type=trend_data["dimension"],
        dimension_key=trend_data["dimension_key"],
        currency="USD",
        start_date=start_d,
        end_date=end_d,
        points=pts,
    )


@router.get("/contributors/{anomaly_id}", response_model=AnomalyContributorResponse)
def get_anomaly_contributors(
    anomaly_id: uuid.UUID,
    db: Session = Depends(get_sync_db),
) -> AnomalyContributorResponse:
    """Returns ranked contributing resources and SKUs driving the cost anomaly."""
    anomaly = engine.get_anomaly_by_id(db, anomaly_id)
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CostAnomaly with id {anomaly_id} not found",
        )

    contributors = anomaly.contributing_resources or []
    return AnomalyContributorResponse(
        anomaly_id=anomaly.id,
        service_name=anomaly.service_name or "General",
        total_actual_cost=anomaly.actual_cost,
        total_expected_cost=anomaly.expected_cost,
        absolute_increase=anomaly.absolute_deviation,
        contributors=contributors,
        explanation=anomaly.explanation,
    )


@router.get("/evidence/{anomaly_id}", response_model=AnomalyEvidenceResponse)
def get_anomaly_evidence(
    anomaly_id: uuid.UUID,
    db: Session = Depends(get_sync_db),
) -> AnomalyEvidenceResponse:
    """Returns underlying statistical parameters and source billing references."""
    anomaly = engine.get_anomaly_by_id(db, anomaly_id)
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CostAnomaly with id {anomaly_id} not found",
        )

    return AnomalyEvidenceResponse(
        anomaly_id=anomaly.id,
        anomaly_date=anomaly.anomaly_date,
        provider=anomaly.provider,
        service_name=anomaly.service_name or "General",
        detection_method=anomaly.detection_method,
        actual_cost=anomaly.actual_cost,
        expected_cost=anomaly.expected_cost,
        z_score=anomaly.z_score,
        confidence_score=anomaly.confidence_score,
        baseline_metrics=anomaly.baseline_metrics or {},
        root_cause_analysis=anomaly.root_cause_analysis or {},
        source_billing_references=anomaly.source_billing_references or [],
    )


@router.get("/runs", response_model=List[AnomalyRunResponse])
def list_detection_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
) -> List[AnomalyRunResponse]:
    """Lists historical anomaly detection runs and execution statistics."""
    runs = engine.list_runs(db, limit=limit, offset=offset)
    return [AnomalyRunResponse.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=AnomalyRunResponse)
def get_detection_run_by_id(
    run_id: uuid.UUID,
    db: Session = Depends(get_sync_db),
) -> AnomalyRunResponse:
    """Retrieves an execution audit record by run_id."""
    run = engine.get_run_by_id(db, run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AnomalyDetectionRun with id {run_id} not found",
        )
    return AnomalyRunResponse.model_validate(run)


@router.get("/methods", response_model=List[DetectionMethodInfoResponse])
def get_detection_methods() -> List[DetectionMethodInfoResponse]:
    """Returns descriptions of supported anomaly detection methods and their mathematical definitions."""
    return [
        DetectionMethodInfoResponse(
            method_id="Z_SCORE",
            name="Parametric Z-Score",
            formula="z = (x - mu) / sigma",
            description="Identifies observations that exceed mu + k * sigma, assuming normal spending distribution.",
            default_thresholds={"threshold": "2.5000", "min_points": 7},
        ),
        DetectionMethodInfoResponse(
            method_id="MODIFIED_Z_SCORE",
            name="Median Absolute Deviation (MAD) Modified Z-Score",
            formula="M_i = 0.6745 * (x_i - median) / MAD",
            description="Robust non-parametric score unaffected by existing extreme outliers or skewed distributions.",
            default_thresholds={"threshold": "3.0000", "min_points": 7},
        ),
        DetectionMethodInfoResponse(
            method_id="IQR",
            name="Interquartile Range Tukey Fences",
            formula="Upper Fence = Q3 + 1.5 * (Q3 - Q1)",
            description="Classic exploratory boxplot outlier detection using quartile spread.",
            default_thresholds={"multiplier": "1.5000", "min_points": 7},
        ),
        DetectionMethodInfoResponse(
            method_id="CHANGE_POINT",
            name="CUSUM & Dual-Window Structural Shift",
            formula="S_i = max(0, S_{i-1} + (x_i - (mu + k)))",
            description="Detects persistent step increases and gradual structural shifts in cloud expenditure.",
            default_thresholds={"k_slack": "0.5000", "h_threshold": "4.0000", "min_days": 14},
        ),
        DetectionMethodInfoResponse(
            method_id="ENSEMBLE",
            name="Consensus Multi-Method Detector",
            formula="Votes = Sum(I(Method_j triggers)) >= 2",
            description="Combines Z-score, Modified Z-score, and IQR to eliminate false positives.",
            default_thresholds={"consensus_min_votes": 2},
        ),
        DetectionMethodInfoResponse(
            method_id="NEW_SPEND",
            name="First-Seen Zero-History Detector",
            formula="x_t > min_cost AND sum(x_{t-k...t-1}) == 0",
            description="Detects newly appeared spending on previously inactive or newly created resources.",
            default_thresholds={"min_new_spend_cost": "15.0000", "required_zero_days": 7},
        ),
    ]


@router.get("/financial-impact", response_model=FinancialImpactSummaryResponse)
def get_financial_impact_summary(
    provider: Optional[str] = Query(None, description="Filter by cloud provider"),
    account_id: Optional[str] = Query(None, description="Filter by account"),
    db: Session = Depends(get_sync_db),
) -> FinancialImpactSummaryResponse:
    """Returns aggregated deduplicated financial impact and annualized projections."""
    query = db.query(CostAnomaly)
    if provider:
        query = query.filter(CostAnomaly.provider == provider)
    if account_id:
        query = query.filter(CostAnomaly.account_id == account_id)

    anomalies = query.all()
    open_statuses = {"DETECTED", "INVESTIGATING", "ACKNOWLEDGED", "REOPENED", "OPEN"}
    active_anoms = [a for a in anomalies if (a.status or "DETECTED") in open_statuses]

    total_excess = sum((a.estimated_excess_cost or Decimal("0.0000") for a in active_anoms), Decimal("0.0000"))
    total_monthly = sum((a.projected_monthly_impact or Decimal("0.0000") for a in active_anoms), Decimal("0.0000"))
    total_annual = (total_excess * DAYS_PER_YEAR / DAYS_PER_MONTH).quantize(Decimal("0.0001"))

    by_prov: Dict[str, Decimal] = {}
    by_cat: Dict[str, Decimal] = {}
    by_sev: Dict[str, Decimal] = {}

    for a in active_anoms:
        p = a.provider
        c = a.anomaly_category or AnomalyCategory.SERVICE_SPIKE.value
        s = a.severity or Severity.MEDIUM.value
        excess = a.estimated_excess_cost or Decimal("0.0000")

        by_prov[p] = by_prov.get(p, Decimal("0.0000")) + excess
        by_cat[c] = by_cat.get(c, Decimal("0.0000")) + excess
        by_sev[s] = by_sev.get(s, Decimal("0.0000")) + excess

    top_spikes = [
        {
            "anomaly_id": str(a.id),
            "provider": a.provider,
            "service_name": a.service_name,
            "anomaly_date": a.anomaly_date.isoformat(),
            "actual_cost": str(a.actual_cost),
            "excess_cost": str(a.estimated_excess_cost),
            "percentage_increase": str(a.spike_percentage),
            "severity": a.severity,
        }
        for a in sorted(active_anoms, key=lambda item: item.estimated_excess_cost or Decimal("0.0000"), reverse=True)[:5]
    ]

    return FinancialImpactSummaryResponse(
        currency="USD",
        total_excess_expenditure=total_excess,
        projected_monthly_impact=total_monthly,
        projected_annual_impact=total_annual,
        active_anomalies_count=len(active_anoms),
        excess_by_provider=by_prov,
        excess_by_category=by_cat,
        excess_by_severity=by_sev,
        top_cost_spikes=top_spikes,
    )


@router.patch("/anomalies/{anomaly_id}/status", response_model=CostAnomalyResponse)
def update_status(
    anomaly_id: uuid.UUID,
    payload: AnomalyStatusUpdateRequest,
    db: Session = Depends(get_sync_db),
) -> CostAnomalyResponse:
    """Updates anomaly status (ACKNOWLEDGED, INVESTIGATING, DISMISSED, RESOLVED, REOPENED)."""
    try:
        new_stat = AnomalyStatus(payload.status)
    except ValueError:
        valid_vals = [s.value for s in AnomalyStatus]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{payload.status}'. Valid values are: {valid_vals}",
        )

    try:
        updated = update_anomaly_status(
            db=db,
            anomaly_id=anomaly_id,
            new_status=new_stat,
            user=payload.user or "finops_reviewer",
            reason=payload.reason,
            notes=payload.investigation_notes,
        )
        return CostAnomalyResponse.model_validate(updated)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

