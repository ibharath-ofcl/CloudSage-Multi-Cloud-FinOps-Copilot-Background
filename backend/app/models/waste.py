"""
CloudSage Waste Detection Model.
Records detected cloud waste resulting from heuristic analysis of resource utilization and billing.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from backend.app.core.database import Base
from backend.app.core.enums import Severity, WasteStatus, WasteType

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class WasteDetection(Base):
    """Identified cloud waste instance (e.g. idle compute, unattached storage)."""
    __tablename__ = "waste_detections"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    resource_id = Column(
        String(512),
        ForeignKey("cloud_resources.resource_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    provider = Column(
        String(16),
        nullable=False,
        index=True,
        doc="Cloud Provider (AWS, AZURE, GCP)"
    )
    waste_type = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Classification of waste (IDLE_VM, UNATTACHED_DISK, etc.)"
    )
    severity = Column(
        String(16),
        nullable=False,
        default=Severity.MEDIUM.value,
        index=True,
        doc="Severity level (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    status = Column(
        String(16),
        nullable=False,
        default=WasteStatus.ACTIVE.value,
        index=True,
        doc="Status (ACTIVE, SNOOZED, DISMISSED, RESOLVED)"
    )
    estimated_monthly_waste = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Estimated monthly monetary waste in USD"
    )
    telemetry_proof = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Supporting metrics (e.g. avg CPU %, network IO, attachment status)"
    )
    dismissal_reason = Column(
        String(512),
        nullable=True,
        doc="Reviewer explanation if dismissed"
    )
    dismissed_by = Column(
        String(128),
        nullable=True,
        doc="Reviewer user email / identity"
    )
    snooze_until = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Expiry timestamp if snoozed"
    )
    detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Detection timestamp"
    )

    resource = relationship("CloudResource", back_populates="waste_detections")
    recommendation = relationship("Recommendation", back_populates="waste_detection", uselist=False)

    __table_args__ = (
        Index("idx_waste_active_prov", "status", "provider"),
        Index("idx_waste_type_status", "waste_type", "status"),
    )

    def __repr__(self) -> str:
        return f"<WasteDetection id={self.id} type={self.waste_type} waste={self.estimated_monthly_waste} USD status={self.status}>"
