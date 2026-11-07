"""
CloudSage Billing Record Pydantic Schemas.
FOCUS 1.0 schema validation with strict Decimal representation for financial figures.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory


class BillingRecordBase(BaseModel):
    provider: CloudProvider = Field(..., description="Cloud Provider (AWS, AZURE, GCP)")
    billing_account_id: str = Field(..., max_length=64, description="Payer billing account ID")
    subscription_id: str = Field(..., max_length=64, description="Sub-account, subscription, or GCP project ID")
    resource_id: str = Field(..., max_length=512, description="Resource ARN or URI")
    resource_name: Optional[str] = Field(None, max_length=256, description="Human-readable name")
    service_category: ServiceCategory = Field(..., description="Canonical service category")
    service_name: str = Field(..., max_length=128, description="Provider native service name")
    region: str = Field(..., max_length=64, description="Geographical region")
    zone: Optional[str] = Field(None, max_length=64, description="Availability zone")
    usage_start_time: datetime = Field(..., description="Start of usage interval (UTC)")
    usage_end_time: datetime = Field(..., description="End of usage interval (UTC)")
    usage_quantity: Decimal = Field(..., ge=0, description="Usage amount in normalized units")
    usage_unit: str = Field(..., max_length=32, description="Standardized unit (e.g. HOURS)")
    unblended_cost: Decimal = Field(..., ge=0, description="Net cost in USD (Strict Decimal)")
    blended_cost: Optional[Decimal] = Field(None, ge=0, description="Blended cost if applicable")
    list_cost: Optional[Decimal] = Field(None, ge=0, description="Public list price in USD")
    pricing_model: PricingModel = Field(default=PricingModel.ON_DEMAND, description="Pricing mechanism")
    currency: str = Field(default="USD", max_length=8, description="Currency standard")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Sanitized metadata tags")
    raw_metadata: Optional[Dict[str, Any]] = Field(None, description="Original raw provider metadata")


class BillingRecordCreate(BillingRecordBase):
    pass


class BillingRecordResponse(BillingRecordBase):
    record_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
