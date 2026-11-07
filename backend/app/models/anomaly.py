"""
CloudSage Cost Anomaly and Baseline Data Models.
Stores statistical spending spikes, baseline distributions, change-point events,
root-cause attribution, and execution audit logs.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from backend.app.core.database import Base
from backend.app.core.enums import AnomalyCategory, AnomalyStatus, DetectionMethod, Severity

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class CostAnomaly(Base):
    """
    Statistical cost anomaly record flagged by the Cost Anomaly Detection Engine.
    Represents an unexpected spending deviation, sudden step increase, or abnormal surge.
    """
    __tablename__ = "cost_anomalies"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    detector_id = Column(
        String(64),
        nullable=False,
        default="statistical_anomaly_detector",
        index=True,
        doc="Identifier of detector producing this anomaly finding",
    )
    detector_version = Column(
        String(16),
        nullable=False,
        default="1.0.0",
        doc="Version of detector logic",
    )
    provider = Column(
        String(16),
        nullable=False,
        index=True,
        doc="Cloud Provider (AWS, AZURE, GCP)",
    )
    account_id = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Account, Subscription, or Project ID",
    )
    service_category = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Standardized service category (COMPUTE, STORAGE, DATABASE, etc.)",
    )
    service_name = Column(
        String(128),
        nullable=False,
        index=True,
        doc="Native hyperscaler service name",
    )
    region = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Cloud region",
    )
    resource_id = Column(
        String(512),
        nullable=True,
        index=True,
        doc="Specific resource identifier if anomaly is resource-scoped",
    )
    sku = Column(
        String(128),
        nullable=True,
        doc="SKU or usage type identifier",
    )
    anomaly_category = Column(
        String(64),
        nullable=False,
        default=AnomalyCategory.SERVICE_SPIKE.value,
        index=True,
        doc="Category: SERVICE_SPIKE, RESOURCE_SPIKE, PERSISTENT_STEP, NEW_SPEND, REGION_SPIKE, SKU_PRICE_CHANGE, ACCOUNT_SPIKE, USAGE_SPIKE",
    )
    title = Column(
        String(256),
        nullable=True,
        doc="Human-readable title describing the anomaly",
    )
    explanation = Column(
        Text,
        nullable=True,
        doc="Detailed evidence-backed explanation of the cost event",
    )
    anomaly_date = Column(
        Date,
        nullable=False,
        index=True,
        doc="Date on which the spending spike/step occurred",
    )
    detection_method = Column(
        String(64),
        nullable=False,
        default=DetectionMethod.Z_SCORE.value,
        index=True,
        doc="Detection method: Z_SCORE, MODIFIED_Z_SCORE, IQR, CHANGE_POINT, ENSEMBLE, NEW_SPEND",
    )
    actual_cost = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Actual observed cost on anomaly date (USD)",
    )
    expected_cost = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Expected baseline expenditure (USD)",
    )
    baseline_mean = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Trailing observation window mean (mu)",
    )
    baseline_stddev = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Trailing observation window standard deviation (sigma)",
    )
    z_score = Column(
        Numeric(8, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Standard score (Z-Score)",
    )
    spike_percentage = Column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Percentage deviation over expected baseline",
    )
    absolute_deviation = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Observed cost minus expected cost (USD)",
    )
    estimated_excess_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Estimated unbudgeted excess expenditure (USD)",
    )
    projected_monthly_impact = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Projected 30-day financial impact if anomaly persists (USD)",
    )
    currency = Column(
        String(3),
        nullable=False,
        default="USD",
        doc="Reporting currency (USD)",
    )
    baseline_window_days = Column(
        Integer,
        nullable=False,
        default=30,
        doc="Number of historical days evaluated in baseline window",
    )
    observation_window_days = Column(
        Integer,
        nullable=False,
        default=1,
        doc="Number of days in current evaluation interval",
    )
    severity = Column(
        String(16),
        nullable=False,
        default=Severity.MEDIUM.value,
        index=True,
        doc="Anomaly severity (LOW, MEDIUM, HIGH, CRITICAL)",
    )
    status = Column(
        String(32),
        nullable=False,
        default=AnomalyStatus.OPEN.value,
        index=True,
        doc="Status: OPEN, ACKNOWLEDGED, INVESTIGATING, RESOLVED, DISMISSED, REOPENED, FALSE_POSITIVE",
    )
    confidence_score = Column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("1.0000"),
        doc="Evidence certainty score (0.0000 to 1.0000)",
    )
    baseline_metrics = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Full statistical baseline parameters (mean, median, MAD, Q1, Q3, IQR, etc.)",
    )
    root_cause_analysis = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Root cause attribution breakdown (primary driver, SKU change, usage change)",
    )
    contributing_resources = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="Ranked list of specific resources driving this cost deviation",
    )
    source_billing_references = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="Identifiers of source billing records substantiating this anomaly",
    )
    dismissal_reason = Column(
        String(512),
        nullable=True,
        doc="Reviewer justification for dismissal",
    )
    dismissed_by = Column(
        String(128),
        nullable=True,
        doc="User or service principal who dismissed the finding",
    )
    resolution_reason = Column(
        String(512),
        nullable=True,
        doc="Explanation of how the anomaly was resolved",
    )
    resolved_by = Column(
        String(128),
        nullable=True,
        doc="User or service principal who resolved the finding",
    )
    investigation_notes = Column(
        Text,
        nullable=True,
        doc="Ongoing notes from FinOps team investigation",
    )
    first_detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp when anomaly was first identified",
    )
    last_detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp when anomaly was most recently evaluated",
    )
    detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Legacy detection timestamp for backward compatibility",
    )
    reopened_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when a previously resolved/dismissed anomaly was reopened",
    )

    @property
    def observed_cost(self) -> Decimal:
        return self.actual_cost

    @observed_cost.setter
    def observed_cost(self, value: Decimal) -> None:
        self.actual_cost = value

    @property
    def percentage_deviation(self) -> Decimal:
        return self.spike_percentage

    @percentage_deviation.setter
    def percentage_deviation(self, value: Decimal) -> None:
        self.spike_percentage = value

    @property
    def deviation(self) -> Decimal:
        return self.absolute_deviation

    @property
    def anomaly_id(self):
        return self.id

    __table_args__ = (
        Index("idx_anomaly_status_date", "status", "anomaly_date"),
        Index("idx_anomaly_prov_service", "provider", "service_name", "anomaly_date"),
        Index("idx_anomaly_cat_severity", "anomaly_category", "severity"),
        Index("idx_anomaly_dedup", "provider", "account_id", "service_name", "resource_id", "anomaly_date", "anomaly_category"),
    )

    @property
    def baseline_id(self):
        return self.id

    def __repr__(self) -> str:
        return (
            f"<CostAnomaly id={self.id} service={self.service_name} "
            f"actual={self.actual_cost} expected={self.expected_cost} USD status={self.status}>"
        )


class CostBaseline(Base):
    """
    Rolling statistical baseline distribution computed across a specific dimension
    (Provider, Account, Service, Region, Resource, Cost Center, or Project).
    """
    __tablename__ = "cost_baselines"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    dimension_type = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Dimension category: PROVIDER, ACCOUNT, SERVICE, REGION, RESOURCE, COST_CENTER, PROJECT",
    )
    dimension_key = Column(
        String(512),
        nullable=False,
        index=True,
        doc="Unique composite dimension identifier (e.g., AWS/112233445566/AmazonEC2)",
    )
    provider = Column(
        String(16),
        nullable=False,
        index=True,
        doc="Cloud Provider (AWS, AZURE, GCP)",
    )
    account_id = Column(
        String(64),
        nullable=True,
        index=True,
        doc="Cloud account, subscription, or project ID",
    )
    service_name = Column(
        String(128),
        nullable=True,
        index=True,
        doc="Cloud service name",
    )
    region = Column(
        String(64),
        nullable=True,
        doc="Cloud region",
    )
    resource_id = Column(
        String(512),
        nullable=True,
        index=True,
        doc="Cloud resource ID if baseline is resource-scoped",
    )
    window_days = Column(
        Integer,
        nullable=False,
        default=30,
        doc="Observation span in days (7, 14, 30, 60, 90)",
    )
    start_date = Column(
        Date,
        nullable=False,
        doc="Earliest observation date included in baseline",
    )
    end_date = Column(
        Date,
        nullable=False,
        doc="Latest observation date included in baseline",
    )
    mean = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Arithmetic mean daily expenditure (USD)",
    )
    stddev = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Sample standard deviation (USD)",
    )
    median = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Median daily expenditure (USD)",
    )
    mad = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Median Absolute Deviation (MAD) (USD)",
    )
    q1 = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="First quartile (25th percentile) (USD)",
    )
    q3 = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Third quartile (75th percentile) (USD)",
    )
    iqr = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Interquartile Range (Q3 - Q1) (USD)",
    )
    min_value = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Minimum daily expenditure observed (USD)",
    )
    max_value = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Maximum daily expenditure observed (USD)",
    )
    sample_count = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Total number of daily samples aggregated",
    )
    zero_count = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of zero-spend days in baseline window",
    )
    currency = Column(
        String(3),
        nullable=False,
        default="USD",
        doc="Standardized currency",
    )
    version = Column(
        String(16),
        nullable=False,
        default="1.0",
        doc="Baseline calculation version",
    )
    calculated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Timestamp when baseline was generated",
    )

    __table_args__ = (
        Index("idx_baseline_dim_key_window", "dimension_key", "window_days"),
        Index("idx_baseline_prov_svc", "provider", "service_name"),
    )

    @property
    def baseline_id(self):
        return self.id

    def __repr__(self) -> str:
        return f"<CostBaseline key={self.dimension_key} mean={self.mean} stddev={self.stddev} window={self.window_days}d>"


class AnomalyDetectionRun(Base):
    """
    Execution audit log for an anomaly detection run (full, provider-specific, or scoped).
    """
    __tablename__ = "anomaly_detection_runs"

    run_id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    provider = Column(
        String(16),
        nullable=False,
        default="ALL",
        index=True,
        doc="Cloud Provider (AWS, AZURE, GCP, or ALL)",
    )
    scope = Column(
        String(64),
        nullable=False,
        default="FULL",
        doc="Scan scope (FULL, PROVIDER, SERVICE, ACCOUNT, RESOURCE, DATE_RANGE)",
    )
    status = Column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
        doc="Status: PENDING, RUNNING, COMPLETED, PARTIAL_SUCCESS, FAILED",
    )
    total_series_evaluated = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Total number of distinct time series evaluated",
    )
    baselines_generated = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of statistical baselines generated or refreshed",
    )
    anomalies_created = Column(
        Integer,
        nullable=False,
        default=0,
        doc="New anomaly findings detected",
    )
    anomalies_updated = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Existing active anomalies updated with refreshed evidence",
    )
    anomalies_unchanged = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Anomalies reviewed or snoozed left unchanged",
    )
    anomalies_resolved = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Anomalies resolved due to return to baseline",
    )
    total_excess_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Total estimated excess unbudgeted expenditure identified (USD)",
    )
    detector_summary = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Summary statistics per detector heuristic",
    )
    error_details = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="Structured error logs and execution exceptions",
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Execution start timestamp",
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Execution completion timestamp",
    )

    __table_args__ = (
        Index("idx_anomaly_run_prov_status", "provider", "status"),
        Index("idx_anomaly_run_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<AnomalyDetectionRun id={self.run_id} provider={self.provider} status={self.status} anomalies={self.anomalies_created}>"
