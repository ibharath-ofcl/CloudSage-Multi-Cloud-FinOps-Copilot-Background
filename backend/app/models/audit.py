"""
CloudSage Immutable Audit Ledger Model.
Captures all user authentication, recommendation approvals, dismissals, and privileged operations.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from backend.app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class AuditLog(Base):
    """Immutable audit record for compliance (SOC 2 / ISO 27001)."""
    __tablename__ = "audit_logs"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Audit event timestamp"
    )
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User ID if authenticated"
    )
    user_email = Column(
        String(256),
        nullable=True,
        index=True,
        doc="User email at event time"
    )
    action_type = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Action executed (LOGIN, RECOMMENDATION_APPROVE, etc.)"
    )
    resource_type = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Target entity type (recommendation, waste, billing)"
    )
    resource_id = Column(
        String(512),
        nullable=True,
        index=True,
        doc="Target entity identifier"
    )
    before_state = Column(
        JSON_TYPE,
        nullable=True,
        doc="State prior to mutation"
    )
    after_state = Column(
        JSON_TYPE,
        nullable=True,
        doc="State following mutation"
    )
    client_ip = Column(
        String(64),
        nullable=True,
        doc="Client IP address"
    )
    status = Column(
        String(16),
        nullable=False,
        default="SUCCESS",
        doc="Outcome status (SUCCESS, FAILURE)"
    )

    __table_args__ = (
        Index("idx_audit_user_time", "user_id", "timestamp"),
        Index("idx_audit_action_time", "action_type", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action_type} user={self.user_email} status={self.status}>"
