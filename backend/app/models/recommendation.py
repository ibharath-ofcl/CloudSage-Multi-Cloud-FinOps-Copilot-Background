"""
CloudSage Advisory Recommendation Model.
Stores actionable, risk-scored savings recommendations with human-in-the-loop review state tracking,
evidence links, execution audit logs, and status history.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from backend.app.core.database import Base
from backend.app.core.enums import (
    ImplementationEffort,
    Priority,
    RecommendationAction,
    RecommendationStatus,
    RiskLevel,
)

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Recommendation(Base):
    """
    Advisory Optimization Recommendation.
    Strictly non-destructive; tracks formal human approval lifecycle and traceable evidence.
    """
    __tablename__ = "recommendations"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    recommendation_key = Column(
        String(256),
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        index=True,
        doc="Deterministic composite deduplication key",
    )
    waste_detection_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("waste_detections.id", ondelete="SET NULL"),
        nullable=True,
        doc="Originating waste detection if generated from heuristic",
    )
    resource_id = Column(
        String(512),
        ForeignKey("cloud_resources.resource_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Target cloud resource ARN or URI (nullable for account/service-level advisories)",
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
        doc="Cloud Account / Subscription / Project ID",
    )
    region = Column(
        String(64),
        nullable=True,
        index=True,
        doc="Cloud Region",
    )
    service_name = Column(
        String(128),
        nullable=True,
        index=True,
        doc="Native hyperscaler service name",
    )
    service_category = Column(
        String(32),
        nullable=True,
        index=True,
        doc="Standardized service category (COMPUTE, STORAGE, DATABASE, etc.)",
    )
    resource_name = Column(
        String(256),
        nullable=True,
        doc="Human-readable resource name",
    )
    strategy_id = Column(
        String(64),
        nullable=False,
        default="advisory_strategy",
        index=True,
        doc="Identifier of strategy that generated recommendation",
    )
    strategy_version = Column(
        String(16),
        nullable=False,
        default="1.0",
        doc="Version of strategy logic",
    )
    action_type = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Recommended remediation action (TERMINATE, RIGHTSIZE, etc.)",
    )
    priority = Column(
        String(8),
        nullable=False,
        default=Priority.P2.value,
        index=True,
        doc="Priority classification (P1, P2, P3, P4)",
    )
    priority_score = Column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("0.5000"),
        doc="Normalized composite priority score (0.0000 - 1.0000)",
    )
    risk_level = Column(
        String(16),
        nullable=False,
        default=RiskLevel.LOW.value,
        index=True,
        doc="Operational risk (NONE, LOW, MEDIUM, HIGH, CRITICAL)",
    )
    risk_score = Column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("0.2000"),
        doc="Normalized risk score (0.0000 - 1.0000)",
    )
    confidence_score = Column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("1.0000"),
        doc="Evidence certainty score (0.0000 - 1.0000)",
    )
    status = Column(
        String(32),
        nullable=False,
        default=RecommendationStatus.PROPOSED.value,
        index=True,
        doc="Lifecycle state (PROPOSED, UNDER_REVIEW, ENDORSED, APPROVED, ACCEPTED, IN_PROGRESS, IMPLEMENTED, VERIFIED, DISMISSED, REJECTED, EXPIRED, REOPENED)",
    )
    current_monthly_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Current baseline monthly expenditure in USD",
    )
    projected_monthly_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Projected post-implementation monthly cost in USD",
    )
    estimated_monthly_savings = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Projected monthly cost reduction in USD",
    )
    estimated_annual_savings = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Projected annualized cost reduction (12 * monthly)",
    )
    verified_savings = Column(
        Numeric(18, 4),
        nullable=True,
        doc="Post-implementation measured savings in USD",
    )
    currency = Column(
        String(3),
        nullable=False,
        default="USD",
        doc="Standardized currency (USD)",
    )
    implementation_effort = Column(
        String(16),
        nullable=False,
        default=ImplementationEffort.LOW.value,
        doc="Estimated engineering effort (QUICK_WIN, LOW, MEDIUM, HIGH, COMPLEX)",
    )
    title = Column(
        String(256),
        nullable=False,
        doc="Summary recommendation headline",
    )
    description = Column(
        Text,
        nullable=False,
        doc="Detailed rationale and utilization justification",
    )
    remediation_guide = Column(
        Text,
        nullable=False,
        doc="Step-by-step instructions, CLI snippet, or Terraform guidance",
    )
    savings_calculation = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Detailed breakdown of savings formulas, hourly rates, discount models",
    )
    implementation_guidance = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Structured CLI, Terraform, rollback, prerequisites, and safety alerts",
    )
    assumptions = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="Documented assumptions made in savings projections",
    )
    evidence_summary = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Consolidated metrics and findings summary",
    )
    tags = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Owner, Environment, Project, CostCenter tags",
    )
    endorsed_by = Column(
        String(128),
        nullable=True,
        doc="Finance Analyst identity who validated ROI",
    )
    approved_by = Column(
        String(128),
        nullable=True,
        doc="FinOps / Engineering Lead who formally approved action",
    )
    review_reason = Column(
        String(512),
        nullable=True,
        doc="Rejection, dismissal, or review justification",
    )
    reviewed_by = Column(
        String(128),
        nullable=True,
        doc="Reviewer identity",
    )
    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of formal approval",
    )
    accepted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when recommendation was accepted",
    )
    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of review/rejection/dismissal",
    )
    implemented_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of manual implementation",
    )
    verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when realized savings were measured/verified",
    )
    expiry_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp after which recommendation expires if unacted",
    )
    snooze_until = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp until recommendation is snoozed from triage",
    )
    assigned_to = Column(
        String(128),
        nullable=True,
        index=True,
        doc="Assigned owner or engineering lead",
    )
    external_ticket_ref = Column(
        String(128),
        nullable=True,
        index=True,
        doc="Jira / ServiceNow / Linear ticket reference",
    )
    revised_monthly_savings = Column(
        Numeric(18, 4),
        nullable=True,
        doc="Governance-approved revised monthly savings",
    )
    is_savings_overridden = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="True if savings were modified and approved via governance workflow",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Proposal creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="Last modification timestamp",
    )

    resource = relationship("CloudResource", back_populates="recommendations")
    waste_detection = relationship("WasteDetection", back_populates="recommendation")
    evidence_items = relationship(
        "RecommendationEvidence",
        back_populates="recommendation",
        cascade="all, delete-orphan",
    )
    history_items = relationship(
        "RecommendationHistory",
        back_populates="recommendation",
        cascade="all, delete-orphan",
    )
    savings_overrides = relationship(
        "RecommendationSavingsOverride",
        back_populates="recommendation",
        cascade="all, delete-orphan",
    )

    @property
    def dismissal_reason(self) -> Optional[str]:
        return self.review_reason

    @dismissal_reason.setter
    def dismissal_reason(self, value: Optional[str]) -> None:
        self.review_reason = value

    __table_args__ = (
        Index("idx_rec_status_priority", "status", "priority"),
        Index("idx_rec_prov_savings", "provider", "estimated_monthly_savings"),
        Index("idx_rec_strategy_status", "strategy_id", "status"),
        Index("idx_rec_key", "recommendation_key"),
    )

    def __repr__(self) -> str:
        return (
            f"<Recommendation id={self.id} action={self.action_type} "
            f"savings={self.estimated_monthly_savings} USD status={self.status}>"
        )


class RecommendationEvidence(Base):
    """
    Evidence item supporting an optimization recommendation.
    Links telemetry metrics, waste detection findings, cost anomalies, or billing records.
    """
    __tablename__ = "recommendation_evidence"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    recommendation_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_type = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Type of evidence: WASTE_DETECTION, COST_ANOMALY, METRIC_SERIES, BILLING_RECORD, INVENTORY_RELATIONSHIP",
    )
    waste_detection_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("waste_detections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    anomaly_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("cost_anomalies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resource_id = Column(
        String(512),
        nullable=True,
        index=True,
    )
    description = Column(
        Text,
        nullable=False,
        doc="Readable explanation of evidence",
    )
    telemetry_data = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Metrics, baseline stats, or configuration snapshot",
    )
    billing_record_ids = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="List of associated billing record UUIDs",
    )
    confidence_score = Column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("1.0000"),
        doc="Certainty of this specific evidence item",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    recommendation = relationship("Recommendation", back_populates="evidence_items")

    __table_args__ = (
        Index("idx_rec_ev_rec_type", "recommendation_id", "evidence_type"),
    )

    def __repr__(self) -> str:
        return f"<RecommendationEvidence id={self.id} type={self.evidence_type}>"


class RecommendationHistory(Base):
    """
    Audit log of status changes and user actions on a recommendation.
    """
    __tablename__ = "recommendation_history"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    recommendation_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status = Column(
        String(32),
        nullable=True,
    )
    to_status = Column(
        String(32),
        nullable=False,
    )
    actor = Column(
        String(128),
        nullable=False,
        doc="User or service identity making the change",
    )
    action = Column(
        String(64),
        nullable=False,
        doc="STATUS_CHANGE, FEEDBACK, ENDORSEMENT, APPROVAL, IMPLEMENTATION, VERIFICATION",
    )
    notes = Column(
        Text,
        nullable=True,
        doc="Justification or feedback notes",
    )
    details = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Detailed metadata or audit payload",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    recommendation = relationship("Recommendation", back_populates="history_items")

    __table_args__ = (
        Index("idx_rec_hist_rec_time", "recommendation_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<RecommendationHistory id={self.id} from={self.from_status} to={self.to_status} actor={self.actor}>"


class RecommendationRun(Base):
    """
    Audit log of a recommendation generation execution run.
    """
    __tablename__ = "recommendation_runs"

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
        doc="Execution scope: FULL, PROVIDER, SERVICE, STRATEGY, ACCOUNT",
    )
    status = Column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
        doc="Status: PENDING, RUNNING, COMPLETED, PARTIAL_SUCCESS, FAILED",
    )
    total_evaluated = Column(
        Integer,
        nullable=False,
        default=0,
    )
    recommendations_created = Column(
        Integer,
        nullable=False,
        default=0,
    )
    recommendations_updated = Column(
        Integer,
        nullable=False,
        default=0,
    )
    recommendations_unchanged = Column(
        Integer,
        nullable=False,
        default=0,
    )
    recommendations_suppressed = Column(
        Integer,
        nullable=False,
        default=0,
    )
    total_monthly_savings = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Total active monthly savings generated in run (USD)",
    )
    total_annual_savings = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Total active annualized savings generated in run (USD)",
    )
    strategy_summary = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Summary statistics per strategy",
    )
    error_details = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="Errors and suppressed candidate logs",
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_rec_run_prov_status", "provider", "status"),
        Index("idx_rec_run_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<RecommendationRun id={self.run_id} status={self.status} savings={self.total_monthly_savings}>"


class RecommendationSavingsOverride(Base):
    """
    Formal governance audit record for proposing and approving revised monthly savings
    on an optimization recommendation, supporting human-in-the-loop dual control.
    """
    __tablename__ = "recommendation_savings_overrides"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    recommendation_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_monthly_savings = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Original algorithmic monthly savings projection in USD",
    )
    proposed_monthly_savings = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Proposed revised monthly savings projection in USD",
    )
    reason = Column(
        Text,
        nullable=False,
        doc="Engineering / FinOps justification for manual override",
    )
    proposed_by = Column(
        String(128),
        nullable=False,
        doc="Identity of engineer/analyst proposing the adjustment",
    )
    approved_by = Column(
        String(128),
        nullable=True,
        doc="Identity of FinOps manager/lead who reviewed and approved/rejected",
    )
    status = Column(
        String(32),
        nullable=False,
        default="PROPOSED",
        index=True,
        doc="Governance status: PROPOSED, APPROVED, REJECTED",
    )
    rejection_reason = Column(
        Text,
        nullable=True,
        doc="Explanation if the proposed override was rejected",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of approval or rejection",
    )

    recommendation = relationship("Recommendation", back_populates="savings_overrides")

    __table_args__ = (
        Index("idx_rec_override_rec_status", "recommendation_id", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<RecommendationSavingsOverride id={self.id} rec_id={self.recommendation_id} "
            f"orig={self.original_monthly_savings} proposed={self.proposed_monthly_savings} status={self.status}>"
        )
