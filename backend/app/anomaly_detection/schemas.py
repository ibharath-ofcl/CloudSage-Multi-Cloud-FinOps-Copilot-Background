"""
CloudSage Cost Anomaly Detection Request and Response Schemas.
Pydantic v2 schemas for anomaly findings, baselines, trends, contributors, and review actions.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class CostAnomalyResponse(BaseModel):
    """Schema representing an identified cloud cost anomaly."""
    id: uuid.UUID
    detector_id: str
    detector_version: str
    provider: str
    account_id: str
    service_category: str
    service_name: str
    region: str
    resource_id: Optional[str] = None
    sku: Optional[str] = None
    anomaly_category: str
    title: Optional[str] = None
    explanation: Optional[str] = None
    anomaly_date: date
    detection_method: str
    actual_cost: Decimal
    expected_cost: Decimal
    baseline_mean: Decimal
    baseline_stddev: Decimal
    z_score: Decimal
    spike_percentage: Decimal
    absolute_deviation: Decimal
    estimated_excess_cost: Decimal
    projected_monthly_impact: Decimal
    currency: str = "USD"
    severity: str
    status: str
    confidence_score: Decimal
    baseline_window_days: int
    observation_window_days: int
    baseline_metrics: Dict[str, Any] = Field(default_factory=dict)
    root_cause_analysis: Dict[str, Any] = Field(default_factory=dict)
    contributing_resources: List[Dict[str, Any]] = Field(default_factory=list)
    source_billing_references: List[str] = Field(default_factory=list)
    dismissal_reason: Optional[str] = None
    dismissed_by: Optional[str] = None
    resolution_reason: Optional[str] = None
    resolved_by: Optional[str] = None
    investigation_notes: Optional[str] = None
    first_detected_at: datetime
    last_detected_at: datetime
    reopened_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CostAnomalyListResponse(BaseModel):
    """Paginated list of cost anomalies."""
    total: int
    items: List[CostAnomalyResponse]
    limit: int
    offset: int


class AnomalySummaryResponse(BaseModel):
    """Executive summary of open anomalies and financial excess."""
    total_open_anomalies: int
    total_excess_cost_usd: Decimal
    total_projected_monthly_impact_usd: Decimal
    anomalies_by_severity: Dict[str, int]
    anomalies_by_provider: Dict[str, int]
    anomalies_by_category: Dict[str, int]
    excess_cost_by_provider: Dict[str, Decimal]
    excess_cost_by_service: Dict[str, Decimal]


class CostBaselineResponse(BaseModel):
    """Schema representing a statistical baseline distribution."""
    id: uuid.UUID
    dimension_type: str
    dimension_key: str
    provider: str
    account_id: Optional[str] = None
    service_name: Optional[str] = None
    region: Optional[str] = None
    resource_id: Optional[str] = None
    window_days: int
    start_date: date
    end_date: date
    mean: Decimal
    stddev: Decimal
    median: Decimal
    mad: Decimal
    q1: Decimal
    q3: Decimal
    iqr: Decimal
    min_value: Decimal
    max_value: Decimal
    sample_count: int
    zero_count: int
    currency: str = "USD"
    version: str
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CostBaselineListResponse(BaseModel):
    """Paginated list of statistical baselines."""
    total: int
    items: List[CostBaselineResponse]
    limit: int
    offset: int


class TrendPointResponse(BaseModel):
    """A single date's trend observation."""
    date: date
    observed_cost: Decimal
    expected_cost: Decimal
    upper_threshold: Decimal
    lower_threshold: Decimal
    is_anomaly: bool = False
    anomaly_category: Optional[str] = None


class TrendResponse(BaseModel):
    """Time-series trend comparing observed expenditure against baseline and thresholds."""
    dimension_type: str
    dimension_key: str
    currency: str = "USD"
    start_date: date
    end_date: date
    points: List[TrendPointResponse]


class AnomalyContributorResponse(BaseModel):
    """Contributing resource or SKU breakdown for a specific anomaly."""
    anomaly_id: uuid.UUID
    service_name: str
    total_actual_cost: Decimal
    total_expected_cost: Decimal
    absolute_increase: Decimal
    contributors: List[Dict[str, Any]]
    explanation: Optional[str] = None


class AnomalyEvidenceResponse(BaseModel):
    """Detailed mathematical and observational evidence backing an anomaly."""
    anomaly_id: uuid.UUID
    anomaly_date: date
    provider: str
    service_name: str
    detection_method: str
    actual_cost: Decimal
    expected_cost: Decimal
    z_score: Decimal
    confidence_score: Decimal
    baseline_metrics: Dict[str, Any]
    root_cause_analysis: Dict[str, Any]
    source_billing_references: List[str]


class AnomalyRunRequest(BaseModel):
    """Payload for triggering an anomaly detection run."""
    provider: Optional[str] = Field("ALL", description="AWS, AZURE, GCP, or ALL")
    account_id: Optional[str] = Field(None, description="Specific account, subscription, or project")
    service_name: Optional[str] = Field(None, description="Specific cloud service name")
    start_date: Optional[date] = Field(None, description="Start date for evaluation window")
    end_date: Optional[date] = Field(None, description="End date for evaluation window")
    baseline_window_days: int = Field(30, ge=7, le=90, description="Baseline lookback window in days")


class AnomalyRunResponse(BaseModel):
    """Execution audit statistics for an anomaly detection run."""
    run_id: uuid.UUID
    provider: str
    scope: str
    status: str
    total_series_evaluated: int
    baselines_generated: int
    anomalies_created: int
    anomalies_updated: int
    anomalies_unchanged: int
    anomalies_resolved: int
    total_excess_cost: Decimal
    detector_summary: Dict[str, Any] = Field(default_factory=dict)
    error_details: List[Any] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AnomalyStatusUpdateRequest(BaseModel):
    """Payload for human review: acknowledge, investigate, dismiss, or resolve."""
    status: str = Field(..., description="ACKNOWLEDGED, INVESTIGATING, DISMISSED, RESOLVED")
    reason: Optional[str] = Field(None, description="Mandatory reason for dismissal or resolution explanation")
    user: Optional[str] = Field(None, description="Reviewer email or username")
    investigation_notes: Optional[str] = Field(None, description="Ongoing investigation notes")


class FinancialImpactSummaryResponse(BaseModel):
    """Aggregated financial impact metrics across anomalies."""
    currency: str = "USD"
    total_excess_expenditure: Decimal
    projected_monthly_impact: Decimal
    projected_annual_impact: Decimal
    active_anomalies_count: int
    excess_by_provider: Dict[str, Decimal]
    excess_by_category: Dict[str, Decimal]
    excess_by_severity: Dict[str, Decimal]
    top_cost_spikes: List[Dict[str, Any]]


class DetectionMethodInfoResponse(BaseModel):
    """Description of a supported detection method and its mathematical formulation."""
    method_id: str
    name: str
    formula: str
    description: str
    default_thresholds: Dict[str, Any]
