"""
CloudSage Waste Detection Pydantic Schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import CloudProvider, Severity, WasteStatus, WasteType


class WasteDetectionBase(BaseModel):
    resource_id: str = Field(..., max_length=512)
    provider: CloudProvider
    waste_type: WasteType
    severity: Severity = Field(default=Severity.MEDIUM)
    status: WasteStatus = Field(default=WasteStatus.ACTIVE)
    estimated_monthly_waste: Decimal = Field(..., ge=0, description="Projected monthly dollar waste")
    telemetry_proof: Dict[str, Any] = Field(default_factory=dict, description="Supporting metrics")
    dismissal_reason: Optional[str] = Field(None, max_length=512)
    dismissed_by: Optional[str] = Field(None, max_length=128)
    snooze_until: Optional[datetime] = None


class WasteDetectionCreate(WasteDetectionBase):
    pass


class WasteDetectionUpdate(BaseModel):
    status: Optional[WasteStatus] = None
    dismissal_reason: Optional[str] = None
    dismissed_by: Optional[str] = None
    snooze_until: Optional[datetime] = None


class WasteDetectionResponse(WasteDetectionBase):
    id: UUID
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)
