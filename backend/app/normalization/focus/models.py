"""
CloudSage FOCUS 1.0 Specification Data Models.
Implements the FinOps Open Cost & Usage Specification (FOCUS) 1.0 standard schema.
Reference: https://focus.finops.org/
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class FocusChargeCategory(str, Enum):
    """FOCUS 1.0 ChargeCategory Allowed Values."""
    USAGE = "Usage"
    PURCHASE = "Purchase"
    TAX = "Tax"
    CREDIT = "Credit"
    ADJUSTMENT = "Adjustment"
    FEE = "Fee"


class FocusPricingCategory(str, Enum):
    """FOCUS 1.0 PricingCategory Allowed Values."""
    ON_DEMAND = "On-Demand"
    COMMITTED = "Committed"
    SPOT = "Spot"
    DYNAMIC = "Dynamic"
    TIERED = "Tiered"
    STANDARD = "Standard"
    OTHER = "Other"


class FocusServiceCategory(str, Enum):
    """FOCUS 1.0 ServiceCategory Standard Classes."""
    COMPUTE = "Compute"
    STORAGE = "Storage"
    DATABASE = "Database"
    NETWORK = "Network"
    ANALYTICS = "Analytics"
    AI_AND_ML = "AI and Machine Learning"
    SECURITY = "Security"
    MANAGEMENT_AND_GOV = "Management and Governance"
    OTHER = "Other"


class Focus10Record(BaseModel):
    """
    Formal FOCUS 1.0 Specification Normalized Record.
    Adheres strictly to official FinOps Foundation schema conventions.
    """
    # Mandatory Core Dimensions
    BillingAccountId: str = Field(..., description="Top-level billing account ID")
    BillingAccountName: Optional[str] = Field(None, description="Display name for billing account")
    BillingCurrency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    BillingPeriodStart: Optional[datetime] = Field(None, description="Start of invoice billing cycle (UTC)")
    BillingPeriodEnd: Optional[datetime] = Field(None, description="End of invoice billing cycle (UTC)")

    ChargeCategory: FocusChargeCategory = Field(default=FocusChargeCategory.USAGE, description="Category of charge")
    ChargeClass: Optional[str] = Field(None, description="Correction or Reversal classification")
    ChargeDescription: Optional[str] = Field(None, description="Human readable charge description")
    ChargeFrequency: Optional[str] = Field(None, description="One-Time, Recurring, or Usage-Based")
    ChargePeriodStart: datetime = Field(..., description="Billing interval start (UTC)")
    ChargePeriodEnd: datetime = Field(..., description="Billing interval end (UTC)")

    # Consumption & Pricing Dimensions
    ConsumedQuantity: Optional[Decimal] = Field(None, ge=0, description="Measured quantity of resource consumed")
    ConsumedUnit: Optional[str] = Field(None, description="Unit of consumption")
    BilledCost: Decimal = Field(..., ge=0, description="Direct cash charge on invoice in USD")
    EffectiveCost: Decimal = Field(..., ge=0, description="Cost reflecting amortized commitments/credits")
    ListCost: Optional[Decimal] = Field(None, ge=0, description="Public retail price before discounts")
    PricingCategory: FocusPricingCategory = Field(default=FocusPricingCategory.ON_DEMAND, description="Commitment category")

    # Cloud Provider & Resource Dimensions
    ProviderName: str = Field(..., description="AWS, Microsoft Azure, Google Cloud Platform")
    PublisherName: Optional[str] = Field(None, description="Publisher or Marketplace vendor")
    RegionId: Optional[str] = Field(None, description="Standardized geographic region ID")
    RegionName: Optional[str] = Field(None, description="Human readable region name")
    ResourceId: Optional[str] = Field(None, description="Unique cloud resource identifier or ARN")
    ResourceName: Optional[str] = Field(None, description="Resource name or tag display")
    ResourceType: Optional[str] = Field(None, description="Provider resource type definition")

    # Taxonomy & Organization Dimensions
    ServiceCategory: FocusServiceCategory = Field(..., description="Normalized FOCUS service category")
    ServiceName: str = Field(..., description="Service product name")
    SubAccountId: Optional[str] = Field(None, description="Subscription ID, Project ID, or Linked Account ID")
    SubAccountName: Optional[str] = Field(None, description="Display name for sub-account")
    Tags: Dict[str, str] = Field(default_factory=dict, description="Clean resource metadata tags")

    # Provider Extension Dimensions (x_ prefix per FOCUS 1.0 guidelines)
    x_OriginalCost: Optional[Decimal] = Field(None, description="Original un-normalized cost before FX")
    x_OriginalCurrency: Optional[str] = Field(None, description="Original billing currency before FX")
    x_Fingerprint: Optional[str] = Field(None, description="SHA-256 deduplication fingerprint")

    model_config = ConfigDict(populate_by_name=True)
