"""
CloudSage Advisory Recommendation Pydantic Schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import (
    CloudProvider,
    ImplementationEffort,
    Priority,
    RecommendationAction,
    RecommendationStatus,
    RiskLevel,
)


class RecommendationBase(BaseModel):
    resource_id: str = Field(..., max_length=512)
    provider: CloudProvider
    action_type: RecommendationAction
    priority: Priority = Field(default=Priority.P2)
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    status: RecommendationStatus = Field(default=RecommendationStatus.PROPOSED)
    estimated_monthly_savings: Decimal = Field(..., ge=0, description="Monthly dollar savings")
    estimated_annual_savings: Decimal = Field(..., ge=0, description="Annual dollar savings")
    implementation_effort: ImplementationEffort = Field(default=ImplementationEffort.LOW)
    title: str = Field(..., max_length=256)
    description: str
    remediation_guide: str = Field(..., description="Step-by-step remediation guide or CLI snippet")
    endorsed_by: Optional[str] = Field(None, max_length=128)
    approved_by: Optional[str] = Field(None, max_length=128)
    approved_at: Optional[datetime] = None
    implemented_at: Optional[datetime] = None


class RecommendationCreate(RecommendationBase):
    waste_detection_id: Optional[UUID] = None


class RecommendationStatusUpdate(BaseModel):
    status: RecommendationStatus
    actor_email: str = Field(..., max_length=128)
    notes: Optional[str] = None


class RecommendationResponse(RecommendationBase):
    id: UUID
    waste_detection_id: Optional[UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
