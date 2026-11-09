"""
CloudSage Investigation and Root Cause Analysis Data Models.
Maintains persistent investigation cases, evidence findings, collaboration notes,
evidence links, and immutable state audit histories.
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional
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
    ConfidenceCategory,
    EvidenceSource,
    FindingType,
    InvestigationPriority,
    InvestigationStatus,
)

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class InvestigationCase(Base):
    """
    Persistent Investigation Workspace Case.
    Tracks root-cause triage, assigned FinOps engineer, hypotheses,
    verified causes, and resolution governance.
    """
    __tablename__ = "investigation_cases"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    case_number = Column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
        doc="Human-friendly investigation identifier (e.g. INV-2026-0001)",
    )
    anomaly_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("cost_anomalies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Originating cost anomaly being investigated",
    )
    alert_instance_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("alert_instances.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional linked alert notification instance",
    )
    title = Column(
        String(256),
        nullable=False,
        doc="Headline description of the investigation",
    )
    status = Column(
        String(32),
        nullable=False,
        default=InvestigationStatus.NEW.value,
        index=True,
        doc="Lifecycle state: NEW, ASSIGNED, INVESTIGATING, ROOT_CAUSE_IDENTIFIED, ACTION_RECOMMENDED, RESOLVED, CLOSED",
    )
    priority = Column(
        String(16),
        nullable=False,
        default=InvestigationPriority.MEDIUM.value,
        index=True,
        doc="Urgency tier: CRITICAL, HIGH, MEDIUM, LOW",
    )
    assigned_to = Column(
        String(128),
        nullable=True,
        index=True,
        doc="Assigned FinOps engineer or team owner email",
    )
    assigned_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when assignment was recorded",
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
    service_name = Column(
        String(128),
        nullable=False,
        index=True,
        doc="Cloud service name under investigation",
    )
    region = Column(
        String(64),
        nullable=True,
        doc="Geographical cloud region scope",
    )
    resource_id = Column(
        String(512),
        nullable=True,
        index=True,
        doc="Specific primary resource identifier if known",
    )
    excess_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Anomalous excess expenditure in USD",
    )
    actual_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Observed expenditure in USD",
    )
    expected_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Baseline expected expenditure in USD",
    )
    root_cause_summary = Column(
        Text,
        nullable=True,
        doc="Diagnostic summary synthesized from verified findings",
    )
    verified_root_cause = Column(
        Text,
        nullable=True,
        doc="Confirmed causal explanation once verified",
    )
    suspected_category = Column(
        String(64),
        nullable=True,
        doc="Category: USAGE_SURGE, RATE_CHANGE, CONFIGURATION_DRIFT, ORPHANED_INFRASTRUCTURE, DEPLOYMENT_SPIKE, SKU_MISCONFIGURATION",
    )
    resolution_notes = Column(
        Text,
        nullable=True,
        doc="Documented resolution rationale (mandatory for RESOLVED state)",
    )
    created_by = Column(
        String(128),
        nullable=False,
        doc="Principal who opened the investigation",
    )
    updated_by = Column(
        String(128),
        nullable=True,
        doc="Principal who last updated the case",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    closed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_by = Column(
        String(128),
        nullable=True,
    )

    # Relationships
    anomaly = relationship("CostAnomaly", backref="investigations")
    alert_instance = relationship("AlertInstance", backref="investigations")
    findings = relationship("InvestigationFinding", back_populates="investigation", cascade="all, delete-orphan")
    notes = relationship("InvestigationNote", back_populates="investigation", cascade="all, delete-orphan")
    evidence_links = relationship("InvestigationEvidenceLink", back_populates="investigation", cascade="all, delete-orphan")
    history = relationship("InvestigationHistory", back_populates="investigation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_inv_prov_status", "provider", "status"),
        Index("idx_inv_account_status", "account_id", "status"),
        Index("idx_inv_assigned", "assigned_to", "status"),
    )

    def __repr__(self) -> str:
        return f"<InvestigationCase number={self.case_number} status={self.status} excess=${self.excess_cost}>"


class InvestigationFinding(Base):
    """
    Evidence-grounded diagnostic finding.
    Distinguishes observed facts from statistical correlations, hypotheses, and verified causes.
    """
    __tablename__ = "investigation_findings"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    investigation_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("investigation_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Linked parent investigation case",
    )
    finding_type = Column(
        String(32),
        nullable=False,
        default=FindingType.FACT.value,
        index=True,
        doc="Classification: FACT, CORRELATION, HYPOTHESIS, VERIFIED_CAUSE",
    )
    title = Column(
        String(256),
        nullable=False,
        doc="Finding headline",
    )
    explanation = Column(
        Text,
        nullable=False,
        doc="Detailed factual breakdown or reasoning",
    )
    dimension = Column(
        String(64),
        nullable=True,
        doc="Attribution dimension: SERVICE, RESOURCE, SKU, REGION, USAGE, PRICING, ENVIRONMENT",
    )
    financial_impact = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Dollar share of total anomalous spend (USD)",
    )
    contribution_percentage = Column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Percentage contribution to anomaly excess spend",
    )
    confidence_category = Column(
        String(32),
        nullable=False,
        default=ConfidenceCategory.MEDIUM.value,
        index=True,
        doc="Confidence tier: HIGH, MEDIUM, LOW, INSUFFICIENT_EVIDENCE",
    )
    confidence_score = Column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("1.0000"),
        doc="Deterministic confidence score between 0.0000 and 1.0000",
    )
    evidence_source = Column(
        String(64),
        nullable=False,
        default=EvidenceSource.BILLING_RECORD.value,
        doc="Source of evidence signal: BILLING_RECORD, RESOURCE_INVENTORY, UTILIZATION_METRIC, etc.",
    )
    evidence_reference = Column(
        String(512),
        nullable=True,
        doc="Reference pointer (e.g. resource ID, billing record ID, metric name)",
    )
    supporting_observations = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="List of factual observations corroborating this finding",
    )
    contradictory_observations = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="List of missing, inconsistent, or conflicting signals",
    )
    suggested_next_step = Column(
        Text,
        nullable=True,
        doc="Actionable next step recommended for the investigation team",
    )
    created_by = Column(
        String(128),
        nullable=False,
        default="system_engine",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    investigation = relationship("InvestigationCase", back_populates="findings")

    def __repr__(self) -> str:
        return f"<InvestigationFinding type={self.finding_type} title='{self.title}' impact=${self.financial_impact}>"


class InvestigationNote(Base):
    """Collaboration notes and human analyst commentary on an active case."""
    __tablename__ = "investigation_notes"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    investigation_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("investigation_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author = Column(
        String(128),
        nullable=False,
        doc="Author email address or system principal",
    )
    content = Column(
        Text,
        nullable=False,
        doc="Analyst commentary, hypothesis, or triage update",
    )
    is_system_generated = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="True if created by background engine or copilot",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    investigation = relationship("InvestigationCase", back_populates="notes")


class InvestigationEvidenceLink(Base):
    """
    Explicit entity link between an investigation case and underlying FinOps records.
    Connects cases to resources, billing records, waste detections, and recommendations.
    """
    __tablename__ = "investigation_evidence_links"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    investigation_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("investigation_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Entity type: RESOURCE, BILLING_RECORD, WASTE_DETECTION, RECOMMENDATION, ALERT_INSTANCE",
    )
    entity_id = Column(
        String(512),
        nullable=False,
        index=True,
        doc="Primary key or identifier of the linked record",
    )
    relationship_role = Column(
        String(64),
        nullable=False,
        default="SUPPORTING_EVIDENCE",
        doc="Role: PRIMARY_DRIVER, CORRELATED_WASTE, PENDING_RECOMMENDATION, ORIGINATING_ALERT, TELEMETRY_SIGNAL",
    )
    metadata_snapshot = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Frozen attribute snapshot at time of linking",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    investigation = relationship("InvestigationCase", back_populates="evidence_links")

    __table_args__ = (
        Index("idx_inv_ev_type_id", "entity_type", "entity_id"),
    )


class InvestigationHistory(Base):
    """
    Immutable audit ledger of all investigation case transitions, assignments, and governance actions.
    """
    __tablename__ = "investigation_history"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    investigation_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("investigation_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status = Column(
        String(32),
        nullable=True,
        doc="Lifecycle state before mutation",
    )
    to_status = Column(
        String(32),
        nullable=False,
        doc="Lifecycle state after mutation",
    )
    actor = Column(
        String(128),
        nullable=False,
        doc="Server-verified authenticated principal email",
    )
    action = Column(
        String(64),
        nullable=False,
        doc="Action: CREATE, ASSIGN, TRANSITION, NOTE_ADDED, FINDING_RECORDED, CLOSE, REOPEN",
    )
    notes = Column(
        Text,
        nullable=True,
        doc="Operational commentary or justification",
    )
    details = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Metadata snapshot and parameter payload",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    investigation = relationship("InvestigationCase", back_populates="history")
