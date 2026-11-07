"""
CloudSage Cost Anomaly Pydantic Schemas.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import AnomalyStatus, CloudProvider, ServiceCategory, Severity


class CostAnomalyBase(BaseModel):
    provider: CloudProvider
    service_category: ServiceCategory
    service_name: str = Field(..., max_length=128)
    account_id: str = Field(..., max_length=64)
    region: str = Field(..., max_length=64)
    anomaly_date: date
    actual_cost: Decimal = Field(..., ge=0)
    expected_cost: Decimal = Field(..., ge=0)
    baseline_mean: Decimal = Field(..., ge=0)
    baseline_stddev: Decimal = Field(..., ge=0)
    z_score: Decimal
    spike_percentage: Decimal
    severity: Severity = Field(default=Severity.MEDIUM)
    status: AnomalyStatus = Field(default=AnomalyStatus.OPEN)
    root_cause_analysis: Dict[str, Any] = Field(default_factory=dict)


class CostAnomalyCreate(CostAnomalyBase):
    pass


class CostAnomalyStatusUpdate(BaseModel):
    status: AnomalyStatus


class CostAnomalyResponse(CostAnomalyBase):
    id: UUID
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)
