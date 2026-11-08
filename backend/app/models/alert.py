"""
CloudSage Alert Rules, Alert Instances, and Notification Delivery Hub Models.
Manages enterprise threshold configurations, multi-cloud anomaly alerts,
transactional outbox delivery, in-app notification center, and user preferences.
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
    AlertStatus,
    AlertType,
    NotificationChannel,
    NotificationDeliveryStatus,
    Severity,
)

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class AlertRule(Base):
    """
    Enterprise user-configured threshold rule for cost anomalies and budget triggers.
    Supports multi-dimensional scoping across provider, account, service, region,
    severity tiers, and financial deviation thresholds.
    """
    __tablename__ = "alert_rules"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name = Column(
        String(128),
        nullable=False,
        doc="Human-readable rule name",
    )
    description = Column(
        String(512),
        nullable=True,
        doc="Operational context or purpose of alert rule",
    )
    alert_type = Column(
        String(32),
        nullable=False,
        default=AlertType.ANOMALY_ZSCORE.value,
        index=True,
        doc="Alert trigger category (ANOMALY_ZSCORE, BUDGET_THRESHOLD, etc.)",
    )
    provider = Column(
        String(16),
        nullable=False,
        default="ALL",
        index=True,
        doc="Cloud Provider scope: AWS, AZURE, GCP, or ALL",
    )
    account_id = Column(
        String(64),
        nullable=True,
        index=True,
        doc="Specific account, subscription, or project ID scope",
    )
    region = Column(
        String(64),
        nullable=True,
        doc="Specific cloud region scope (e.g. us-east-1)",
    )
    service_name = Column(
        String(128),
        nullable=True,
        doc="Hyperscaler service name scope (e.g. Amazon Elastic Compute Cloud)",
    )
    environment = Column(
        String(64),
        nullable=True,
        doc="Environment tag scope (e.g. production, staging)",
    )
    owner = Column(
        String(128),
        nullable=True,
        doc="Owner email or team scope",
    )
    cost_center = Column(
        String(64),
        nullable=True,
        doc="Cost center identifier scope",
    )
    min_severity = Column(
        String(16),
        nullable=False,
        default=Severity.MEDIUM.value,
        index=True,
        doc="Minimum severity required to trigger (LOW, MEDIUM, HIGH, CRITICAL)",
    )
    threshold_value = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Primary trigger threshold value (e.g. Z-score 3.0 or dollar amount)",
    )
    min_excess_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Minimum anomalous excess cost in USD required to trigger",
    )
    percentage_deviation_threshold = Column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Minimum percentage deviation over baseline required to trigger",
    )
    absolute_deviation_threshold = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Minimum absolute cost deviation over baseline required to trigger",
    )
    anomaly_category = Column(
        String(64),
        nullable=True,
        doc="Specific anomaly category trigger (e.g. SERVICE_SPIKE, RESOURCE_SPIKE)",
    )
    channels = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="List of enabled notification channels: ['IN_APP', 'EMAIL', 'WEBHOOK']",
    )
    recipients = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="List of target recipients (emails, webhook URLs, user IDs)",
    )
    cooldown_minutes = Column(
        Integer,
        nullable=False,
        default=1440,
        doc="Cooldown window in minutes to prevent duplicate alert fatigue (default 24h)",
    )
    escalation_policy = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Escalation tiers, escalation delay in minutes, and escalation targets",
    )
    is_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        doc="Active rule evaluation toggle",
    )
    is_archived = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Soft-delete / archival flag",
    )
    created_by = Column(
        String(128),
        nullable=False,
        default="system",
        doc="User or service principal who created the rule",
    )
    updated_by = Column(
        String(128),
        nullable=True,
        doc="User who last updated the rule",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Rule creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="Rule last updated timestamp",
    )

    # Relationships
    notifications = relationship("NotificationLog", back_populates="alert_rule")
    alert_instances = relationship("AlertInstance", back_populates="alert_rule")

    def __repr__(self) -> str:
        return f"<AlertRule id={self.id} name={self.name} provider={self.provider} enabled={self.is_enabled}>"


class AlertInstance(Base):
    """
    Materialized alert instance connecting an anomaly event to a matched alert rule.
    Maintains complete operational lifecycle state:
    OPEN -> ACKNOWLEDGED -> INVESTIGATING -> RESOLVED -> SUPPRESSED -> CLOSED.
    """
    __tablename__ = "alert_instances"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    alert_rule_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Matched originating alert rule",
    )
    anomaly_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("cost_anomalies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Underlying cost anomaly source of truth",
    )
    dedup_key = Column(
        String(256),
        nullable=False,
        index=True,
        doc="Deterministic deduplication identity string",
    )
    title = Column(
        String(256),
        nullable=False,
        doc="Alert headline summary",
    )
    severity = Column(
        String(16),
        nullable=False,
        default=Severity.MEDIUM.value,
        index=True,
        doc="Current alert severity tier (LOW, MEDIUM, HIGH, CRITICAL)",
    )
    current_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Observed daily spend at time of trigger (USD)",
    )
    expected_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Baseline expected expenditure (USD)",
    )
    excess_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Anomalous excess expenditure (USD)",
    )
    percentage_deviation = Column(
        Numeric(8, 2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Observed percentage deviation over baseline",
    )
    status = Column(
        String(32),
        nullable=False,
        default=AlertStatus.OPEN.value,
        index=True,
        doc="Lifecycle state (OPEN, ACKNOWLEDGED, INVESTIGATING, RESOLVED, SUPPRESSED, CLOSED)",
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
        doc="Cloud Account or Subscription ID",
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
        doc="Cloud region",
    )
    resource_id = Column(
        String(512),
        nullable=True,
        index=True,
        doc="Target resource ARN or identifier if resource-scoped",
    )
    acknowledged_by = Column(
        String(128),
        nullable=True,
        doc="Actor who acknowledged the alert",
    )
    acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when alert was acknowledged",
    )
    investigated_by = Column(
        String(128),
        nullable=True,
        doc="Actor currently leading the investigation",
    )
    investigation_notes = Column(
        Text,
        nullable=True,
        doc="Ongoing notes and findings from engineering triage",
    )
    ticket_ref = Column(
        String(128),
        nullable=True,
        doc="External ITSM ticket reference (e.g. FINOPS-1092, JIRA-842)",
    )
    resolved_by = Column(
        String(128),
        nullable=True,
        doc="Actor who resolved the alert",
    )
    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Resolution timestamp",
    )
    resolution_notes = Column(
        Text,
        nullable=True,
        doc="Mandatory justification and root-cause resolution explanation",
    )
    suppressed_by = Column(
        String(128),
        nullable=True,
        doc="Actor who initiated alert suppression",
    )
    suppress_reason = Column(
        Text,
        nullable=True,
        doc="Operational reason for alert suppression",
    )
    suppress_until = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Expiration timestamp of temporary suppression window",
    )
    trigger_count = Column(
        Integer,
        nullable=False,
        default=1,
        doc="Number of times this anomaly matched during cooldown without re-alerting",
    )
    first_triggered_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp of initial trigger event",
    )
    last_triggered_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp of most recent evaluation match",
    )
    escalation_level = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Current escalation tier reached",
    )
    last_escalated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of most recent severity escalation",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Alert record creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="Alert record last update timestamp",
    )

    # Relationships
    alert_rule = relationship("AlertRule", back_populates="alert_instances")
    anomaly = relationship("CostAnomaly")
    history = relationship("AlertHistory", back_populates="alert_instance", cascade="all, delete-orphan")
    outbox_items = relationship("NotificationOutbox", back_populates="alert_instance", cascade="all, delete-orphan")
    in_app_notifications = relationship("InAppNotification", back_populates="alert_instance", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<AlertInstance id={self.id} status={self.status} severity={self.severity} excess={self.excess_cost}>"


class NotificationOutbox(Base):
    """
    Transactional outbox for reliable asynchronous notification delivery.
    Guarantees at-least-once dispatch, retry backoff, and dead-letter queue isolation.
    """
    __tablename__ = "notification_outbox"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    alert_instance_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("alert_instances.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Originating alert instance",
    )
    channel = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Outbound channel: IN_APP, EMAIL, WEBHOOK, SLACK, TEAMS",
    )
    recipient = Column(
        String(256),
        nullable=False,
        doc="Destination email, webhook URL, or user ID",
    )
    subject = Column(
        String(256),
        nullable=False,
        doc="Subject line or notification title",
    )
    payload = Column(
        JSON_TYPE,
        nullable=False,
        doc="Structured notification JSON payload",
    )
    status = Column(
        String(32),
        nullable=False,
        default=NotificationDeliveryStatus.PENDING.value,
        index=True,
        doc="Delivery status: PENDING, PROCESSING, SENT, DELIVERED, FAILED, RETRYING, DEAD_LETTERED, CANCELLED",
    )
    attempts = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of dispatch attempts executed",
    )
    max_attempts = Column(
        Integer,
        nullable=False,
        default=5,
        doc="Maximum permitted dispatch attempts before dead-lettering",
    )
    next_attempt_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Scheduled timestamp for next delivery attempt",
    )
    last_attempt_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of most recent attempt",
    )
    last_error = Column(
        Text,
        nullable=True,
        doc="Sanitized error description from last failed attempt",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Outbox entry creation timestamp",
    )
    delivered_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when delivery was successfully executed",
    )

    # Relationships
    alert_instance = relationship("AlertInstance", back_populates="outbox_items")
    delivery_attempts = relationship("NotificationDeliveryAttempt", back_populates="outbox", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<NotificationOutbox id={self.id} channel={self.channel} status={self.status} attempts={self.attempts}>"


class NotificationDeliveryAttempt(Base):
    """
    Detailed audit log for every individual notification dispatch attempt.
    Captures latency, response code, and error diagnostics.
    """
    __tablename__ = "notification_delivery_attempts"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    outbox_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("notification_outbox.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent outbox entry",
    )
    attempt_number = Column(
        Integer,
        nullable=False,
        doc="Sequential attempt number (1, 2, 3...)",
    )
    channel = Column(
        String(32),
        nullable=False,
        doc="Channel used for this attempt",
    )
    recipient = Column(
        String(256),
        nullable=False,
        doc="Target recipient",
    )
    status = Column(
        String(16),
        nullable=False,
        doc="Outcome: SUCCESS, FAILED",
    )
    response_code = Column(
        Integer,
        nullable=True,
        doc="HTTP response status code or SMTP return code",
    )
    response_body = Column(
        Text,
        nullable=True,
        doc="Sanitized response snippet or provider message ID",
    )
    latency_ms = Column(
        Integer,
        nullable=True,
        doc="Round-trip dispatch latency in milliseconds",
    )
    error_message = Column(
        Text,
        nullable=True,
        doc="Detailed error traceback or failure reason",
    )
    attempted_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp when attempt occurred",
    )

    outbox = relationship("NotificationOutbox", back_populates="delivery_attempts")

    def __repr__(self) -> str:
        return f"<NotificationDeliveryAttempt outbox_id={self.outbox_id} attempt={self.attempt_number} status={self.status}>"


class InAppNotification(Base):
    """
    In-app notification center feed item.
    Enables unread count badges, notification dropdowns, and read/unread triage.
    """
    __tablename__ = "in_app_notifications"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    alert_instance_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("alert_instances.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Linked alert instance",
    )
    recipient_user_id = Column(
        String(128),
        nullable=False,
        default="ALL",
        index=True,
        doc="User email / ID or 'ALL' for tenant-wide broadcasts",
    )
    title = Column(
        String(256),
        nullable=False,
        doc="Notification headline",
    )
    message = Column(
        Text,
        nullable=False,
        doc="Notification body text and context",
    )
    severity = Column(
        String(16),
        nullable=False,
        default=Severity.MEDIUM.value,
        index=True,
        doc="Severity tier (LOW, MEDIUM, HIGH, CRITICAL)",
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
        doc="Cloud account / subscription ID",
    )
    service_name = Column(
        String(128),
        nullable=False,
        doc="Hyperscaler service name",
    )
    excess_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Anomalous excess cost in USD",
    )
    is_read = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Read/unread indicator",
    )
    read_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when marked read",
    )
    action_url = Column(
        String(256),
        nullable=True,
        doc="Frontend route to investigate alert",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Notification creation timestamp",
    )

    alert_instance = relationship("AlertInstance", back_populates="in_app_notifications")

    def __repr__(self) -> str:
        return f"<InAppNotification id={self.id} read={self.is_read} severity={self.severity}>"


class NotificationPreference(Base):
    """
    User-level notification routing preferences.
    Configures preferred channels, minimum severity, quiet hours, and digest cadence.
    """
    __tablename__ = "notification_preferences"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id = Column(
        String(128),
        nullable=True,
        index=True,
        doc="User unique ID identifier",
    )
    user_email = Column(
        String(256),
        unique=True,
        nullable=False,
        index=True,
        doc="User email address identifier",
    )
    enabled_channels = Column(
        JSON_TYPE,
        nullable=False,
        default=lambda: ["IN_APP", "EMAIL"],
        doc="User-approved delivery channels",
    )
    min_severity = Column(
        String(16),
        nullable=False,
        default=Severity.LOW.value,
        doc="Minimum severity for outbound notifications (LOW, MEDIUM, HIGH, CRITICAL)",
    )
    receive_digests = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether user accepts periodic digests",
    )
    digest_frequency = Column(
        String(16),
        nullable=False,
        default="DAILY",
        doc="Cadence: DAILY, WEEKLY, NONE",
    )
    quiet_hours_enabled = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether non-critical notifications are suppressed during quiet hours",
    )
    quiet_hours_start_utc = Column(
        String(8),
        nullable=True,
        default="22:00",
        doc="Quiet hours window start time in UTC (HH:MM)",
    )
    quiet_hours_end_utc = Column(
        String(8),
        nullable=True,
        default="08:00",
        doc="Quiet hours window end time in UTC (HH:MM)",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Preference creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        doc="Preference update timestamp",
    )

    def __repr__(self) -> str:
        return f"<NotificationPreference email={self.user_email} channels={self.enabled_channels}>"


class AlertHistory(Base):
    """
    Immutable audit ledger of all alert state transitions and governance actions.
    Records transition actor, timestamp, action type, and justification notes.
    """
    __tablename__ = "alert_history"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    alert_instance_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("alert_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Linked alert instance",
    )
    from_status = Column(
        String(32),
        nullable=True,
        doc="Previous lifecycle status",
    )
    to_status = Column(
        String(32),
        nullable=False,
        doc="New lifecycle status",
    )
    actor = Column(
        String(128),
        nullable=False,
        doc="Authenticated user or system principal who executed the transition",
    )
    action = Column(
        String(64),
        nullable=False,
        doc="Action executed: ACKNOWLEDGE, INVESTIGATE, RESOLVE, SUPPRESS, ESCALATE, REOPEN, CLOSE",
    )
    notes = Column(
        Text,
        nullable=True,
        doc="Human or automated commentary / justification",
    )
    details = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Contextual metadata or parameter snapshot",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Audit entry creation timestamp",
    )

    alert_instance = relationship("AlertInstance", back_populates="history")

    def __repr__(self) -> str:
        return f"<AlertHistory alert_id={self.alert_instance_id} {self.from_status}->{self.to_status} by {self.actor}>"


class NotificationLog(Base):
    """
    Historical record of an outbound notification dispatched to an external channel.
    Maintained for backward compatibility with earlier stages.
    """
    __tablename__ = "notification_logs"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    alert_rule_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Originating alert rule",
    )
    channel = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Outbound channel (SLACK, TEAMS, EMAIL, WEBHOOK, IN_APP)",
    )
    recipient = Column(
        String(256),
        nullable=False,
        doc="Target webhook URL, channel name, or email",
    )
    payload = Column(
        JSON_TYPE,
        nullable=False,
        doc="Notification payload delivered",
    )
    status = Column(
        String(16),
        nullable=False,
        default="DELIVERED",
        index=True,
        doc="Delivery status (DELIVERED, FAILED)",
    )
    dispatched_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Dispatch timestamp",
    )

    alert_rule = relationship("AlertRule", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<NotificationLog id={self.id} channel={self.channel} status={self.status}>"
