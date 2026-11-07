"""
CloudSage Inventory Request and Response Schemas.
Pydantic v2 schemas for multi-cloud resource inventory, relationships, synchronization, and correlation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ResourceRelationshipResponse(BaseModel):
    """Schema representing a directional resource relationship."""
    id: uuid.UUID
    source_resource_id: str
    target_resource_id: str
    relationship_type: str
    provider: str
    discovery_source: str
    confidence: Decimal
    first_observed_at: datetime
    last_observed_at: datetime
    relationship_metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class CloudResourceResponse(BaseModel):
    """Basic inventory resource representation."""
    resource_id: str
    provider: str
    account_id: str
    resource_name: Optional[str]
    service_category: str
    service_name: str
    resource_type: str
    region: str
    zone: Optional[str] = None
    status: str
    tags: Dict[str, str] = Field(default_factory=dict)
    owner: Optional[str] = None
    department: Optional[str] = None
    project: Optional[str] = None
    environment: str
    cost_center: Optional[str] = None
    tag_quality_score: Decimal
    monthly_cost: Decimal
    resource_created_at: Optional[datetime] = None
    first_discovered_at: datetime
    last_seen_at: datetime
    last_inventory_sync_at: Optional[datetime] = None
    discovery_source: str
    discovery_status: str

    model_config = ConfigDict(from_attributes=True)


class CloudResourceDetailResponse(CloudResourceResponse):
    """Detailed inventory resource representation including metadata, relationships, and cost."""
    raw_tags: Optional[Dict[str, Any]] = None
    resource_metadata: Optional[Dict[str, Any]] = None
    metadata_version: str
    relationships: List[ResourceRelationshipResponse] = []
    total_billed_cost: Optional[Decimal] = Decimal("0.0000")
    billing_records_count: Optional[int] = 0
    latest_billing_period: Optional[datetime] = None


class InventorySyncRunResponse(BaseModel):
    """Audit schema for an inventory synchronization execution."""
    run_id: uuid.UUID
    provider: str
    discovery_mode: str
    status: str
    source_identifier: Optional[str]
    total_discovered: int
    new_resources: int
    updated_resources: int
    stale_resources: int
    relationships_discovered: int
    started_at: datetime
    completed_at: Optional[datetime]
    error_details: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class InventoryQualityReportResponse(BaseModel):
    """Quality and coverage report schema for cloud inventory."""
    report_id: uuid.UUID
    sync_run_id: Optional[uuid.UUID]
    provider: Optional[str]
    total_resources: int
    completeness_score: Decimal
    tag_completeness_score: Decimal
    inventory_confidence: Decimal
    findings_count: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    findings_summary: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventorySummaryResponse(BaseModel):
    """High-level summary of cloud resource inventory across providers."""
    total_resources: int
    provider_distribution: Dict[str, int]
    service_category_distribution: Dict[str, int]
    status_distribution: Dict[str, int]
    environment_distribution: Dict[str, int]
    total_monthly_spend_usd: Decimal
    total_relationships: int
    average_tag_quality_score: Decimal
    inventory_coverage_percentage: Decimal
    last_synchronized_at: Optional[datetime] = None


class InventoryCoverageResponse(BaseModel):
    """Coverage breakdown comparing billing records vs inventory confirmed assets."""
    total_unique_resources: int
    inventory_confirmed_resources: int
    billing_only_resources: int
    inventory_only_resources: int
    reconciled_coverage_percentage: Decimal
    provider_coverage: Dict[str, Dict[str, Any]]


class BillingCorrelationResponse(BaseModel):
    """Resource-level financial correlation report."""
    resource_id: str
    provider: str
    account_id: str
    resource_name: Optional[str]
    service_name: str
    resource_type: str
    inventory_status: str
    discovery_status: str
    correlation_status: str = "CONFIRMED_BILLED"
    total_billed_cost: Decimal
    total_effective_cost: Decimal
    currency: str = "USD"
    billing_record_count: int
    earliest_billing_date: Optional[datetime] = None
    latest_billing_date: Optional[datetime] = None


class LiveDiscoveryRequest(BaseModel):
    """Request schema for triggering live read-only cloud discovery."""
    provider: str = Field(..., description="AWS, AZURE, or GCP")
    regions: Optional[List[str]] = Field(None, description="Specific regions to probe (e.g. ['us-east-1', 'us-west-2'])")
    resource_types: Optional[List[str]] = Field(None, description="Filter specific resource types to discover")


class InventoryImportResponse(BaseModel):
    """Response returned upon importing an inventory export file."""
    sync_run_id: str
    status: str
    provider: str
    total_discovered: int
    new_resources: int
    updated_resources: int
    stale_resources: int
    relationships_reconciled: int
    quality_score: float
    errors: List[Dict[str, Any]] = []


class CloudResourceListResponse(BaseModel):
    """Paginated list of cloud inventory resources."""
    total: int
    items: List[CloudResourceResponse]
    limit: int
    offset: int

