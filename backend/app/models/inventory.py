"""
CloudSage Inventory and Resource Intelligence Models.
Entities for resource relationships, inventory sync runs, and inventory quality assessments.
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from backend.app.core.database import Base

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class ResourceRelationship(Base):
    """
    Topology relationship between cloud resources
    (e.g., EC2 Instance -> Attached EBS Volume, Snapshot -> Source Volume).
    """
    __tablename__ = "resource_relationships"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    source_resource_id = Column(
        String(512),
        ForeignKey("cloud_resources.resource_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Origin resource (e.g. Virtual Machine)",
    )
    target_resource_id = Column(
        String(512),
        nullable=False,
        index=True,
        doc="Dependent or associated resource (e.g. Attached Volume or Network Interface)",
    )
    relationship_type = Column(
        String(64),
        nullable=False,
        index=True,
        doc="Relationship type: ATTACHED_TO, SNAPSHOT_OF, MEMBER_OF, ASSOCIATED_WITH",
    )
    provider = Column(
        String(16),
        nullable=False,
        index=True,
        doc="Cloud Provider (AWS, AZURE, GCP)",
    )
    discovery_source = Column(
        String(32),
        nullable=False,
        default="INVENTORY_DISCOVERY",
        doc="Source of relationship discovery (INVENTORY_EXPORT, LIVE_CLOUD, BILLING_INFERRED)",
    )
    confidence = Column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("1.0000"),
        doc="Confidence score of relationship confirmation (1.0000 = confirmed, 0.8000 = inferred)",
    )
    first_observed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_observed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    relationship_metadata = Column(
        JSON_TYPE,
        nullable=True,
        default=dict,
        doc="Additional relationship metadata (e.g. mount point /dev/sda1, device index)",
    )

    __table_args__ = (
        UniqueConstraint("source_resource_id", "target_resource_id", "relationship_type", name="uq_resource_relationships"),
        Index("idx_rel_src_tgt", "source_resource_id", "target_resource_id"),
    )

    def __repr__(self) -> str:
        return f"<ResourceRelationship {self.source_resource_id} --[{self.relationship_type}]--> {self.target_resource_id}>"


class InventorySyncRun(Base):
    """
    Audit log of an inventory synchronization execution (file import or live discovery).
    """
    __tablename__ = "inventory_sync_runs"

    run_id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    provider = Column(
        String(16),
        nullable=False,
        index=True,
        doc="Cloud Provider (AWS, AZURE, GCP, or ALL)",
    )
    discovery_mode = Column(
        String(32),
        nullable=False,
        default="EXPORT_BASED",
        doc="Discovery mode: EXPORT_BASED or LIVE_CLOUD",
    )
    status = Column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
        doc="Status: PENDING, RUNNING, COMPLETED, PARTIAL_SUCCESS, FAILED",
    )
    source_identifier = Column(
        String(256),
        nullable=True,
        doc="File name or API endpoint queried",
    )
    total_discovered = Column(
        Integer,
        nullable=False,
        default=0,
    )
    new_resources = Column(
        Integer,
        nullable=False,
        default=0,
    )
    updated_resources = Column(
        Integer,
        nullable=False,
        default=0,
    )
    stale_resources = Column(
        Integer,
        nullable=False,
        default=0,
    )
    relationships_discovered = Column(
        Integer,
        nullable=False,
        default=0,
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
        return f"<InventorySyncRun id={self.run_id} provider={self.provider} status={self.status}>"


class InventoryQualityReport(Base):
    """
    Inventory quality evaluation snapshot measuring coverage, completeness, and hygiene.
    """
    __tablename__ = "inventory_quality_reports"

    report_id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    sync_run_id = Column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
        doc="Associated inventory sync run ID if triggered by a sync",
    )
    provider = Column(
        String(16),
        nullable=True,
        index=True,
        doc="Cloud provider evaluated (AWS, AZURE, GCP or ALL)",
    )
    total_resources = Column(
        Integer,
        nullable=False,
        default=0,
    )
    completeness_score = Column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("100.00"),
        doc="Resource metadata completeness score (0.00 to 100.00)",
    )
    tag_completeness_score = Column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("100.00"),
        doc="Tag hygiene and ownership governance score (0.00 to 100.00)",
    )
    inventory_confidence = Column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("1.0000"),
        doc="Overall inventory confidence score",
    )
    findings_count = Column(
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
    findings_summary = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Structured findings and quality metrics breakdown",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<InventoryQualityReport id={self.report_id} completeness={self.completeness_score}%>"
