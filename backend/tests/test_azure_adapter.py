"""
CloudSage Azure Ingestion Adapter Unit Tests.
Category B: Valid Cost Management export, missing IDs, tag normalization, and column variations.
"""

from decimal import Decimal
import io
import pytest
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.adapters.azure.adapter import AzureCostAdapter
from backend.app.ingestion.adapters.azure.parser import AzureCostParser


def test_azure_valid_cost_export_parsing():
    csv_data = """BillingAccountId,SubscriptionId,ResourceGroup,ResourceId,ResourceName,MeterCategory,MeterSubCategory,ConsumedService,Date,Quantity,UnitOfMeasure,CostInBillingCurrency,BillingCurrency,ResourceLocation,PricingModel,Tags
EA-101,00000000-0000-0000-0000-000000000001,rg-prod,/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-prod/providers/Microsoft.Compute/virtualMachines/vm-prod-01,vm-prod-01,Virtual Machines,D Series,Virtual Machines,2026-11-01,10.0,Hours,1.9200,USD,eastus,OnDemand,"{""owner"": ""platform-team"", ""env"": ""prod""}"
"""
    adapter = AzureCostAdapter()
    stream = io.StringIO(csv_data)
    items = list(adapter.parse_stream(stream))

    assert len(items) == 1
    item = items[0]
    assert item.provider == CloudProvider.AZURE
    assert item.billing_account_id == "EA-101"
    assert item.subscription_id == "00000000-0000-0000-0000-000000000001"
    assert item.service_category == ServiceCategory.COMPUTE
    assert item.service_name == "Virtual Machines"
    assert item.resource_id == "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-prod/providers/Microsoft.Compute/virtualMachines/vm-prod-01"
    assert item.unblended_cost == Decimal("1.9200")
    assert isinstance(item.unblended_cost, Decimal)
    assert item.tags["owner"] == "platform-team"
    assert item.tags["env"] == "prod"
    assert item.tags["resource_group"] == "rg-prod"


def test_azure_missing_resource_id():
    """Verifies fallback resource URI generation when ResourceId is empty."""
    csv_data = """BillingAccountId,SubscriptionId,ResourceGroup,MeterCategory,ConsumedService,Date,Quantity,UnitOfMeasure,CostInBillingCurrency
EA-102,sub-123,rg-backend,Storage,Storage Accounts,2026-11-01,50.0,GB,0.9200
"""
    adapter = AzureCostAdapter()
    stream = io.StringIO(csv_data)
    items = list(adapter.parse_stream(stream))

    assert len(items) == 1
    item = items[0]
    assert item.service_category == ServiceCategory.STORAGE
    assert "sub-123" in item.resource_id
    assert "rg-backend" in item.resource_id
    assert item.unblended_cost == Decimal("0.9200")


def test_azure_tag_parsing_variations():
    """Verifies that Azure tag parsing handles JSON, key:value strings, and malformed strings."""
    # JSON dictionary
    tags1 = AzureCostParser.parse_azure_tags('{"Owner": "sre", "Department": "Core"}')
    assert tags1["owner"] == "sre"
    assert tags1["department"] == "Core"

    # Colon-separated string
    tags2 = AzureCostParser.parse_azure_tags("Owner: data-eng, env: staging")
    assert tags2["owner"] == "data-eng"
    assert tags2["env"] == "staging"

    # Empty or null
    assert AzureCostParser.parse_azure_tags("") == {}
    assert AzureCostParser.parse_azure_tags("null") == {}
    assert AzureCostParser.parse_azure_tags("{}") == {}


def test_azure_column_variations():
    """Verifies support for PreTaxCost, UsageDateTime, and casing variations."""
    csv_data = """billingAccountId,subscriptionGuid,resourceGroupName,PreTaxCost,usageDateTime,meterCategory,consumedService
EA-103,guid-555,rg-data,15.7500,11/01/2026,SQL Database,Azure SQL
"""
    adapter = AzureCostAdapter()
    stream = io.StringIO(csv_data)
    items = list(adapter.parse_stream(stream))

    assert len(items) == 1
    item = items[0]
    assert item.subscription_id == "guid-555"
    assert item.service_category == ServiceCategory.DATABASE
    assert item.unblended_cost == Decimal("15.7500")
