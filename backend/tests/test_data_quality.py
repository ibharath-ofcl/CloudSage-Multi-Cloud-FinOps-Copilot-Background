"""
CloudSage Data Quality Engine & Framework Tests.
Verifies quality rule violations, severity tiering, overall scoring, and report persistence.
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from backend.app.normalization.quality.evaluator import DataQualityEngine
from backend.app.normalization.quality.models import QualitySeverity
from backend.app.normalization.quality.service import DataQualityService


def test_data_quality_pristine_record():
    """Verify that a complete, valid record triggers zero findings."""
    record = {
        "provider": "AWS",
        "billing_account_id": "acc-12345",
        "resource_id": "arn:aws:ec2:us-east-1:12345:instance/i-abc",
        "service_name": "AmazonEC2",
        "service_category": "COMPUTE",
        "unblended_cost": Decimal("25.0000"),
        "currency": "USD",
        "usage_start_time": datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        "usage_end_time": datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
        "usage_unit": "HOURS",
        "tags": {"owner": "devops@company.com", "environment": "production"},
    }

    findings = DataQualityEngine.evaluate_record(record)
    assert len(findings) == 0


def test_data_quality_critical_violations():
    """Verify missing mandatory fields and inverted timestamps are flagged as CRITICAL."""
    # Inverted timestamps
    record_inverted = {
        "provider": "AWS",
        "billing_account_id": "acc-12345",
        "resource_id": "i-123",
        "service_name": "AmazonEC2",
        "service_category": "COMPUTE",
        "unblended_cost": Decimal("10.00"),
        "currency": "USD",
        "usage_start_time": datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc),
        "usage_end_time": datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc), # Start > End
        "tags": {"owner": "devops"},
    }
    findings = DataQualityEngine.evaluate_record(record_inverted)
    critical_rules = [f.rule_id for f in findings if f.severity == QualitySeverity.CRITICAL]
    assert "DQ-004" in critical_rules


def test_data_quality_negative_cost_and_invalid_currency():
    """Verify negative cost is flagged as CRITICAL and invalid currency is flagged as HIGH."""
    record = {
        "provider": "AWS",
        "billing_account_id": "acc-123",
        "resource_id": "i-123",
        "service_name": "AmazonEC2",
        "unblended_cost": Decimal("-50.00"),  # Negative
        "currency": "INVALID_CURRENCY",       # Invalid
        "usage_start_time": datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
        "usage_end_time": datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
    }

    findings = DataQualityEngine.evaluate_record(record)
    severities = {f.severity for f in findings}
    assert QualitySeverity.CRITICAL in severities
    assert QualitySeverity.HIGH in severities


def test_data_quality_batch_scoring_and_persistence(db_session):
    """Verify batch evaluation calculates overall score and persists report."""
    records = [
        # Clean record
        {
            "provider": "AWS",
            "billing_account_id": "acc-1",
            "resource_id": "arn:aws:s3:::bucket-1",
            "service_name": "AmazonS3",
            "service_category": "STORAGE",
            "unblended_cost": Decimal("5.00"),
            "currency": "USD",
            "usage_start_time": datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
            "usage_end_time": datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
            "usage_unit": "GB_MONTH",
            "tags": {"owner": "data-team", "environment": "production"},
        },
        # Record with missing tags (medium/low findings)
        {
            "provider": "AWS",
            "billing_account_id": "acc-1",
            "resource_id": "arn:aws:s3:::bucket-2",
            "service_name": "AmazonS3",
            "service_category": "STORAGE",
            "unblended_cost": Decimal("10.00"),
            "currency": "USD",
            "usage_start_time": datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc),
            "usage_end_time": datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
            "usage_unit": "GB_MONTH",
            "tags": {},
        },
    ]

    report = DataQualityService.evaluate_and_persist(db_session, records=records, provider="AWS")
    assert report.total_records_evaluated == 2
    assert report.overall_score > Decimal("90.00")
    assert report.overall_score <= Decimal("100.00")
    assert report.medium_findings >= 1

    # Verify retrieval
    latest = DataQualityService.get_latest_report(db_session, provider="AWS")
    assert latest is not None
    assert latest.report_id == report.report_id
