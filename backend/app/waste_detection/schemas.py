"""
CloudSage Waste Detection Request and Response Schemas.
Pydantic v2 schemas for waste findings, detection runs, summary reports, and review workflows.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import Severity, WasteStatus, WasteType


class WasteFindingResponse(BaseModel):
    """Schema representing an identified cloud waste finding."""
    id: uuid.UUID
    resource_id: str
    provider: str
    account_id: Optional[str] = None
    resource_type: Optional[str] = None
    detector_id: Optional[str] = None
    detector_version: str
    waste_type: str
    finding_title: Optional[str] = None
    explanation: Optional[str] = None
    severity: str
    status: str
    confidence_score: Decimal
    estimated_monthly_savings: Decimal
    currency: str = "USD"
    original_currency: Optional[str] = None
    original_cost: Optional[Decimal] = None
    observation_window_days: int
    data_quality_status: str
    requires_human_review: bool
    telemetry_proof: Dict[str, Any] = Field(default_factory=dict)
    first_detected_at: datetime
    last_evaluated_at: datetime
    dismissal_reason: Optional[str] = None
    dismissed_by: Optional[str] = None
    snooze_until: Optional[datetime] = None
    assigned_to: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    reopened_by: Optional[str] = None
    reopened_at: Optional[datetime] = None
    action_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WasteFindingListResponse(BaseModel):
    """Paginated list of cloud waste findings."""
    total: int
    items: List[WasteFindingResponse]
    limit: int
    offset: int


class WasteDetectionRunRequest(BaseModel):
    """Request payload for triggering a waste detection run."""
    provider: Optional[str] = Field("ALL", description="AWS, AZURE, GCP, or ALL")
    account_id: Optional[str] = Field(None, description="Specific cloud account/subscription/project")
    detectors: Optional[List[str]] = Field(None, description="List of detector IDs to execute")
    categories: Optional[List[str]] = Field(None, description="List of waste categories to evaluate")
    lookback_days: int = Field(7, ge=1, le=90, description="Metric observation window in days")


class WasteDetectionRunResponse(BaseModel):
    """Audit schema for a waste detection execution."""
    run_id: uuid.UUID
    provider: str
    status: str
    total_resources_evaluated: int
    findings_created: int
    findings_updated: int
    findings_unchanged: int
    total_estimated_monthly_savings: Decimal
    detector_summary: Dict[str, Any] = Field(default_factory=dict)
    error_details: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WasteSummaryResponse(BaseModel):
    """Executive KPI and category breakdown summary of cloud waste."""
    total_open_findings: int
    total_estimated_monthly_savings: Decimal
    findings_by_severity: Dict[str, int]
    findings_by_category: Dict[str, int]
    findings_by_provider: Dict[str, int]
    savings_by_category: Dict[str, Decimal]
    savings_by_provider: Dict[str, Decimal]


class FindingStatusUpdateRequest(BaseModel):
    """Human review request for acknowledging, dismissing, resolving, or snoozing a finding."""
    status: str = Field(..., description="ACKNOWLEDGED, DISMISSED, RESOLVED, SNOOZED")
    reason: Optional[str] = Field(None, description="Explanation for dismissal or status change")
    user: Optional[str] = Field(None, description="Reviewer email / username")
    snooze_days: Optional[int] = Field(None, ge=1, le=90, description="Days to snooze finding before re-evaluation")


class DetectorInfoResponse(BaseModel):
    """Metadata describing a registered waste detector."""
    detector_id: str
    detector_version: str
    waste_category: str
    description: str
    supported_providers: List[str]
    default_thresholds: Dict[str, Any]


class WasteActionRequest(BaseModel):
    action: str = Field(..., description="Action: ACKNOWLEDGE, ASSIGN, SNOOZE, DISMISS, RESOLVE, REOPEN")
    actor: str = Field(..., max_length=128)
    reason: Optional[str] = None
    snooze_days: Optional[int] = Field(None, ge=1, le=365)
    assigned_to: Optional[str] = None


class BatchWasteActionRequest(BaseModel):
    finding_ids: List[uuid.UUID] = Field(..., min_length=1)
    action: str = Field(..., description="Action: ACKNOWLEDGE, ASSIGN, SNOOZE, DISMISS, RESOLVE, REOPEN")
    actor: str = Field(..., max_length=128)
    reason: Optional[str] = None
    snooze_days: Optional[int] = Field(None, ge=1, le=365)
    assigned_to: Optional[str] = None


class BatchWasteActionResponse(BaseModel):
    total_requested: int
    total_successful: int
    total_failed: int
    successful: List[Dict[str, Any]]
    failed: List[Dict[str, Any]]
