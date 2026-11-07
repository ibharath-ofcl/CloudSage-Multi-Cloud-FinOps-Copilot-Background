"""
CloudSage Cloud Resource and Telemetry Metrics Models.
Maintains inventory of discovered cloud resources and their time-series utilization metrics.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from backend.app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class CloudResource(Base):
    """Inventory record for a discovered multi-cloud resource."""
    __tablename__ = "cloud_resources"

    resource_id = Column(
        String(512),
        primary_key=True,
        nullable=False,
        doc="Globally unique cloud resource ARN or URI"
    )
    provider = Column(
        String(16),
        nullable=False,
        index=True,
        doc="Cloud Provider (AWS, AZURE, GCP)"
    )
    account_id = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Account, Subscription, or Project ID"
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
        doc="Standardized category (COMPUTE, STORAGE, DATABASE, etc.)"
    )
    service_name = Column(
        String(128),
        nullable=False,
        index=True,
        doc="Cloud service name (e.g. AmazonEC2, Azure VM)"
    )
    resource_type = Column(
        String(64),
        nullable=False,
        doc="Specific asset type (e.g. ec2:instance, managed_disk)"
    )
    region = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Cloud region"
    )
    status = Column(
        String(32),
        nullable=False,
        default="active",
        doc="Resource status (running, stopped, available, unattached)"
    )
    tags = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Normalized resource metadata tags"
    )
    owner = Column(
        String(128),
        nullable=True,
        index=True,
        doc="Owner identity extracted from tags"
    )
    environment = Column(
        String(64),
        nullable=False,
        default="unknown",
        index=True,
        doc="Environment tag (production, staging, dev, test)"
    )
    cost_center = Column(
        String(64),
        nullable=True,
        index=True,
        doc="Financial cost center or department"
    )
    monthly_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Trailing 30-day aggregate cost in USD"
    )
    first_discovered_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Discovery timestamp"
    )
    last_seen_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Latest telemetry confirmation timestamp"
    )

    metrics = relationship("ResourceMetric", back_populates="resource", cascade="all, delete-orphan")
    waste_detections = relationship("WasteDetection", back_populates="resource")
    recommendations = relationship("Recommendation", back_populates="resource")

    __table_args__ = (
        Index("idx_res_prov_env", "provider", "environment"),
        Index("idx_res_owner", "owner"),
    )

    def __repr__(self) -> str:
        return f"<CloudResource id={self.resource_id} provider={self.provider} status={self.status}>"


class ResourceMetric(Base):
    """Time-series utilization metric record (CPU, Memory, Network, Disk)."""
    __tablename__ = "resource_metrics"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    resource_id = Column(
        String(512),
        ForeignKey("cloud_resources.resource_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    metric_name = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Metric name (e.g. cpu_utilization_pct, network_in_bytes)"
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Interval sample timestamp"
    )
    average_value = Column(
        Numeric(10, 4),
        nullable=False,
        doc="Mean value during sample window"
    )
    peak_value = Column(
        Numeric(10, 4),
        nullable=False,
        doc="Peak value during sample window"
    )
    sample_count = Column(
        Integer,
        nullable=False,
        default=1,
        doc="Number of observations aggregated"
    )

    resource = relationship("CloudResource", back_populates="metrics")

    __table_args__ = (
        Index("idx_metrics_res_name_time", "resource_id", "metric_name", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<ResourceMetric res={self.resource_id} {self.metric_name}={self.average_value}>"
