"""
CloudSage Investigation Pydantic v2 Schemas.
Enforces strict Decimal representation for monetary values and validates
multi-dimensional root cause analysis payloads.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# --- Request Schemas ---

class InvestigationCaseCreate(BaseModel):
    anomaly_id: UUID = Field(..., description="Target cost anomaly identifier to investigate")
    alert_instance_id: Optional[UUID] = Field(None, description="Optional associated alert instance")
    title: Optional[str] = Field(None, max_length=256, description="Optional custom title (defaults from anomaly)")
    priority: Optional[str] = Field("MEDIUM", description="Priority tier: CRITICAL, HIGH, MEDIUM, LOW")
    assigned_to: Optional[str] = Field(None, max_length=128, description="Initial assignee email or principal ID")
    initial_notes: Optional[str] = Field(None, description="Initial investigation notes or hypothesis")


class InvestigationCaseUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=256)
    priority: Optional[str] = Field(None, description="CRITICAL, HIGH, MEDIUM, LOW")
    assigned_to: Optional[str] = Field(None, max_length=128)
    root_cause_summary: Optional[str] = None
    verified_root_cause: Optional[str] = None
    suspected_category: Optional[str] = None
    resolution_notes: Optional[str] = None


class InvestigationAssignRequest(BaseModel):
    assigned_to: str = Field(..., max_length=128, description="Email or principal ID of assignee")
    notes: Optional[str] = Field(None, description="Optional assignment handover notes")


class InvestigationTransitionRequest(BaseModel):
    status: str = Field(..., description="Target lifecycle status: NEW, ASSIGNED, INVESTIGATING, ROOT_CAUSE_IDENTIFIED, ACTION_RECOMMENDED, RESOLVED, CLOSED")
    notes: Optional[str] = Field(None, description="Operational notes or justification")
    verified_root_cause: Optional[str] = Field(None, description="Required when transitioning to ROOT_CAUSE_IDENTIFIED or RESOLVED")


class InvestigationNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Analyst note or collaboration comment")


class InvestigationFindingCreate(BaseModel):
    finding_type: str = Field(..., description="FACT, CORRELATION, HYPOTHESIS, VERIFIED_CAUSE")
    title: str = Field(..., min_length=3, max_length=256)
    explanation: str = Field(..., min_length=5)
    dimension: Optional[str] = Field(None, max_length=64, description="SERVICE, RESOURCE, SKU, REGION, USAGE, PRICING, ENVIRONMENT")
    financial_impact: Decimal = Field(default=Decimal("0.0000"), ge=0, description="Dollar share of total excess spend")
    contribution_percentage: Decimal = Field(default=Decimal("0.00"), ge=0, le=100, description="Percentage of anomaly excess")
    confidence_category: str = Field("MEDIUM", description="HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE")
    confidence_score: Decimal = Field(default=Decimal("1.0000"), ge=0, le=1)
    evidence_source: str = Field("BILLING_RECORD", description="BILLING_RECORD, RESOURCE_INVENTORY, UTILIZATION_METRIC, etc.")
    evidence_reference: Optional[str] = Field(None, max_length=512)
    supporting_observations: List[str] = Field(default_factory=list)
    contradictory_observations: List[str] = Field(default_factory=list)
    suggested_next_step: Optional[str] = None


# --- Response Schemas ---

class InvestigationFindingResponse(BaseModel):
    id: UUID
    investigation_id: UUID
    finding_type: str
    title: str
    explanation: str
    dimension: Optional[str]
    financial_impact: Decimal
    contribution_percentage: Decimal
    confidence_category: str
    confidence_score: Decimal
    evidence_source: str
    evidence_reference: Optional[str]
    supporting_observations: List[str]
    contradictory_observations: List[str]
    suggested_next_step: Optional[str]
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestigationNoteResponse(BaseModel):
    id: UUID
    investigation_id: UUID
    author: str
    content: str
    is_system_generated: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestigationEvidenceLinkResponse(BaseModel):
    id: UUID
    investigation_id: UUID
    entity_type: str
    entity_id: str
    relationship_role: str
    metadata_snapshot: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestigationHistoryResponse(BaseModel):
    id: UUID
    investigation_id: UUID
    from_status: Optional[str]
    to_status: str
    actor: str
    action: str
    notes: Optional[str]
    details: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestigationCaseResponse(BaseModel):
    id: UUID
    case_number: str
    anomaly_id: UUID
    alert_instance_id: Optional[UUID]
    title: str
    status: str
    priority: str
    assigned_to: Optional[str]
    assigned_at: Optional[datetime]
    provider: str
    account_id: str
    service_name: str
    region: Optional[str]
    resource_id: Optional[str]
    excess_cost: Decimal
    actual_cost: Decimal
    expected_cost: Decimal
    root_cause_summary: Optional[str]
    verified_root_cause: Optional[str]
    suspected_category: Optional[str]
    resolution_notes: Optional[str]
    created_by: str
    updated_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    closed_by: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class InvestigationCaseDetailResponse(InvestigationCaseResponse):
    findings: List[InvestigationFindingResponse] = Field(default_factory=list)
    notes: List[InvestigationNoteResponse] = Field(default_factory=list)
    evidence_links: List[InvestigationEvidenceLinkResponse] = Field(default_factory=list)
    history: List[InvestigationHistoryResponse] = Field(default_factory=list)
    anomaly_details: Optional[Dict[str, Any]] = None


class InvestigationCaseListResponse(BaseModel):
    items: List[InvestigationCaseResponse]
    total: int


class InvestigationStatsResponse(BaseModel):
    total_investigations: int
    open_investigations: int
    critical_investigations: int
    unassigned_investigations: int
    root_cause_identified_count: int
    resolved_investigations: int
    total_excess_spend_investigated: Decimal
    average_investigation_age_hours: Decimal


# --- Analytical Decomposition Schemas ---

class DimensionContributor(BaseModel):
    dimension_key: str
    dimension_value: str
    actual_cost: Decimal
    expected_cost: Decimal
    excess_cost: Decimal
    percentage_deviation: Decimal
    contribution_share: Decimal
    resource_count: int


class DimensionDecompositionResponse(BaseModel):
    dimension_name: str
    total_excess_cost: Decimal
    contributors: List[DimensionContributor]
    unallocated_excess_cost: Decimal
    coverage_percentage: Decimal


class MultiDimensionalAnalysisResponse(BaseModel):
    investigation_id: UUID
    anomaly_id: UUID
    total_excess_cost: Decimal
    dimensions: Dict[str, List[DimensionContributor]]
    dominant_dimension: str
    analysis_timestamp: datetime


class ContributionRankingItem(BaseModel):
    rank: int
    entity_type: str
    entity_id: str
    entity_name: Optional[str]
    provider: str
    service_name: str
    excess_cost: Decimal
    contribution_share: Decimal
    cumulative_share: Decimal
    confidence_category: str


class ContributionRankingResponse(BaseModel):
    investigation_id: UUID
    total_excess_cost: Decimal
    top_contributors: List[ContributionRankingItem]
    pareto_80_count: int


class UsagePriceDecompositionItem(BaseModel):
    category: str
    amount: Decimal
    percentage_share: Decimal
    explanation: str


class UsagePriceAnalysisResponse(BaseModel):
    investigation_id: UUID
    total_excess_cost: Decimal
    usage_effect: Decimal
    price_effect: Decimal
    mix_or_quantity_effect: Decimal
    unclassified_effect: Decimal
    primary_cost_driver: str
    decomposition_breakdown: List[UsagePriceDecompositionItem]
    methodology_notes: str


class TimelineDataPoint(BaseModel):
    date: str
    actual_cost: Decimal
    baseline_expected_cost: Decimal
    excess_cost: Decimal
    is_anomaly_period: bool
    seven_day_moving_avg: Optional[Decimal] = None


class TimelineAnalysisResponse(BaseModel):
    investigation_id: UUID
    anomaly_date: str
    anomaly_start: str
    peak_spend_date: str
    peak_excess_cost: Decimal
    data_points: List[TimelineDataPoint]
    day_over_day_change_pct: Decimal
    week_over_week_change_pct: Decimal
    month_over_month_change_pct: Decimal


class ResourceInvestigationItem(BaseModel):
    resource_id: str
    resource_name: Optional[str]
    resource_type: str
    provider: str
    region: str
    owner: Optional[str]
    environment: str
    cost_center: Optional[str]
    actual_cost: Decimal
    excess_cost: Decimal
    contribution_percentage: Decimal
    status: str
    metrics_summary: Dict[str, Any] = Field(default_factory=dict)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)


class ResourceInvestigationResponse(BaseModel):
    investigation_id: UUID
    total_affected_resources: int
    resources: List[ResourceInvestigationItem]


class CrossSignalCorrelationResponse(BaseModel):
    investigation_id: UUID
    correlated_waste_detections: List[Dict[str, Any]] = Field(default_factory=list)
    correlated_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    correlated_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    correlation_confidence: str
    correlation_summary: str


class AnomalyInvestigationSummaryResponse(BaseModel):
    anomaly_id: UUID
    has_active_investigation: bool
    investigation_id: Optional[UUID] = None
    case_number: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None
    excess_cost: Decimal
    primary_root_cause: Optional[str] = None
    confidence_category: str
    finding_count: int
