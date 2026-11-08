"""
CloudSage Alert Rules, Alert Instances, and Notification Schemas.
Pydantic v2 schemas for rule management, alert triage, outbox delivery,
in-app notification center, and user preferences.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.app.core.enums import (
    AlertStatus,
    AlertType,
    NotificationChannel,
    NotificationDeliveryStatus,
    Severity,
)


class AlertRuleBase(BaseModel):
    name: str = Field(..., max_length=128, description="Human-readable rule name")
    description: Optional[str] = Field(None, max_length=512, description="Rule description")
    alert_type: str = Field(default=AlertType.ANOMALY_ZSCORE.value, max_length=32)
    provider: str = Field(default="ALL", description="AWS, AZURE, GCP, or ALL")
    account_id: Optional[str] = Field(None, max_length=64, description="Cloud account ID scope")
    region: Optional[str] = Field(None, max_length=64, description="Region scope")
    service_name: Optional[str] = Field(None, max_length=128, description="Service name scope")
    environment: Optional[str] = Field(None, max_length=64, description="Environment scope")
    owner: Optional[str] = Field(None, max_length=128, description="Owner scope")
    cost_center: Optional[str] = Field(None, max_length=64, description="Cost center scope")
    min_severity: str = Field(default=Severity.MEDIUM.value, description="LOW, MEDIUM, HIGH, CRITICAL")
    threshold_value: Decimal = Field(default=Decimal("0.0000"), description="Trigger limit or Z-score")
    min_excess_cost: Decimal = Field(default=Decimal("0.0000"), ge=0, description="Minimum anomalous excess cost in USD")
    percentage_deviation_threshold: Decimal = Field(default=Decimal("0.00"), ge=0, description="Minimum % deviation")
    absolute_deviation_threshold: Decimal = Field(default=Decimal("0.0000"), ge=0, description="Minimum $ absolute deviation")
    anomaly_category: Optional[str] = Field(None, description="Category filter (e.g. SERVICE_SPIKE)")
    channels: List[str] = Field(default_factory=lambda: ["IN_APP"], description="Channels: IN_APP, EMAIL, WEBHOOK")
    recipients: List[str] = Field(default_factory=list, description="Target emails, webhook URLs, user IDs")
    cooldown_minutes: int = Field(default=1440, ge=1, le=43200, description="Cooldown window in minutes")
    escalation_policy: Dict[str, Any] = Field(default_factory=dict, description="Escalation rules and delays")
    is_enabled: bool = Field(default=True, description="Active evaluation toggle")

    @field_validator("min_excess_cost", "absolute_deviation_threshold", "threshold_value")
    @classmethod
    def validate_non_negative_currency(cls, v: Decimal) -> Decimal:
        if v < Decimal("0.0000"):
            raise ValueError("Financial thresholds cannot be negative.")
        return v

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, channels: List[str]) -> List[str]:
        valid = {c.value for c in NotificationChannel}
        for ch in channels:
            if ch.upper() not in valid:
                raise ValueError(f"Invalid notification channel '{ch}'. Valid channels: {valid}")
        return [c.upper() for c in channels]


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    provider: Optional[str] = None
    account_id: Optional[str] = None
    region: Optional[str] = None
    service_name: Optional[str] = None
    environment: Optional[str] = None
    owner: Optional[str] = None
    cost_center: Optional[str] = None
    min_severity: Optional[str] = None
    threshold_value: Optional[Decimal] = None
    min_excess_cost: Optional[Decimal] = None
    percentage_deviation_threshold: Optional[Decimal] = None
    absolute_deviation_threshold: Optional[Decimal] = None
    anomaly_category: Optional[str] = None
    channels: Optional[List[str]] = None
    recipients: Optional[List[str]] = None
    cooldown_minutes: Optional[int] = Field(None, ge=1, le=43200)
    escalation_policy: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class AlertRuleResponse(AlertRuleBase):
    id: UUID
    is_archived: bool
    created_by: str
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertRuleListResponse(BaseModel):
    items: List[AlertRuleResponse]
    total: int


class AlertRulePreviewRequest(BaseModel):
    provider: Optional[str] = "ALL"
    account_id: Optional[str] = None
    min_severity: str = "MEDIUM"
    min_excess_cost: Decimal = Decimal("0.0000")
    percentage_deviation_threshold: Decimal = Decimal("0.00")
    sample_limit: int = 10


class AlertRulePreviewMatch(BaseModel):
    anomaly_id: UUID
    title: str
    provider: str
    account_id: str
    service_name: str
    excess_cost: Decimal
    percentage_deviation: Decimal
    severity: str
    detected_at: datetime


class AlertRulePreviewResponse(BaseModel):
    matched_count: int
    total_evaluated: int
    sample_matches: List[AlertRulePreviewMatch]


# --- Alert Instance & Lifecycle Schemas ---

class AlertActionRequest(BaseModel):
    action: str = Field(..., description="ACKNOWLEDGE, INVESTIGATE, RESOLVE, SUPPRESS, REOPEN, CLOSE")
    notes: Optional[str] = Field(None, description="Notes, root cause, or resolution rationale")
    suppress_hours: Optional[int] = Field(None, ge=1, le=8760, description="Hours to suppress if action is SUPPRESS")
    ticket_ref: Optional[str] = Field(None, max_length=128, description="Jira, ServiceNow, or Linear ticket reference")


class AlertHistoryResponse(BaseModel):
    id: UUID
    alert_instance_id: UUID
    previous_status: Optional[str]
    new_status: str
    action: str
    actor: str
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertInstanceResponse(BaseModel):
    id: UUID
    alert_rule_id: Optional[UUID]
    anomaly_id: UUID
    dedup_key: str
    title: str
    severity: str
    current_cost: Decimal
    expected_cost: Decimal
    excess_cost: Decimal
    percentage_deviation: Decimal
    status: str
    provider: str
    account_id: str
    service_name: str
    region: str
    resource_id: Optional[str]
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    investigated_by: Optional[str]
    investigation_notes: Optional[str]
    ticket_ref: Optional[str]
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    suppressed_by: Optional[str]
    suppress_reason: Optional[str]
    suppress_until: Optional[datetime]
    trigger_count: int
    first_triggered_at: datetime
    last_triggered_at: datetime
    escalation_level: int
    last_escalated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertInstanceListResponse(BaseModel):
    items: List[AlertInstanceResponse]
    total: int


class AlertStatsResponse(BaseModel):
    total_alerts: int
    active_alerts: int
    critical_alerts: int
    high_alerts: int
    unacknowledged_alerts: int
    investigating_alerts: int
    resolved_alerts: int
    suppressed_alerts: int
    delivery_failures_24h: int


# --- In-App Notifications ---

class InAppNotificationResponse(BaseModel):
    id: UUID
    alert_instance_id: Optional[UUID]
    recipient_user_id: str
    title: str
    message: str
    severity: str
    provider: str
    account_id: str
    service_name: str
    excess_cost: Decimal
    is_read: bool
    read_at: Optional[datetime]
    action_url: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InAppNotificationListResponse(BaseModel):
    items: List[InAppNotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


# --- Outbox & Delivery Management ---

class NotificationDeliveryAttemptResponse(BaseModel):
    id: UUID
    outbox_id: UUID
    attempt_number: int
    channel: str
    recipient: str
    status: str
    response_code: Optional[int]
    response_body: Optional[str]
    latency_ms: Optional[int]
    error_message: Optional[str]
    attempted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationOutboxResponse(BaseModel):
    id: UUID
    alert_instance_id: Optional[UUID]
    channel: str
    recipient: str
    subject: str
    payload: Dict[str, Any]
    status: str
    attempts: int
    max_attempts: int
    next_attempt_at: datetime
    last_attempt_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    delivered_at: Optional[datetime]
    delivery_attempts: List[NotificationDeliveryAttemptResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class NotificationOutboxListResponse(BaseModel):
    items: List[NotificationOutboxResponse]
    total: int


class AlertInstanceDetailResponse(AlertInstanceResponse):
    history: List[AlertHistoryResponse] = Field(default_factory=list)
    deliveries: List[NotificationOutboxResponse] = Field(default_factory=list)
    anomaly: Optional[Dict[str, Any]] = None


class OutboxRetryResponse(BaseModel):
    outbox_id: UUID
    previous_status: str
    new_status: str
    scheduled_attempt: datetime
    message: str


class NotificationHealthResponse(BaseModel):
    status: str
    in_app_operational: bool
    email_mode: str
    webhook_operational: bool
    pending_outbox_count: int
    dead_letter_count: int
    total_delivered_24h: int
    total_failed_24h: int


# --- User Notification Preferences ---

class NotificationPreferenceRequest(BaseModel):
    enabled_channels: List[str] = Field(default_factory=lambda: ["IN_APP", "EMAIL"])
    min_severity: str = Field(default=Severity.LOW.value)
    receive_digests: bool = True
    digest_frequency: str = Field(default="DAILY")
    quiet_hours_enabled: bool = False
    quiet_hours_start_utc: Optional[str] = "22:00"
    quiet_hours_end_utc: Optional[str] = "08:00"

    @field_validator("enabled_channels")
    @classmethod
    def validate_channels(cls, channels: List[str]) -> List[str]:
        valid = {c.value for c in NotificationChannel}
        for ch in channels:
            if ch.upper() not in valid:
                raise ValueError(f"Invalid channel '{ch}'. Valid options: {valid}")
        return [c.upper() for c in channels]


class NotificationPreferenceResponse(NotificationPreferenceRequest):
    id: UUID
    user_email: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Legacy Schemas for Backward Compatibility ---

class NotificationLogBase(BaseModel):
    alert_rule_id: Optional[UUID] = None
    channel: NotificationChannel
    recipient: str = Field(..., max_length=256)
    payload: Dict[str, Any]
    status: str = Field(default="DELIVERED", max_length=16)


class NotificationLogCreate(NotificationLogBase):
    pass


class NotificationLogResponse(NotificationLogBase):
    id: UUID
    dispatched_at: datetime

    model_config = ConfigDict(from_attributes=True)
