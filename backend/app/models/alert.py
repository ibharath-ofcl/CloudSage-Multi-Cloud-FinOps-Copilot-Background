"""
CloudSage Alert Rules and Notification Delivery Log Models.
Manages threshold configurations and logs multi-channel notifications (Slack, Teams, Email).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import (
    Boolean,
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
from backend.app.core.enums import AlertType, NotificationChannel

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class AlertRule(Base):
    """User-configured threshold rule for budgets, cost anomalies, and waste triggers."""
    __tablename__ = "alert_rules"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    name = Column(
        String(128),
        nullable=False,
        doc="Human-readable rule name"
    )
    alert_type = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Alert trigger category (BUDGET_THRESHOLD, ANOMALY_ZSCORE, etc.)"
    )
    threshold_value = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Trigger threshold value (e.g. dollar budget, or Z-score 3.0)"
    )
    channels = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="List of dispatch destinations (Slack URLs, Emails, etc.)"
    )
    is_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Active evaluation toggle"
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Rule creation timestamp"
    )

    notifications = relationship("NotificationLog", back_populates="alert_rule")

    def __repr__(self) -> str:
        return f"<AlertRule id={self.id} name={self.name} type={self.alert_type} threshold={self.threshold_value}>"


class NotificationLog(Base):
    """Record of an outbound notification dispatched to an external channel."""
    __tablename__ = "notification_logs"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    alert_rule_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Originating alert rule"
    )
    channel = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Outbound channel (SLACK, TEAMS, EMAIL, WEBHOOK)"
    )
    recipient = Column(
        String(256),
        nullable=False,
        doc="Target webhook URL, channel name, or email"
    )
    payload = Column(
        JSON_TYPE,
        nullable=False,
        doc="Notification payload delivered"
    )
    status = Column(
        String(16),
        nullable=False,
        default="DELIVERED",
        index=True,
        doc="Delivery status (DELIVERED, FAILED)"
    )
    dispatched_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Dispatch timestamp"
    )

    alert_rule = relationship("AlertRule", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<NotificationLog id={self.id} channel={self.channel} status={self.status}>"
