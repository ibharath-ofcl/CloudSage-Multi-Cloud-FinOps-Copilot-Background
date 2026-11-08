"""
Pydantic Schemas for CloudSage Multi-Cloud FinOps Dashboard.
Defines structured response payloads for executive KPIs, time-series trends,
provider comparisons, service breakdowns, resource rankings, savings summaries,
and report exports.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import CloudProvider, Priority, Severity


class DashboardFilterParams(BaseModel):
    """Global query filter parameters for dashboard endpoints."""
    start_date: Optional[date] = Field(None, description="Start date (inclusive, YYYY-MM-DD)")
    end_date: Optional[date] = Field(None, description="End date (inclusive, YYYY-MM-DD)")
    provider: Optional[str] = Field(None, description="Cloud provider filter (AWS, AZURE, GCP, or ALL)")
    service: Optional[str] = Field(None, description="Service name filter (e.g. Amazon EC2)")
    account_id: Optional[str] = Field(None, description="Account, Subscription, or Project ID")
    region: Optional[str] = Field(None, description="Cloud region filter")
    environment: Optional[str] = Field(None, description="Environment tag (prod, dev, staging)")
    owner: Optional[str] = Field(None, description="Owner or team tag")
    cost_center: Optional[str] = Field(None, description="Cost center tag")


class ExecutiveKpiSummary(BaseModel):
    """Executive FinOps KPI summary metrics."""
    model_config = ConfigDict(from_attributes=True)

    total_spend: Decimal = Field(..., description="Total unblended cloud expenditure in USD")
    mtd_spend: Decimal = Field(..., description="Month-to-date cloud expenditure in USD")
    previous_period_spend: Decimal = Field(..., description="Expenditure in the preceding comparison period in USD")
    mom_change_percentage: Decimal = Field(..., description="Month-over-month spend change percentage (+/-)")
    active_anomalies_count: int = Field(..., description="Number of currently open/unresolved cost anomalies")
    anomalous_excess_cost: Decimal = Field(..., description="Total estimated excess cost from open anomalies in USD")
    identified_waste_count: int = Field(..., description="Number of active infrastructure waste detections")
    identified_monthly_waste: Decimal = Field(..., description="Estimated monthly waste across idle/unattached assets in USD")
    potential_monthly_savings: Decimal = Field(..., description="Total actionable monthly savings from open recommendations in USD")
    potential_annual_savings: Decimal = Field(..., description="Annualized actionable savings in USD")
    verified_realized_savings: Optional[Decimal] = Field(None, description="Actual verified realized savings (null if unverified)")
    currency: str = Field(default="USD", description="Currency code")
    data_freshness_timestamp: datetime = Field(..., description="Timestamp of the most recent billing/inventory sync")


class CostTrendPoint(BaseModel):
    """Single time-series spending interval."""
    model_config = ConfigDict(from_attributes=True)

    date: str = Field(..., description="Date formatted as YYYY-MM-DD")
    total_cost: Decimal = Field(..., description="Total daily expenditure in USD")
    aws_cost: Decimal = Field(default=Decimal("0.0000"), description="AWS daily expenditure in USD")
    azure_cost: Decimal = Field(default=Decimal("0.0000"), description="Azure daily expenditure in USD")
    gcp_cost: Decimal = Field(default=Decimal("0.0000"), description="GCP daily expenditure in USD")
    has_anomaly: bool = Field(default=False, description="Whether a cost anomaly was flagged on this date")


class CostTrendResponse(BaseModel):
    """Historical cost trajectory and trend response."""
    timeframe: str = Field(..., description="e.g. 'last_30_days', 'last_90_days', 'mtd'")
    granularity: str = Field(default="DAILY", description="DAILY, WEEKLY, or MONTHLY")
    points: List[CostTrendPoint] = Field(default_factory=list)
    total_cost: Decimal
    currency: str = "USD"


class ProviderComparisonItem(BaseModel):
    """Expenditure metrics for an individual cloud provider."""
    model_config = ConfigDict(from_attributes=True)

    provider: str = Field(..., description="AWS, AZURE, GCP")
    cost: Decimal = Field(..., description="Total spend for provider in USD")
    percentage: Decimal = Field(..., description="Percentage of total multi-cloud spend")
    record_count: int = Field(..., description="Number of underlying billing records")
    resource_count: int = Field(default=0, description="Number of tracked resources")


class ProviderComparisonResponse(BaseModel):
    """Multi-cloud provider spending distribution."""
    providers: List[ProviderComparisonItem] = Field(default_factory=list)
    total_spend: Decimal
    currency: str = "USD"


class ServiceCostItem(BaseModel):
    """Expenditure metrics for a specific cloud service."""
    model_config = ConfigDict(from_attributes=True)

    service_name: str
    service_category: str
    provider: str
    cost: Decimal
    percentage: Decimal
    record_count: int


class ServiceBreakdownResponse(BaseModel):
    """Top-N services and service categories breakdown."""
    services: List[ServiceCostItem] = Field(default_factory=list)
    categories: Dict[str, Decimal] = Field(default_factory=dict, description="Spend grouped by standard category")
    total_spend: Decimal
    currency: str = "USD"


class ResourceCostItem(BaseModel):
    """Expenditure and utilization metrics for a top cost-driving resource."""
    model_config = ConfigDict(from_attributes=True)

    resource_id: str
    resource_name: Optional[str]
    provider: str
    service_name: str
    region: str
    monthly_cost: Decimal
    status: str
    owner: Optional[str] = None
    environment: Optional[str] = None


class ResourceCostsResponse(BaseModel):
    """Top cost-driving resources ranking."""
    resources: List[ResourceCostItem] = Field(default_factory=list)
    total_spend: Decimal
    currency: str = "USD"


class SavingsSummaryResponse(BaseModel):
    """Prioritized savings and anti-double-counting financial breakdown."""
    potential_monthly_savings: Decimal
    potential_annual_savings: Decimal
    verified_realized_savings: Optional[Decimal] = None
    savings_by_provider: Dict[str, Decimal] = Field(default_factory=dict)
    savings_by_strategy: Dict[str, Decimal] = Field(default_factory=dict)
    savings_by_priority: Dict[str, Decimal] = Field(default_factory=dict)
    anti_double_counting_guarantee: bool = True
    currency: str = "USD"


class AnomalySummaryResponse(BaseModel):
    """Cost anomaly intelligence summary."""
    total_active_anomalies: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    total_excess_cost: Decimal
    anomalies_by_provider: Dict[str, int] = Field(default_factory=dict)
    anomalies_by_category: Dict[str, int] = Field(default_factory=dict)
    open_vs_resolved: Dict[str, int] = Field(default_factory=dict)
    currency: str = "USD"


class WasteSummaryResponse(BaseModel):
    """Cloud waste detection summary."""
    total_active_waste_items: int
    total_monthly_waste: Decimal
    waste_by_type: Dict[str, Decimal] = Field(default_factory=dict)
    waste_by_provider: Dict[str, Decimal] = Field(default_factory=dict)
    severity_distribution: Dict[str, int] = Field(default_factory=dict)
    currency: str = "USD"


class RecommendationSummaryResponse(BaseModel):
    """Advisory recommendation summary."""
    total_open_recommendations: int
    potential_monthly_savings: Decimal
    priority_distribution: Dict[str, int] = Field(default_factory=dict)
    strategy_distribution: Dict[str, int] = Field(default_factory=dict)
    status_distribution: Dict[str, int] = Field(default_factory=dict)
    currency: str = "USD"


class InventorySummaryResponse(BaseModel):
    """Multi-cloud inventory intelligence summary."""
    total_resources: int
    resources_by_provider: Dict[str, int] = Field(default_factory=dict)
    resources_by_type: Dict[str, int] = Field(default_factory=dict)
    resources_by_region: Dict[str, int] = Field(default_factory=dict)
    tag_coverage_percentage: Decimal
    untagged_resources_count: int


class IngestionSummaryResponse(BaseModel):
    """Ingestion pipeline health and status summary."""
    total_runs: int
    successful_runs: int
    failed_runs: int
    total_records_ingested: int
    provider_coverage: List[str] = Field(default_factory=list)
    last_successful_ingestion: Optional[datetime] = None


class DataQualitySummaryResponse(BaseModel):
    """FOCUS 1.0 normalization and data quality compliance summary."""
    overall_quality_score: Decimal
    focus_compliance_percentage: Decimal
    total_records_evaluated: int
    tag_quality_score: Decimal
    currency_uniformity_score: Decimal


class DashboardOverviewResponse(BaseModel):
    """Unified executive command center response combining core FinOps domains."""
    kpi: ExecutiveKpiSummary
    provider_comparison: ProviderComparisonResponse
    cost_trends: CostTrendResponse
    top_services: ServiceBreakdownResponse
    savings_summary: SavingsSummaryResponse
    anomaly_summary: AnomalySummaryResponse
    waste_summary: WasteSummaryResponse
    recommendation_summary: RecommendationSummaryResponse
    copilot_suggested_questions: List[str] = Field(default_factory=list)


class DashboardExportRequest(BaseModel):
    """Request payload for dashboard data export."""
    format: str = Field(default="json", description="Export format: 'json' or 'csv'")
    section: str = Field(default="overview", description="Section: 'overview', 'trends', 'services', 'anomalies', 'waste', 'recommendations'")
    filters: Optional[DashboardFilterParams] = None
