"""
CloudSage Inventory Quality Evaluator Tests.
Verifies completeness scoring, tag governance grading, severity-tiered findings, and report persistence.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from backend.app.inventory.quality import InventoryQualityEvaluator
from backend.app.models.inventory import InventoryQualityReport
from backend.app.models.resource import CloudResource


def test_inventory_quality_pristine_resource(db_session: Session):
    now = datetime.now(timezone.utc)
    res = CloudResource(
        resource_id="arn:aws:ec2:us-east-1:111:instance/i-pristine",
        provider="AWS",
        account_id="111",
        resource_name="pristine-box",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="active",
        tags={"environment": "production", "owner": "lead@cloud.com"},
        owner="lead@cloud.com",
        department="FinOps",
        project="CostOptimization",
        environment="production",
        cost_center="CC-100",
        tag_quality_score=Decimal("100.00"),
        first_discovered_at=now,
        last_seen_at=now,
        last_inventory_sync_at=now,
        discovery_status="CONFIRMED",
    )
    db_session.add(res)
    db_session.commit()

    report = InventoryQualityEvaluator.evaluate(db=db_session, provider="AWS", persist=True)
    assert report.total_resources == 1
    assert report.completeness_score == Decimal("100.00")
    assert report.tag_completeness_score == Decimal("100.00")
    assert report.inventory_confidence == Decimal("1.0000")
    assert report.critical_findings == 0
    assert report.high_findings == 0


def test_inventory_quality_critical_and_high_violations(db_session: Session):
    now = datetime.now(timezone.utc)
    res_bad = CloudResource(
        resource_id="arn:aws:ec2:us-east-1:111:instance/i-bad-tags",
        provider="AWS",
        account_id="111",
        service_category="COMPUTE",
        service_name="AmazonEC2",
        resource_type="ec2:instance",
        region="us-east-1",
        status="unknown",
        tags={},
        owner=None,  # CRITICAL: Missing owner
        environment="unknown",  # HIGH: Unknown environment
        project=None,
        cost_center=None,  # MEDIUM: Missing cost allocation
        tag_quality_score=Decimal("0.00"),
        first_discovered_at=now - timedelta(days=25),
        last_seen_at=now - timedelta(days=25),
        last_inventory_sync_at=now - timedelta(days=25),
        discovery_status="STALE",  # HIGH: Stale resource
    )
    db_session.add(res_bad)
    db_session.commit()

    report = InventoryQualityEvaluator.evaluate(db=db_session, provider="AWS", persist=True)
    assert report.total_resources == 1
    assert report.critical_findings >= 1
    assert report.high_findings >= 1
    assert report.completeness_score < Decimal("50.00")
    assert report.tag_completeness_score == Decimal("0.00")
    assert report.inventory_confidence < Decimal("0.5000")

    # Verify saved to database
    db_report = db_session.query(InventoryQualityReport).filter(InventoryQualityReport.report_id == report.report_id).first()
    assert db_report is not None
