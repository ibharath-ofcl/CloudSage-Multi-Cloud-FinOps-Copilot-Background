"""
Tests for Contribution Ranking and Pareto 80/20 Analysis Engine.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest

from backend.app.investigation.contribution_analysis import ContributionAnalysisEngine
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord


def _create_anomaly(db_session, total_excess=Decimal("1000.0000")):
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="STORAGE",
        service_name="AmazonS3",
        region="us-east-1",
        resource_id=None,
        anomaly_category="SERVICE_SPIKE",
        anomaly_date=date(2026, 3, 20),
        actual_cost=Decimal("1500.0000"),
        expected_cost=Decimal("500.0000"),
        estimated_excess_cost=total_excess,
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)
    db_session.commit()
    return anomaly


def test_single_contributor_ranking(db_session):
    """When a single resource drives the anomaly, pareto_80_count is 1 with 100% share."""
    anomaly = _create_anomaly(db_session)
    res = ContributionAnalysisEngine.rank_contributors(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    assert len(res.top_contributors) == 1
    top = res.top_contributors[0]
    assert top.rank == 1
    assert top.contribution_share == Decimal("100.00")
    assert top.cumulative_share == Decimal("100.00")
    assert res.pareto_80_count == 1


def test_pareto_multi_contributor(db_session):
    """Verifies that cumulative share accumulates correctly and pareto_80_count marks 80% threshold."""
    anomaly = _create_anomaly(db_session, total_excess=Decimal("1000.0000"))

    # Add 4 resources: 600 USD (60%), 250 USD (25%), 100 USD (10%), 50 USD (5%)
    costs = [Decimal("600.0000"), Decimal("250.0000"), Decimal("100.0000"), Decimal("50.0000")]
    for idx, c in enumerate(costs, start=1):
        b = BillingRecord(
            record_id=uuid.uuid4(),
            provider="AWS",
            billing_account_id="123456789012",
            subscription_id="123456789012",
            resource_id=f"bucket-00{idx}",
            resource_name=f"Bucket {idx}",
            service_category="STORAGE",
            service_name="AmazonS3",
            region="us-east-1",
            usage_start_time=datetime(2026, 3, 20, 1, 0, 0, tzinfo=timezone.utc),
            usage_end_time=datetime(2026, 3, 20, 2, 0, 0, tzinfo=timezone.utc),
            usage_quantity=Decimal("10.0000"),
            usage_unit="GB",
            unblended_cost=c,
            pricing_model="ON_DEMAND",
        )
        db_session.add(b)
    db_session.commit()

    res = ContributionAnalysisEngine.rank_contributors(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    assert len(res.top_contributors) == 4
    # First item: 60%
    assert res.top_contributors[0].contribution_share == Decimal("60.00")
    assert res.top_contributors[0].cumulative_share == Decimal("60.00")
    # Second item: 25%, cumulative 85% -> Reaches 80%
    assert res.top_contributors[1].contribution_share == Decimal("25.00")
    assert res.top_contributors[1].cumulative_share == Decimal("85.00")
    # Pareto 80 count should be 2
    assert res.pareto_80_count == 2


def test_contributor_ranking_order(db_session):
    """Verifies contributors are strictly ordered descending by excess cost."""
    anomaly = _create_anomaly(db_session)
    for idx, c in enumerate([Decimal("100.0000"), Decimal("800.0000"), Decimal("300.0000")], start=1):
        b = BillingRecord(
            record_id=uuid.uuid4(),
            provider="AWS",
            billing_account_id="123456789012",
            subscription_id="123456789012",
            resource_id=f"res-{idx}",
            service_category="STORAGE",
            service_name="AmazonS3",
            region="us-east-1",
            usage_start_time=datetime(2026, 3, 20, 1, 0, 0, tzinfo=timezone.utc),
            usage_end_time=datetime(2026, 3, 20, 2, 0, 0, tzinfo=timezone.utc),
            unblended_cost=c,
            usage_quantity=Decimal("1.00"),
            usage_unit="GB",
            pricing_model="ON_DEMAND",
        )
        db_session.add(b)
    db_session.commit()

    res = ContributionAnalysisEngine.rank_contributors(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )

    # Top contributor should be res-2 with 800 USD
    assert res.top_contributors[0].entity_id == "res-2"
    assert res.top_contributors[1].entity_id == "res-3"
    assert res.top_contributors[2].entity_id == "res-1"


def test_confidence_tier_assignment(db_session):
    """Top 3 contributors receive HIGH confidence tier."""
    anomaly = _create_anomaly(db_session)
    res = ContributionAnalysisEngine.rank_contributors(
        db=db_session,
        anomaly=anomaly,
        investigation_id=uuid.uuid4(),
    )
    assert res.top_contributors[0].confidence_category == "HIGH"
