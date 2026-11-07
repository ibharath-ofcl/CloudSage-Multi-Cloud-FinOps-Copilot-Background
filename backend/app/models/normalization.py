"""
CloudSage Normalization and Data Quality Models.
Entities for historical exchange rates, SKU catalog mappings, normalization runs, and data quality assessments.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from backend.app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class ExchangeRate(Base):
    """
    Historical and daily foreign exchange rates relative to USD.
    Supports exact-date and preceding-business-day lookups.
    """
    __tablename__ = "exchange_rates"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    currency_code = Column(
        String(3),
        nullable=False,
        index=True,
        doc="ISO 4217 Currency Code (e.g. EUR, GBP, INR, JPY)",
    )
    effective_date = Column(
        Date,
        nullable=False,
        index=True,
        doc="Date for which the exchange rate applies",
    )
    rate_to_usd = Column(
        Numeric(18, 6),
        nullable=False,
        doc="Multiplier to convert 1 foreign unit to USD (Strict Decimal)",
    )
    source = Column(
        String(64),
        nullable=False,
        default="ECB_REFERENCE",
        doc="Source of exchange rate (e.g. ECB, OPEN_EXCHANGE_RATES, STATIC_FALLBACK)",
    )
    is_interpolated = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="True if rate was carried over from preceding business day (weekend/holiday)",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_exchange_rates_curr_date", "currency_code", "effective_date", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ExchangeRate {self.currency_code} on {self.effective_date} = {self.rate_to_usd} USD>"


class SkuCatalogMapping(Base):
    """
    Catalog mapping table resolving hyperscaler service codes and SKUs
    to canonical FinOps categories, families, and resource types.
    """
    __tablename__ = "sku_catalog_mappings"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    provider = Column(
        String(16),
        nullable=False,
        index=True,
        doc="Cloud Provider (AWS, AZURE, GCP)",
    )
    service_code = Column(
        String(128),
        nullable=False,
        index=True,
        doc="Provider-specific service code or product name",
    )
    sku_id = Column(
        String(256),
        nullable=True,
        index=True,
        doc="Provider-specific SKU ID or usage type if available",
    )
    canonical_category = Column(
        String(32),
        nullable=False,
        doc="Standardized FinOps Category (COMPUTE, STORAGE, DATABASE, etc.)",
    )
    service_family = Column(
        String(64),
        nullable=False,
        doc="Sub-category (Virtual Machine, Object Storage, Relational Database)",
    )
    resource_type = Column(
        String(64),
        nullable=False,
        doc="Normalized resource type identifier",
    )
    normalized_unit = Column(
        String(32),
        nullable=False,
        doc="Standardized usage unit (HOURS, GB_MONTH, REQUESTS)",
    )
    pricing_model_default = Column(
        String(32),
        nullable=True,
        doc="Default pricing model if not specified in line item",
    )
    confidence = Column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("1.0000"),
        doc="Confidence score of mapping (1.0 = exact verified match, <0.8 = heuristic)",
    )
    provenance = Column(
        String(32),
        nullable=False,
        default="SYSTEM_CATALOG",
        doc="Mapping provenance (SYSTEM_CATALOG, USER_OVERRIDE, HEURISTIC)",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_sku_catalog_lookup", "provider", "service_code", "sku_id"),
    )

    def __repr__(self) -> str:
        return f"<SkuCatalogMapping {self.provider}:{self.service_code} -> {self.canonical_category}>"


class NormalizationRun(Base):
    """
    Execution audit record for batch normalization or re-normalization jobs.
    """
    __tablename__ = "normalization_runs"

    run_id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    status = Column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
        doc="Status (PENDING, PROCESSING, COMPLETED, PARTIAL_SUCCESS, FAILED)",
    )
    normalization_version = Column(
        String(16),
        nullable=False,
        default="1.0.0",
        doc="Semantic version of normalization logic",
    )
    mapping_version = Column(
        String(16),
        nullable=False,
        default="2026.11",
        doc="Version of service taxonomy and catalog rules applied",
    )
    total_records = Column(
        Integer,
        nullable=False,
        default=0,
    )
    successful_records = Column(
        Integer,
        nullable=False,
        default=0,
    )
    failed_records = Column(
        Integer,
        nullable=False,
        default=0,
    )
    warnings_count = Column(
        Integer,
        nullable=False,
        default=0,
    )
    average_quality_score = Column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("100.00"),
        doc="Average data quality score across all evaluated records",
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_details = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="Quarantined records and error reasons",
    )

    def __repr__(self) -> str:
        return f"<NormalizationRun id={self.run_id} status={self.status} quality={self.average_quality_score}%>"


class DataQualityReport(Base):
    """
    Persisted data quality assessment report for compliance and auditability.
    """
    __tablename__ = "data_quality_reports"

    report_id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    run_id = Column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
        doc="Associated normalization run ID if triggered by batch",
    )
    provider = Column(
        String(16),
        nullable=True,
        index=True,
        doc="Cloud provider evaluated (AWS, AZURE, GCP or ALL)",
    )
    overall_score = Column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("100.00"),
        doc="Overall data quality score (0.00 to 100.00)",
    )
    total_records_evaluated = Column(
        Integer,
        nullable=False,
        default=0,
    )
    critical_findings = Column(
        Integer,
        nullable=False,
        default=0,
    )
    high_findings = Column(
        Integer,
        nullable=False,
        default=0,
    )
    medium_findings = Column(
        Integer,
        nullable=False,
        default=0,
    )
    low_findings = Column(
        Integer,
        nullable=False,
        default=0,
    )
    informational_findings = Column(
        Integer,
        nullable=False,
        default=0,
    )
    findings_summary = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Categorized validation rule findings and metrics",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<DataQualityReport id={self.report_id} score={self.overall_score}%>"
