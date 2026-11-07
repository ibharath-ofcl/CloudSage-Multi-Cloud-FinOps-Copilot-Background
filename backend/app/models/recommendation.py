"""
CloudSage Advisory Recommendation Model.
Stores actionable, risk-scored savings recommendations with human-in-the-loop review state tracking.
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
    Text,
    Uuid,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.core.enums import (
    ImplementationEffort,
    Priority,
    RecommendationAction,
    RecommendationStatus,
    RiskLevel,
)


class Recommendation(Base):
    """
    Advisory Optimization Recommendation.
    Strictly non-destructive; tracks formal human approval lifecycle.
    """
    __tablename__ = "recommendations"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    waste_detection_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("waste_detections.id", ondelete="SET NULL"),
        nullable=True,
        doc="Originating waste detection if generated from heuristic"
    )
    resource_id = Column(
        String(512),
        ForeignKey("cloud_resources.resource_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target cloud resource ARN or URI"
    )
    provider = Column(
        String(16),
        nullable=False,
        index=True,
        doc="Cloud Provider (AWS, AZURE, GCP)"
    )
    action_type = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Recommended remediation action (TERMINATE, RIGHTSIZE, etc.)"
    )
    priority = Column(
        String(8),
        nullable=False,
        default=Priority.P2.value,
        index=True,
        doc="Priority classification (P1, P2, P3, P4)"
    )
    risk_level = Column(
        String(16),
        nullable=False,
        default=RiskLevel.LOW.value,
        index=True,
        doc="Operational risk (NONE, LOW, MEDIUM, HIGH)"
    )
    status = Column(
        String(16),
        nullable=False,
        default=RecommendationStatus.PROPOSED.value,
        index=True,
        doc="Lifecycle state (PROPOSED, UNDER_REVIEW, ENDORSED, APPROVED, DISMISSED, IMPLEMENTED)"
    )
    estimated_monthly_savings = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Projected monthly cost reduction in USD"
    )
    estimated_annual_savings = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Projected annualized cost reduction (12 * monthly)"
    )
    implementation_effort = Column(
        String(16),
        nullable=False,
        default=ImplementationEffort.LOW.value,
        doc="Estimated engineering effort (LOW, MEDIUM, HIGH)"
    )
    title = Column(
        String(256),
        nullable=False,
        doc="Summary recommendation headline"
    )
    description = Column(
        Text,
        nullable=False,
        doc="Detailed rationale and utilization justification"
    )
    remediation_guide = Column(
        Text,
        nullable=False,
        doc="Step-by-step instructions, CLI snippet, or Terraform guidance"
    )
    endorsed_by = Column(
        String(128),
        nullable=True,
        doc="Finance Analyst identity who validated ROI"
    )
    approved_by = Column(
        String(128),
        nullable=True,
        doc="FinOps / Engineering Lead who formally approved action"
    )
    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of formal approval"
    )
    implemented_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of manual implementation"
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Proposal creation timestamp"
    )

    resource = relationship("CloudResource", back_populates="recommendations")
    waste_detection = relationship("WasteDetection", back_populates="recommendation")

    __table_args__ = (
        Index("idx_rec_status_priority", "status", "priority"),
        Index("idx_rec_prov_savings", "provider", "estimated_monthly_savings"),
    )

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} action={self.action_type} savings={self.estimated_monthly_savings} USD status={self.status}>"
