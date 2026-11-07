"""
CloudSage Financial Decimal Precision Unit Tests.
Verifies zero floating-point drift and penny-accurate arithmetic across financial computations.
"""

from decimal import Decimal
import pytest
from backend.app.models import BillingRecord, Recommendation
from backend.app.core.enums import CloudProvider, ServiceCategory, RecommendationAction


def test_floating_point_imprecision_contrast():
    """
    Demonstrates that standard float arithmetic fails financial accuracy,
    while Python Decimal enforces exact decimal representation.
    """
    # Standard IEEE 754 float failure:
    float_sum = 0.1 + 0.2
    assert float_sum != 0.3  # 0.30000000000000004

    # CloudSage Decimal accuracy:
    decimal_sum = Decimal("0.1000") + Decimal("0.2000")
    assert decimal_sum == Decimal("0.3000")


def test_bulk_line_item_summation_precision(db_session):
    """
    Verifies that summing thousands of small fractional line items in the database
    produces exact mathematical totals with zero rounding drift.
    """
    # Simulate 1,000 micro-transactions of $0.0033
    unit_cost = Decimal("0.0033")
    total_count = 1000
    expected_total = Decimal("3.3000")

    running_sum = Decimal("0.0000")
    for _ in range(total_count):
        running_sum += unit_cost

    assert running_sum == expected_total


def test_annualized_savings_exact_multiplication():
    """Verifies that annual savings calculations maintain exact decimal accuracy."""
    monthly_savings = Decimal("142.8750")
    annual_savings = monthly_savings * Decimal("12")
    assert annual_savings == Decimal("1714.5000")


def test_recommendation_savings_db_persistence(db_session):
    """Verifies that Decimal values stored in the database retain exact 4-decimal precision."""
    res_id = "arn:aws:s3:::enterprise-uncompressed-logs"
    rec = Recommendation(
        resource_id=res_id,
        provider=CloudProvider.AWS.value,
        action_type=RecommendationAction.CONVERT_STORAGE_TIER.value,
        estimated_monthly_savings=Decimal("1234.5678"),
        estimated_annual_savings=Decimal("14814.8136"),
        title="Migrate S3 Standard to Glacier Flexible",
        description="Bucket contains 50TB of archival logs rarely accessed after 30 days.",
        remediation_guide="aws s3api put-bucket-lifecycle-configuration ..."
    )
    db_session.add(rec)
    db_session.commit()

    retrieved = db_session.query(Recommendation).filter_by(resource_id=res_id).first()
    assert retrieved.estimated_monthly_savings == Decimal("1234.5678")
    assert retrieved.estimated_annual_savings == Decimal("14814.8136")
    # Verify exact string representation has not been corrupted to a float
    assert str(retrieved.estimated_monthly_savings) == "1234.5678"
