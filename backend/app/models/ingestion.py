"""
CloudSage Ingestion Run & Tracking Model.
Maintains persistent audit records for all billing ingestion batches, metrics, and error summaries.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from backend.app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class IngestionRun(Base):
    """Tracks the execution and telemetry of a multi-cloud billing ingestion batch."""
    __tablename__ = "ingestion_runs"

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
        doc="Cloud Provider (AWS, AZURE, GCP, SYNTHETIC)"
    )
    source_filename = Column(
        String(256),
        nullable=False,
        doc="Name of the ingested file or synthetic scenario identifier"
    )
    status = Column(
        String(32),
        nullable=False,
        default="RUNNING",
        index=True,
        doc="Status: RUNNING, COMPLETED, PARTIAL_SUCCESS, FAILED"
    )
    total_records = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Total raw line items discovered"
    )
    ingested_records = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Successfully normalized and persisted records"
    )
    duplicate_records = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Records skipped due to idempotency fingerprint match"
    )
    failed_records = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Invalid or corrupted records rejected"
    )
    total_cost = Column(
        Numeric(18, 4),
        nullable=False,
        default=Decimal("0.0000"),
        doc="Sum of normalized unblended cost in USD"
    )
    checksum = Column(
        String(64),
        nullable=True,
        doc="SHA-256 payload checksum for audit verification"
    )
    error_summary = Column(
        JSON_TYPE,
        nullable=True,
        doc="List of validation errors with line numbers and reasons"
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        doc="Ingestion start timestamp"
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Ingestion completion timestamp"
    )

    __table_args__ = (
        Index("idx_ingest_prov_status", "provider", "status"),
        Index("idx_ingest_started_at", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<IngestionRun id={self.id} provider={self.provider} status={self.status} ingested={self.ingested_records}>"
