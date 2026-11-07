"""
CloudSage AWS Ingestion Adapter Unit Tests.
Category A: Valid CUR, missing fields, column variations, and decimal precision.
"""

from decimal import Decimal
import io
import pytest
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.adapters.aws.adapter import AWSCurAdapter
from backend.app.ingestion.adapters.aws.parser import AWSCurParser


def test_aws_valid_cur_parsing():
    csv_data = """identity/LineItemId,bill/PayerAccountId,lineItem/UsageAccountId,lineItem/LineItemType,lineItem/UsageStartDate,lineItem/UsageEndDate,lineItem/ProductCode,lineItem/UsageAmount,pricing/unit,lineItem/UnblendedCost,lineItem/CurrencyCode,lineItem/ResourceId,product/region,resourceTags/user:Owner,resourceTags/user:Environment
line-001,112233445566,112233445566,Usage,2026-11-01T00:00:00Z,2026-11-01T01:00:00Z,AmazonEC2,1.0,HOURS,0.0960,USD,arn:aws:ec2:us-east-1:112233445566:instance/i-001,us-east-1,checkout-team,production
"""
    adapter = AWSCurAdapter()
    stream = io.StringIO(csv_data)
    items = list(adapter.parse_stream(stream))

    assert len(items) == 1
    item = items[0]
    assert item.provider == CloudProvider.AWS
    assert item.billing_account_id == "112233445566"
    assert item.subscription_id == "112233445566"
    assert item.service_category == ServiceCategory.COMPUTE
    assert item.service_name == "AmazonEC2"
    assert item.resource_id == "arn:aws:ec2:us-east-1:112233445566:instance/i-001"
    assert item.unblended_cost == Decimal("0.0960")
    assert isinstance(item.unblended_cost, Decimal)
    assert item.tags["owner"] == "checkout-team"
    assert item.tags["environment"] == "production"


def test_aws_missing_optional_fields():
    """Verifies that missing ResourceId, tags, and zone are handled defensively."""
    csv_data = """identity/LineItemId,lineItem/UsageAccountId,lineItem/ProductCode,lineItem/UsageStartDate,lineItem/UsageEndDate,lineItem/UsageAmount,lineItem/UnblendedCost
line-002,112233445566,AmazonS3,2026-11-01T00:00:00Z,2026-11-01T01:00:00Z,10.5,0.2415
"""
    adapter = AWSCurAdapter()
    stream = io.StringIO(csv_data)
    items = list(adapter.parse_stream(stream))

    assert len(items) == 1
    item = items[0]
    assert item.service_category == ServiceCategory.STORAGE
    assert item.resource_id != ""  # Auto-generated fallback identifier
    assert item.tags == {}
    assert item.zone is None
    assert item.unblended_cost == Decimal("0.2415")


def test_aws_column_variations():
    """Verifies support for legacy and alternate column header names."""
    csv_data = """LineItemId,UsageAccountId,ProductCode,UsageStartDate,UsageEndDate,UsageAmount,UnblendedCost,Unit,CurrencyCode,ResourceId
line-003,998877665544,AmazonRDS,2026-11-01T00:00:00Z,2026-11-01T01:00:00Z,2.0,0.4800,Hrs,USD,arn:aws:rds:us-east-1:998877665544:db:orders-db
"""
    adapter = AWSCurAdapter()
    stream = io.StringIO(csv_data)
    items = list(adapter.parse_stream(stream))

    assert len(items) == 1
    item = items[0]
    assert item.subscription_id == "998877665544"
    assert item.service_category == ServiceCategory.DATABASE
    assert item.service_name == "AmazonRDS"
    assert item.unblended_cost == Decimal("0.4800")
    assert item.resource_id == "arn:aws:rds:us-east-1:998877665544:db:orders-db"


def test_aws_pricing_model_mapping():
    assert AWSCurParser.map_pricing_model("Spot") == PricingModel.SPOT
    assert AWSCurParser.map_pricing_model("SavingsPlanCoveredUsage") == PricingModel.SAVINGS_PLAN
    assert AWSCurParser.map_pricing_model("DiscountedUsage") == PricingModel.RESERVED
    assert AWSCurParser.map_pricing_model("Usage") == PricingModel.ON_DEMAND


def test_aws_service_category_comprehensive_mapping():
    assert AWSCurParser.map_service_category("AmazonEC2") == ServiceCategory.COMPUTE
    assert AWSCurParser.map_service_category("AWSLambda") == ServiceCategory.COMPUTE
    assert AWSCurParser.map_service_category("AmazonS3") == ServiceCategory.STORAGE
    assert AWSCurParser.map_service_category("AmazonEBS") == ServiceCategory.STORAGE
    assert AWSCurParser.map_service_category("AmazonRDS") == ServiceCategory.DATABASE
    assert AWSCurParser.map_service_category("AmazonCloudWatch") == ServiceCategory.MANAGEMENT
    assert AWSCurParser.map_service_category("AWSKMS") == ServiceCategory.SECURITY
    assert AWSCurParser.map_service_category("AmazonSageMaker") == ServiceCategory.AI_ML
    assert AWSCurParser.map_service_category("AmazonAthena") == ServiceCategory.ANALYTICS
    assert AWSCurParser.map_service_category("UnknownServiceCode") == ServiceCategory.OTHER
