"""
CloudSage Cost Anomaly Detection Internal Data Models.
Structured dataclasses for time-series points, statistical baselines,
anomaly candidates, and detector execution results.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from backend.app.core.enums import AnomalyCategory, DetectionMethod, Severity


@dataclass
class TimeSeriesPoint:
    """A single daily or monthly observation in an expenditure time series."""
    timestamp: datetime
    point_date: date
    cost: Decimal
    usage_quantity: Decimal = Decimal("0.0")
    source_record_ids: List[str] = field(default_factory=list)


@dataclass
class TimeSeries:
    """Time-series dataset aggregated across a specific dimension."""
    dimension_type: str  # PROVIDER, ACCOUNT, SERVICE, REGION, RESOURCE, SKU
    dimension_key: str
    provider: str
    account_id: Optional[str] = None
    service_category: Optional[str] = None
    service_name: Optional[str] = None
    region: Optional[str] = None
    resource_id: Optional[str] = None
    sku: Optional[str] = None
    currency: str = "USD"
    points: List[TimeSeriesPoint] = field(default_factory=list)

    @property
    def point_dates(self) -> List[date]:
        return [p.point_date for p in self.points]

    @property
    def cost_values(self) -> List[Decimal]:
        return [p.cost for p in self.points]


@dataclass
class BaselineResult:
    """Statistical baseline metrics computed over an observation window."""
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
    start_date: date
    end_date: date
    window_days: int
    status: str = "SUFFICIENT"  # SUFFICIENT, INSUFFICIENT_HISTORY, ZERO_VARIANCE


@dataclass
class AnomalyCandidate:
    """An identified cost anomaly candidate ready for attribution and persistence."""
    detector_id: str
    detector_version: str
    provider: str
    account_id: str
    service_category: str
    service_name: str
    region: str
    anomaly_date: date
    observed_cost: Decimal
    expected_cost: Decimal
    absolute_deviation: Decimal
    percentage_deviation: Decimal
    estimated_excess_cost: Decimal
    projected_monthly_impact: Decimal
    currency: str = "USD"
    resource_id: Optional[str] = None
    sku: Optional[str] = None
    anomaly_category: AnomalyCategory = AnomalyCategory.SERVICE_SPIKE
    detection_methods: List[DetectionMethod] = field(default_factory=lambda: [DetectionMethod.Z_SCORE])
    z_score: Decimal = Decimal("0.0000")
    severity: Severity = Severity.MEDIUM
    confidence_score: Decimal = Decimal("1.0000")
    title: Optional[str] = None
    explanation: Optional[str] = None
    baseline_window_days: int = 30
    observation_window_days: int = 1
    baseline_metrics: Dict[str, Any] = field(default_factory=dict)
    root_cause_analysis: Dict[str, Any] = field(default_factory=dict)
    contributing_resources: List[Dict[str, Any]] = field(default_factory=list)
    source_billing_references: List[str] = field(default_factory=list)


@dataclass
class DetectorExecutionResult:
    """Outcome of running an anomaly detector against a time series."""
    detector_id: str
    status: str  # DETECTED, CLEAN, INSUFFICIENT_DATA, ERROR
    anomalies: List[AnomalyCandidate] = field(default_factory=list)
    message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangePointResult:
    """Outcome of change-point and structural shift analysis."""
    is_change_point: bool
    change_type: str  # PERSISTENT_STEP, TEMPORARY_SPIKE, GRADUAL_ESCALATION, NONE
    change_point_date: Optional[date] = None
    baseline_mean: Decimal = Decimal("0.0000")
    post_change_mean: Decimal = Decimal("0.0000")
    shift_magnitude: Decimal = Decimal("0.0000")
    shift_percentage: Decimal = Decimal("0.0000")
    confidence: Decimal = Decimal("0.0000")
    consecutive_days_elevated: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
