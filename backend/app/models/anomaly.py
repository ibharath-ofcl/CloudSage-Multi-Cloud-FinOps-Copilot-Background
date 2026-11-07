"""
CloudSage Cost Anomaly Model.
Stores statistical spending spikes, baseline deviations, and automated root-cause attribution.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from backend.app.core.database import Base
from backend.app.core.enums import AnomalyStatus, Severity

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class CostAnomaly(Base):
    """Statistical cost anomaly record flagged by the Anomaly Detection Engine."""
    __tablename__ = "cost_anomalies"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    provider = Column(
        String(16),
        nullable=False,
        index=True,
        doc="Cloud Provider (AWS, AZURE, GCP)"
    )
    service_category = Column(
        String(32),
        nullable=False,
        index=True,
        doc="Service category (COMPUTE, STORAGE, DATABASE, etc.)"
    )
    service_name = Column(
        String(128),
        nullable=False,
        index=True,
        doc="Cloud service name"
    )
    account_id = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Account, Subscription, or Project ID"
    )
    region = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Cloud region"
    )
    anomaly_date = Column(
        Date,
        nullable=False,
        index=True,
        doc="Date on which the spending spike occurred"
    )
    actual_cost = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Actual observed cost on anomaly date"
    )
    expected_cost = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Expected baseline expenditure"
    )
    baseline_mean = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Trailing 30-day mean (mu)"
    )
    baseline_stddev = Column(
        Numeric(18, 4),
        nullable=False,
        doc="Trailing 30-day standard deviation (sigma)"
    )
    z_score = Column(
        Numeric(8, 4),
        nullable=False,
        doc="Standard score (Z-Score)"
    )
    spike_percentage = Column(
        Numeric(8, 2),
        nullable=False,
        doc="Percentage increase over expected baseline"
    )
    severity = Column(
        String(16),
        nullable=False,
        default=Severity.MEDIUM.value,
        index=True,
        doc="Anomaly severity (LOW, MEDIUM, HIGH, CRITICAL)"
    )
    status = Column(
        String(16),
        nullable=False,
        default=AnomalyStatus.OPEN.value,
        index=True,
        doc="Status (OPEN, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE)"
    )
    root_cause_analysis = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Root cause attribution breakdown (driver resource, volume surge, tag)"
    )
    detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
        doc="Detection timestamp"
    )

    __table_args__ = (
        Index("idx_anomaly_status_date", "status", "anomaly_date"),
        Index("idx_anomaly_prov_service", "provider", "service_name", "anomaly_date"),
    )

    def __repr__(self) -> str:
        return f"<CostAnomaly id={self.id} service={self.service_name} z_score={self.z_score} delta={self.actual_cost - self.expected_cost} USD>"
