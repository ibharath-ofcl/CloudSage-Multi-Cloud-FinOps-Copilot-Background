"""
CloudSage Advisory Recommendation Pydantic Schemas.
Full request/response validation schemas for recommendations, runs, evidence, lifecycle, and financial KPIs.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import (
    CloudProvider,
    ImplementationEffort,
    Priority,
    RecommendationAction,
    RecommendationStatus,
    RiskLevel,
)


class RecommendationBase(BaseModel):
    resource_id: Optional[str] = Field(None, max_length=512)
    provider: CloudProvider
    action_type: RecommendationAction
    priority: Priority = Field(default=Priority.P2)
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    status: RecommendationStatus = Field(default=RecommendationStatus.PROPOSED)
    estimated_monthly_savings: Decimal = Field(..., ge=0, description="Monthly dollar savings")
    estimated_annual_savings: Decimal = Field(..., ge=0, description="Annual dollar savings")
    implementation_effort: ImplementationEffort = Field(default=ImplementationEffort.LOW)
    title: str = Field(..., max_length=256)
    description: str
    remediation_guide: str = Field(..., description="Step-by-step remediation guide or CLI snippet")
    endorsed_by: Optional[str] = Field(None, max_length=128)
    approved_by: Optional[str] = Field(None, max_length=128)
    approved_at: Optional[datetime] = None
    implemented_at: Optional[datetime] = None


class RecommendationCreate(RecommendationBase):
    waste_detection_id: Optional[UUID] = None
    recommendation_key: Optional[str] = None
    account_id: Optional[str] = None
    region: Optional[str] = None
    service_name: Optional[str] = None
    service_category: Optional[str] = None
    resource_name: Optional[str] = None
    strategy_id: Optional[str] = "advisory_strategy"
    strategy_version: Optional[str] = "1.0"
    priority_score: Optional[Decimal] = Decimal("0.5000")
    risk_score: Optional[Decimal] = Decimal("0.2000")
    confidence_score: Optional[Decimal] = Decimal("1.0000")
    current_monthly_cost: Optional[Decimal] = Decimal("0.0000")
    projected_monthly_cost: Optional[Decimal] = Decimal("0.0000")
    currency: Optional[str] = "USD"
    savings_calculation: Optional[Dict[str, Any]] = None
    implementation_guidance: Optional[Dict[str, Any]] = None
    assumptions: Optional[List[str]] = None
    evidence_summary: Optional[Dict[str, Any]] = None
    tags: Optional[Dict[str, Any]] = None


class RecommendationStatusUpdate(BaseModel):
    status: RecommendationStatus
    actor_email: str = Field(..., max_length=128)
    notes: Optional[str] = None
    reason: Optional[str] = None


class RecommendationFeedback(BaseModel):
    actor_email: str = Field(..., max_length=128)
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_text: str = Field(..., min_length=1)
    action_type: Optional[str] = "FEEDBACK"


class RecommendationEvidenceResponse(BaseModel):
    id: UUID
    recommendation_id: UUID
    evidence_type: str
    waste_detection_id: Optional[UUID] = None
    anomaly_id: Optional[UUID] = None
    resource_id: Optional[str] = None
    description: str
    telemetry_data: Dict[str, Any] = Field(default_factory=dict)
    billing_record_ids: List[str] = Field(default_factory=list)
    confidence_score: Decimal
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationHistoryResponse(BaseModel):
    id: UUID
    recommendation_id: UUID
    from_status: Optional[str] = None
    to_status: str
    actor: str
    action: str
    notes: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(RecommendationBase):
    id: UUID
    recommendation_key: Optional[str] = None
    waste_detection_id: Optional[UUID] = None
    account_id: Optional[str] = None
    region: Optional[str] = None
    service_name: Optional[str] = None
    service_category: Optional[str] = None
    resource_name: Optional[str] = None
    strategy_id: Optional[str] = None
    strategy_version: Optional[str] = None
    priority_score: Optional[Decimal] = None
    risk_score: Optional[Decimal] = None
    confidence_score: Optional[Decimal] = None
    current_monthly_cost: Optional[Decimal] = None
    projected_monthly_cost: Optional[Decimal] = None
    verified_savings: Optional[Decimal] = None
    currency: Optional[str] = "USD"
    savings_calculation: Optional[Dict[str, Any]] = Field(default_factory=dict)
    implementation_guidance: Optional[Dict[str, Any]] = Field(default_factory=dict)
    assumptions: Optional[List[Any]] = Field(default_factory=list)
    evidence_summary: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tags: Optional[Dict[str, Any]] = Field(default_factory=dict)
    review_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    expiry_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationDetailResponse(RecommendationResponse):
    evidence_items: List[RecommendationEvidenceResponse] = Field(default_factory=list)
    history_items: List[RecommendationHistoryResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RecommendationRunRequest(BaseModel):
    provider: Optional[str] = "ALL"
    strategies: Optional[List[str]] = None
    account_id: Optional[str] = None
    service_name: Optional[str] = None
    scope: Optional[str] = "FULL"


class RecommendationRunResponse(BaseModel):
    run_id: UUID
    provider: str
    scope: str
    status: str
    total_evaluated: int
    recommendations_created: int
    recommendations_updated: int
    recommendations_unchanged: int
    recommendations_suppressed: int
    total_monthly_savings: Decimal
    total_annual_savings: Decimal
    strategy_summary: Dict[str, Any] = Field(default_factory=dict)
    error_details: List[Any] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationSummaryResponse(BaseModel):
    total_recommendations: int
    total_monthly_savings: Decimal
    total_annual_savings: Decimal
    by_provider: Dict[str, Dict[str, Any]]
    by_priority: Dict[str, int]
    by_status: Dict[str, int]
    by_effort: Dict[str, int]
    by_risk: Dict[str, int]
    top_categories: List[Dict[str, Any]]


class RecommendationPriorityBreakdown(BaseModel):
    priority: str
    count: int
    monthly_savings: Decimal
    annual_savings: Decimal


class RecommendationCategoryBreakdown(BaseModel):
    action_type: str
    count: int
    monthly_savings: Decimal
    annual_savings: Decimal


class RecommendationSavingsDetail(BaseModel):
    recommendation_id: UUID
    current_monthly_cost: Decimal
    projected_monthly_cost: Decimal
    monthly_savings: Decimal
    annual_savings: Decimal
    savings_percentage: Decimal
    currency: str
    calculation_breakdown: Dict[str, Any]


class FinancialImpactResponse(BaseModel):
    total_identified_monthly_savings: Decimal
    total_identified_annual_savings: Decimal
    total_realized_monthly_savings: Decimal
    total_realized_annual_savings: Decimal
    realization_rate_pct: Decimal
    savings_by_provider: Dict[str, Decimal]
    savings_by_service: Dict[str, Decimal]


class OwnerImpactResponse(BaseModel):
    owner: str
    recommendation_count: int
    total_monthly_savings: Decimal
    total_annual_savings: Decimal
    pending_approval_count: int
