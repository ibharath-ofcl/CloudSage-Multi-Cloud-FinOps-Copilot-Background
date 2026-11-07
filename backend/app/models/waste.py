"""
CloudSage Waste Detection and Intelligence Models.
Entities for identified cloud waste instances, evidence telemetry, and detection run audit logs.
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
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from backend.app.core.database import Base
from backend.app.core.enums import Severity, WasteStatus, WasteType

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class WasteDetection(Base):
    """
    Identified cloud waste instance (e.g. idle compute, unattached storage, orphaned snapshots).
    Maintains historical telemetry proof, financial savings estimate, and human review status.
    """
    __tablename__ = "waste_detections"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    resource_id = Column(
        String(512),
        ForeignKey("cloud_resources.resource_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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
        doc="Account, Subscription, or Project ID",
    )
    resource_type = Column(
        String(64),
        nullable=True,
        doc="Canonical or native asset type",
    )
    detector_id = Column(
        String(64),
        nullable=True,
        index=True,
        doc="Identifier of the detector producing this finding",
    )
    detector_version = Column(
        String(16),
        nullable=False,
        default="1.0",
        doc="Version of detector logic",
    )
    waste_type = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Classification of waste (IDLE_VM, UNATTACHED_DISK, etc.)",
    )
    finding_title = Column(
        String(256),
        nullable=True,
        doc="Human-readable title describing the waste finding",
    )
    explanation = Column(
        Text,
        nullable=True,
        doc="Detailed rationale explaining why the resource was flagged",
    )
    severity = Column(
        String(16),
        nullable=False,
        default=Severity.MEDIUM.value,
        index=True,
        doc="Severity level (CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL)",
    )
    status = Column(
        String(32),
        nullable=False,
        default=WasteStatus.ACTIVE.value,
        index=True,
        doc="Status (ACTIVE, OPEN, ACKNOWLEDGED, SNOOZED, DISMISSED, RESOLVED, REOPENED)",
    )
    confidence_score = Column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("1.0000"),
        doc="Evidence certainty score (0.0000 to 1.0000)",
    )
    estimated_monthly_waste = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Estimated monthly monetary waste in USD",
    )
    currency = Column(
        String(8),
        nullable=False,
        default="USD",
        doc="Standardized currency (default USD)",
    )
    original_currency = Column(
        String(8),
        nullable=True,
        doc="Original billed currency before conversion",
    )
    original_cost = Column(
        Numeric(18, 4),
        nullable=True,
        doc="Original monthly expenditure in local currency",
    )
    observation_window_days = Column(
        Integer,
        nullable=False,
        default=7,
        doc="Days of continuous metric observation evaluated",
    )
    data_quality_status = Column(
        String(32),
        nullable=False,
        default="VERIFIED",
        doc="Quality status: VERIFIED, INSUFFICIENT_DATA, PARTIAL",
    )
    requires_human_review = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Strict FinOps guardrail: all remediation actions require human review",
    )
    telemetry_proof = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Supporting metrics (e.g. avg CPU %, network IO, attachment status)",
    )
    dismissal_reason = Column(
        String(512),
        nullable=True,
        doc="Reviewer explanation if dismissed",
    )
    dismissed_by = Column(
        String(128),
        nullable=True,
        doc="Reviewer user email / identity",
    )
    snooze_until = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Expiry timestamp if snoozed",
    )
    first_detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Initial detection timestamp",
    )
    last_evaluated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Latest detector evaluation timestamp",
    )
    detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Legacy detection timestamp for backward compatibility",
    )

    resource = relationship("CloudResource", back_populates="waste_detections")
    recommendation = relationship("Recommendation", back_populates="waste_detection", uselist=False)

    @property
    def estimated_monthly_savings(self) -> Decimal:
        return self.estimated_monthly_waste

    @estimated_monthly_savings.setter
    def estimated_monthly_savings(self, value: Decimal) -> None:
        self.estimated_monthly_waste = value

    __table_args__ = (
        Index("idx_waste_active_prov", "status", "provider"),
        Index("idx_waste_type_status", "waste_type", "status"),
        Index("idx_waste_detector_status", "detector_id", "status"),
        Index("idx_waste_res_type", "resource_id", "waste_type"),
    )

    def __repr__(self) -> str:
        return f"<WasteDetection id={self.id} type={self.waste_type} waste={self.estimated_monthly_waste} USD status={self.status}>"


class WasteDetectionRun(Base):
    """
    Audit log of a waste detection execution (full, provider-specific, or single detector).
    """
    __tablename__ = "waste_detection_runs"

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
    status = Column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
        doc="Status: PENDING, RUNNING, COMPLETED, PARTIAL_SUCCESS, FAILED",
    )
    total_resources_evaluated = Column(
        Integer,
        nullable=False,
        default=0,
    )
    findings_created = Column(
        Integer,
        nullable=False,
        default=0,
    )
    findings_updated = Column(
        Integer,
        nullable=False,
        default=0,
    )
    findings_unchanged = Column(
        Integer,
        nullable=False,
        default=0,
    )
    total_estimated_monthly_savings = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Sum of estimated monthly savings across active findings detected",
    )
    detector_summary = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Summary breakdown per detector",
    )
    error_details = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="Quarantined records and detector errors",
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
        Index("idx_waste_run_prov_status", "provider", "status"),
        Index("idx_waste_run_started", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<WasteDetectionRun id={self.run_id} provider={self.provider} status={self.status}>"
