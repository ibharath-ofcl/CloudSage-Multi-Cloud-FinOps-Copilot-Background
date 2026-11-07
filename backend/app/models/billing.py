"""
CloudSage Billing Record Model.
Implements the canonical FinOps Open Cost & Usage Specification (FOCUS™ 1.0)
for unified multi-cloud cost line items across AWS, Azure, and GCP.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from backend.app.core.database import Base
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class BillingRecord(Base):
    """
    Canonical FOCUS 1.0 Normalized Billing Line Item.
    Designed for native range partitioning by `usage_start_time`.
    """
    __tablename__ = "billing_records"

    record_id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Unique identifier for normalized billing record"
    )
    provider = Column(
        String(16),
        nullable=False,
        index=True,
        doc="Cloud Provider (AWS, AZURE, GCP)"
    )
    billing_account_id = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Payer account ID or master billing ID"
    )
    subscription_id = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Sub-account, subscription, or GCP project ID"
    )
    resource_id = Column(
        String(512),
        nullable=False,
        index=True,
        doc="Globally unique cloud resource ARN or URI"
    )
    resource_name = Column(
        String(256),
        nullable=True,
        doc="Human-readable resource name or VM hostname"
    )
    service_category = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Normalized category (COMPUTE, STORAGE, DATABASE, etc.)"
    )
    service_name = Column(
        String(128),
        nullable=False,
        index=True,
        doc="Native hyperscaler service name"
    )
    region = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Normalized geographical region"
    )
    zone = Column(
        String(64),
        nullable=True,
        doc="Availability zone if available"
    )
    usage_start_time = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Billing interval start (Partition key)"
    )
    usage_end_time = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="Billing interval end"
    )
    usage_quantity = Column(
        Numeric(18, 6),
        nullable=False,
        default=Decimal("0.0"),
        doc="Usage amount in normalized units"
    )
    usage_unit = Column(
        String(32),
        nullable=False,
        doc="Standardized usage unit (HOURS, GB_MONTH, etc.)"
    )
    unblended_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Net cash cost in USD (Strict Decimal)"
    )
    blended_cost = Column(
        Numeric(18, 4),
        nullable=True,
        doc="Blended cost if applicable"
    )
    list_cost = Column(
        Numeric(18, 4),
        nullable=True,
        doc="Standard public list price in USD"
    )
    pricing_model = Column(
        String(32),
        nullable=False,
        default=PricingModel.ON_DEMAND.value,
        doc="Pricing model (ON_DEMAND, RESERVED, SPOT, SAVINGS_PLAN)"
    )
    currency = Column(
        String(8),
        nullable=False,
        default="USD",
        doc="Standardized billing currency"
    )
    tags = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Normalized key-value resource metadata tags"
    )
    raw_metadata = Column(
        JSON_TYPE,
        nullable=True,
        doc="Original provider line item attributes for auditability"
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Record ingestion timestamp"
    )

    __table_args__ = (
        Index("idx_billing_prov_srv_time", "provider", "service_category", "usage_start_time"),
        Index("idx_billing_res_time", "resource_id", "usage_start_time"),
    )

    def __repr__(self) -> str:
        return f"<BillingRecord id={self.record_id} provider={self.provider} cost={self.unblended_cost} USD>"
