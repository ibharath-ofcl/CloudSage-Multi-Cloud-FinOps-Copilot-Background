"""
CloudSage Pydantic Schemas Unit Tests.
Validates input serialization, type coercion, and enum integrity.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest
from pydantic import ValidationError
from backend.app.schemas import (
    BillingRecordCreate,
    CloudResourceCreate,
    WasteDetectionCreate,
    RecommendationCreate,
    CostAnomalyCreate,
    UserCreate,
)
from backend.app.core.enums import (
    CloudProvider,
    ServiceCategory,
    WasteType,
    Severity,
    RecommendationAction,
    Priority,
    RiskLevel,
    UserRole,
)


def test_billing_record_schema_valid():
    payload = {
        "provider": "AWS",
        "billing_account_id": "123456789012",
        "subscription_id": "123456789012",
        "resource_id": "arn:aws:ec2:us-east-1:123456789012:instance/i-test",
        "service_category": "COMPUTE",
        "service_name": "AmazonEC2",
        "region": "us-east-1",
        "usage_start_time": datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
        "usage_end_time": datetime(2026, 11, 1, 1, 0, 0, tzinfo=timezone.utc),
        "usage_quantity": Decimal("1.0"),
        "usage_unit": "HOURS",
        "unblended_cost": Decimal("0.0960"),
        "tags": {"owner": "platform", "env": "prod"}
    }
    record = BillingRecordCreate(**payload)
    assert record.provider == CloudProvider.AWS
    assert record.unblended_cost == Decimal("0.0960")
    assert record.tags["owner"] == "platform"


def test_billing_record_schema_invalid_negative_cost():
    payload = {
        "provider": "AWS",
        "billing_account_id": "123456789012",
        "subscription_id": "123456789012",
        "resource_id": "arn:aws:ec2:us-east-1:123456789012:instance/i-test",
        "service_category": "COMPUTE",
        "service_name": "AmazonEC2",
        "region": "us-east-1",
        "usage_start_time": datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
        "usage_end_time": datetime(2026, 11, 1, 1, 0, 0, tzinfo=timezone.utc),
        "usage_quantity": Decimal("1.0"),
        "usage_unit": "HOURS",
        "unblended_cost": Decimal("-5.0000"),  # Invalid negative cost
    }
    with pytest.raises(ValidationError):
        BillingRecordCreate(**payload)


def test_waste_detection_schema_valid():
    payload = {
        "resource_id": "vol-0123456789abcdef0",
        "provider": "AWS",
        "waste_type": "UNATTACHED_DISK",
        "severity": "MEDIUM",
        "estimated_monthly_waste": Decimal("40.0000"),
        "telemetry_proof": {"attachment_state": "available", "days_unattached": 14}
    }
    waste = WasteDetectionCreate(**payload)
    assert waste.waste_type == WasteType.UNATTACHED_DISK
    assert waste.estimated_monthly_waste == Decimal("40.0000")


def test_recommendation_schema_valid():
    payload = {
        "resource_id": "vol-0123456789abcdef0",
        "provider": "AWS",
        "action_type": "TERMINATE",
        "priority": "P2",
        "risk_level": "LOW",
        "estimated_monthly_savings": Decimal("40.0000"),
        "estimated_annual_savings": Decimal("480.0000"),
        "implementation_effort": "LOW",
        "title": "Delete Unattached EBS Volume",
        "description": "Volume unattached for 14 days.",
        "remediation_guide": "aws ec2 delete-volume --volume-id vol-0123456789abcdef0"
    }
    rec = RecommendationCreate(**payload)
    assert rec.action_type == RecommendationAction.TERMINATE
    assert rec.priority == Priority.P2
    assert rec.estimated_annual_savings == Decimal("480.0000")


def test_user_create_schema_password_length():
    with pytest.raises(ValidationError):
        UserCreate(
            email="invalid@user.com",
            full_name="Shorty",
            password="123"  # Shorter than 8 chars
        )
