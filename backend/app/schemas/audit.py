"""
CloudSage Audit Log Pydantic Schemas.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import AuditAction


class AuditLogBase(BaseModel):
    user_id: Optional[UUID] = None
    user_email: Optional[str] = Field(None, max_length=256)
    action_type: AuditAction
    resource_type: str = Field(..., max_length=64)
    resource_id: Optional[str] = Field(None, max_length=512)
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    client_ip: Optional[str] = Field(None, max_length=64)
    status: str = Field(default="SUCCESS", max_length=16)


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
