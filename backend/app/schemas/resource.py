"""
CloudSage Cloud Resource and Telemetry Metrics Pydantic Schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import CloudProvider, ServiceCategory


class ResourceMetricBase(BaseModel):
    metric_name: str = Field(..., max_length=64, description="Metric name (e.g. cpu_utilization_pct)")
    timestamp: datetime = Field(..., description="Interval sample timestamp (UTC)")
    average_value: Decimal = Field(..., description="Mean observed metric value")
    peak_value: Decimal = Field(..., description="Peak observed metric value")
    sample_count: int = Field(default=1, ge=1, description="Observation count")


class ResourceMetricCreate(ResourceMetricBase):
    resource_id: str = Field(..., max_length=512)


class ResourceMetricResponse(ResourceMetricBase):
    id: UUID
    resource_id: str

    model_config = ConfigDict(from_attributes=True)


class CloudResourceBase(BaseModel):
    resource_id: str = Field(..., max_length=512, description="Resource ARN or URI")
    provider: CloudProvider = Field(..., description="AWS, AZURE, GCP")
    account_id: str = Field(..., max_length=64, description="Account, Subscription, or Project ID")
    resource_name: Optional[str] = Field(None, max_length=256)
    service_category: ServiceCategory = Field(..., description="Standardized category")
    service_name: str = Field(..., max_length=128)
    resource_type: str = Field(..., max_length=64)
    region: str = Field(..., max_length=64)
    status: str = Field(default="active", max_length=32)
    tags: Dict[str, Any] = Field(default_factory=dict)
    owner: Optional[str] = Field(None, max_length=128)
    environment: str = Field(default="unknown", max_length=64)
    cost_center: Optional[str] = Field(None, max_length=64)
    monthly_cost: Decimal = Field(default=Decimal("0.0000"), ge=0)


class CloudResourceCreate(CloudResourceBase):
    pass


class CloudResourceResponse(CloudResourceBase):
    first_discovered_at: datetime
    last_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)
