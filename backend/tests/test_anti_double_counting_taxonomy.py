"""
Tests for Anti-Double-Counting Guarantees and Financial Taxonomy.
Verifies strict mathematical separation between baseline spend, avoidable waste,
potential savings, and verified realized savings.
"""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection
from backend.app.services.correlation import CorrelationService


@pytest.fixture
def taxonomy_client(db_session):
    return TestClient(app)


def test_correlation_anti_double_counting_taxonomy(db_session):
    res_id = "arn:aws:ec2:us-east-1:123456789012:instance/i-taxonomy01"
    res = CloudResource(
        resource_id=res_id,
        provider="AWS",
        account_id="123456789012",
        region="us-east-1",
        service_name="AmazonEC2",
        service_category="COMPUTE",
        resource_type="ec2_instance",
        status="active",
        monthly_cost=Decimal("1000.0000"),
        first_discovered_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(res)

    # 1. Active Waste finding: $300/mo
    waste = WasteDetection(
        id=uuid.uuid4(),
        resource_id=res_id,
        provider="AWS",
        waste_type="IDLE_VM",
        severity="HIGH",
        status="ACTIVE",
        estimated_monthly_waste=Decimal("300.0000"),
        first_detected_at=datetime.now(timezone.utc),
        last_evaluated_at=datetime.now(timezone.utc),
    )
    db_session.add(waste)

    # 2. Proposed Recommendation: $300/mo potential savings
    rec = Recommendation(
        id=uuid.uuid4(),
        recommendation_key="tax-rec-01",
        resource_id=res_id,
        provider="AWS",
        action_type="RIGHTSIZE",
        priority="P1",
        status="PROPOSED",
        estimated_monthly_savings=Decimal("300.0000"),
        estimated_annual_savings=Decimal("3600.0000"),
        title="Rightsize i-taxonomy01",
        description="Downsize",
        remediation_guide="Modify",
    )
    db_session.add(rec)

    # 3. Verified Recommendation on same resource (historical): $100 realized savings
    rec_verified = Recommendation(
        id=uuid.uuid4(),
        recommendation_key="tax-rec-ver",
        resource_id=res_id,
        provider="AWS",
        action_type="CONVERT_STORAGE_TIER",
        priority="P3",
        status="VERIFIED",
        estimated_monthly_savings=Decimal("100.0000"),
        verified_savings=Decimal("100.0000"),
        estimated_annual_savings=Decimal("1200.0000"),
        title="Storage tier conversion",
        description="Convert",
        remediation_guide="Tier",
    )
    db_session.add(rec_verified)

    # 4. Cost Anomaly: $150 spike
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_name="AmazonEC2",
        service_category="COMPUTE",
        region="us-east-1",
        resource_id=res_id,
        anomaly_category="RESOURCE_SPIKE",
        severity="HIGH",
        status="OPEN",
        actual_cost=Decimal("1150.0000"),
        expected_cost=Decimal("1000.0000"),
        estimated_excess_cost=Decimal("150.0000"),
        z_score=Decimal("3.8500"),
        anomaly_date=datetime.now(timezone.utc).date(),
        detected_at=datetime.now(timezone.utc),
    )
    db_session.add(anomaly)
    db_session.commit()

    # Query correlation service
    corr = CorrelationService.get_resource_correlations(db_session, resource_id=res_id)

    taxonomy = corr["financial_taxonomy"]
    assert taxonomy["currency"] == "USD"
    # Strict separation guarantees:
    assert taxonomy["baseline_monthly_spend"] == 1000.0
    assert taxonomy["active_monthly_waste"] == 300.0
    assert taxonomy["potential_monthly_savings"] == 400.0  # 300 + 100
    assert taxonomy["verified_realized_savings"] == 100.0
    # Note must explain not adding waste and savings together
    assert "anti_double_counting_note" in taxonomy
    assert "Do not add waste and savings together" in taxonomy["anti_double_counting_note"]
