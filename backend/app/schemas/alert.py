"""
CloudSage Alert Rules and Notification Logs Pydantic Schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import AlertType, NotificationChannel


class AlertRuleBase(BaseModel):
    name: str = Field(..., max_length=128)
    alert_type: AlertType
    threshold_value: Decimal = Field(..., description="Monetary budget or Z-score limit")
    channels: List[Dict[str, Any]] = Field(default_factory=list, description="List of webhook / email targets")
    is_enabled: bool = True


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    threshold_value: Optional[Decimal] = None
    channels: Optional[List[Dict[str, Any]]] = None
    is_enabled: Optional[bool] = None


class AlertRuleResponse(AlertRuleBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
