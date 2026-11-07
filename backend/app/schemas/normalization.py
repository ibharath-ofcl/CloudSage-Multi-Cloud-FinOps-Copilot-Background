"""
CloudSage Normalization Schemas.
Pydantic v2 schemas for FOCUS 1.0 validation, currency rates, SKU catalog, tag governance, and data quality.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ExchangeRateBase(BaseModel):
    """Base schema for exchange rates."""
    currency_code: str = Field(..., min_length=3, max_length=3, description="ISO 4217 Currency Code")
    effective_date: date = Field(..., description="Date for which the exchange rate applies")
    rate_to_usd: Decimal = Field(..., gt=0, description="Multiplier to convert 1 foreign unit to USD")
    source: str = Field(default="ECB_REFERENCE", description="Source of exchange rate")
    is_interpolated: bool = Field(default=False, description="Whether rate was carried over from previous business day")


class ExchangeRateCreate(ExchangeRateBase):
    """Schema for adding or updating an exchange rate."""
    pass


class ExchangeRateResponse(ExchangeRateBase):
    """Response schema for exchange rate representation."""
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CurrencyConversionRequest(BaseModel):
    """Request to convert a monetary amount to USD."""
    amount: Decimal = Field(..., ge=0, description="Original monetary cost")
    currency: str = Field(..., min_length=3, max_length=3, description="Original currency code")
    effective_date: Optional[date] = Field(None, description="Billing date for historical rate lookup")


class CurrencyConversionResult(BaseModel):
    """Result of currency conversion."""
    original_amount: Decimal
    original_currency: str
    converted_amount_usd: Decimal
    target_currency: str = "USD"
    effective_date: date
    rate_used: Decimal
    source: str
    is_interpolated: bool
    conversion_timestamp: datetime


class SkuCatalogMappingBase(BaseModel):
    """Base schema for SKU catalog mapping entries."""
    provider: str = Field(..., description="Cloud Provider (AWS, AZURE, GCP)")
    service_code: str = Field(..., description="Provider service code or product name")
    sku_id: Optional[str] = Field(None, description="SKU ID or usage type")
    canonical_category: str = Field(..., description="Canonical category (COMPUTE, STORAGE, etc.)")
    service_family: str = Field(..., description="Service family or subcategory")
    resource_type: str = Field(..., description="Normalized resource type")
    normalized_unit: str = Field(..., description="Standardized usage unit")
    pricing_model_default: Optional[str] = Field(None, description="Default pricing model")
    confidence: Decimal = Field(default=Decimal("1.0000"), ge=0, le=1, description="Mapping confidence")
    provenance: str = Field(default="SYSTEM_CATALOG", description="Mapping provenance")


class SkuCatalogMappingCreate(SkuCatalogMappingBase):
    """Schema for creating a catalog mapping."""
    pass


class SkuCatalogMappingResponse(SkuCatalogMappingBase):
    """Response schema for catalog mapping."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SkuCatalogLookupRequest(BaseModel):
    """Request to resolve a service code/SKU to canonical categories."""
    provider: str
    service_code: str
    sku_id: Optional[str] = None


class SkuCatalogLookupResponse(BaseModel):
    """Lookup result for SKU resolution."""
    provider: str
    service_code: str
    sku_id: Optional[str]
    canonical_category: str
    service_family: str
    resource_type: str
    normalized_unit: str
    confidence: Decimal
    provenance: str
    is_known: bool


class FocusFieldValidationDetail(BaseModel):
    """Validation report for an individual FOCUS column."""
    column_name: str
    is_valid: bool
    value_present: bool
    requirement_level: str = Field(..., description="Mandatory, Conditional, or Recommended")
    data_type_valid: bool
    enum_valid: Optional[bool] = None
    message: Optional[str] = None


class FocusValidationResult(BaseModel):
    """Overall FOCUS 1.0 validation assessment for a record."""
    is_compliant: bool
    total_columns_evaluated: int
    mandatory_columns_passed: int
    mandatory_columns_failed: int
    conditional_columns_passed: int
    recommended_columns_passed: int
    field_details: List[FocusFieldValidationDetail] = []
    compliance_score: Decimal = Field(..., description="FOCUS 1.0 conformance score percentage")


class FocusConformanceSummary(BaseModel):
    """Global conformance matrix summary across datasets."""
    focus_version: str = "1.0.0"
    specification_url: str = "https://focus.finops.org/"
    assessment_date: datetime
    total_evaluated_records: int
    fully_compliant_count: int
    conformance_percentage: Decimal
    mandatory_coverage_percentage: Decimal
    unsupported_columns: List[str] = []
    partially_supported_columns: List[str] = []
    fully_supported_columns: List[str] = []


class TagQualityAnalysisResult(BaseModel):
    """Quality and governance assessment for a resource's tags."""
    resource_id: str
    raw_tags_count: int
    normalized_tags_count: int
    sanitized_tags: Dict[str, str]
    extracted_owner: Optional[str]
    extracted_environment: Optional[str]
    extracted_cost_center: Optional[str]
    extracted_project: Optional[str]
    extracted_department: Optional[str]
    missing_mandatory_tags: List[str]
    quality_score: Decimal = Field(..., ge=0, le=100, description="Tag hygiene score (0 - 100%)")
    hygiene_rating: str = Field(..., description="EXCELLENT, GOOD, POOR, or UNTAGGED")


class QualityFindingResponse(BaseModel):
    """Individual data quality finding."""
    rule_id: str
    rule_name: str
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL")
    field_name: Optional[str]
    record_identifier: Optional[str]
    message: str
    suggested_remediation: Optional[str]


class DataQualityReportResponse(BaseModel):
    """Full data quality report representation."""
    report_id: uuid.UUID
    run_id: Optional[uuid.UUID]
    provider: Optional[str]
    overall_score: Decimal
    total_records_evaluated: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    informational_findings: int
    findings_summary: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NormalizationRunRequest(BaseModel):
    """Request to trigger a batch normalization or re-normalization."""
    provider: Optional[str] = Field(None, description="Optional provider filter (AWS, AZURE, GCP)")
    reprocess_all: bool = Field(default=False, description="Whether to reprocess historical records")
    start_date: Optional[date] = Field(None, description="Start date filter for reprocessing")
    end_date: Optional[date] = Field(None, description="End date filter for reprocessing")
    batch_size: int = Field(default=500, ge=10, le=5000, description="Processing batch size")


class NormalizationRunResponse(BaseModel):
    """Response representing an executed normalization run."""
    run_id: uuid.UUID
    status: str
    normalization_version: str
    mapping_version: str
    total_records: int
    successful_records: int
    failed_records: int
    warnings_count: int
    average_quality_score: Decimal
    started_at: datetime
    completed_at: Optional[datetime]
    error_details: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)
