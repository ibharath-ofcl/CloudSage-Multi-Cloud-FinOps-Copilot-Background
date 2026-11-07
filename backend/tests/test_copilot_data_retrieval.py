"""
Unit Tests for Copilot Safe Data Retrieval Engine.
Verifies cross-stage querying across BillingRecord, CostAnomaly, WasteDetection,
Recommendation, and CloudResource, enforcing the Zero Float Rule.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest

from backend.app.core.enums import CloudProvider, CopilotIntent, Priority, RecommendationAction, RecommendationStatus, Severity, WasteStatus, WasteType
from backend.app.copilot.citations import CitationBuilder
from backend.app.copilot.data_retrieval import DataRetrievalEngine
from backend.app.copilot.query_planner import QueryPlan
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection


@pytest.fixture
def populated_db(db_session):
    """Seeds test data across all stages."""
    now = datetime.now(timezone.utc)

    # 1. Cloud Resources (first, for FK references)
    res1 = CloudResource(
        resource_id="i-0123456789abcdef0",
        provider=CloudProvider.AWS.value,
        account_id="111122223333",
        region="us-east-1",
        service_category="COMPUTE",
        service_name="Amazon EC2",
        resource_type="ec2_instance",
        resource_name="web-prod-01",
        status="running",
        last_seen_at=now,
    )
    res2 = CloudResource(
        resource_id="vm-legacy-test",
        provider=CloudProvider.AZURE.value,
        account_id="sub-azure-01",
        region="eastus",
        service_category="COMPUTE",
        service_name="Virtual Machines",
        resource_type="virtual_machine",
        resource_name="vm-legacy-test",
        status="running",
        last_seen_at=now,
    )
    db_session.add(res1)
    db_session.add(res2)
    db_session.flush()

    # 2. Billing record
    b1 = BillingRecord(
        record_id=uuid.uuid4(),
        provider=CloudProvider.AWS.value,
        billing_account_id="111122223333",
        subscription_id="sub-aws-01",
        resource_id="i-0123456789abcdef0",
        service_category="COMPUTE",
        service_name="Amazon EC2",
        region="us-east-1",
        usage_start_time=now - timedelta(days=2),
        usage_end_time=now - timedelta(days=1),
        usage_quantity=Decimal("24.000000"),
        usage_unit="Hours",
        unblended_cost=Decimal("150.2500"),
        currency="USD",
        tags={"owner": "data_eng", "env": "prod"},
    )
    db_session.add(b1)

    # 3. Anomaly
    a1 = CostAnomaly(
        id=uuid.uuid4(),
        detector_id="statistical_anomaly_detector",
        detector_version="1.0.0",
        provider=CloudProvider.AWS.value,
        account_id="111122223333",
        service_category="DATABASE",
        service_name="Amazon RDS",
        region="us-east-1",
        resource_id="db-prod-cluster",
        anomaly_category="SERVICE_SPIKE",
        severity=Severity.HIGH.value,
        status="OPEN",
        anomaly_date=now.date(),
        actual_cost=Decimal("600.0000"),
        expected_cost=Decimal("149.2500"),
        estimated_excess_cost=Decimal("450.7500"),
        detected_at=now,
    )
    db_session.add(a1)

    # 4. Waste detection
    w1 = WasteDetection(
        id=uuid.uuid4(),
        provider=CloudProvider.AZURE.value,
        account_id="sub-azure-01",
        resource_id="vm-legacy-test",
        waste_type=WasteType.IDLE_VM.value,
        severity=Severity.MEDIUM.value,
        status=WasteStatus.ACTIVE.value,
        estimated_monthly_waste=Decimal("220.0000"),
        detected_at=now,
    )
    db_session.add(w1)

    # 5. Recommendation
    r1 = Recommendation(
        id=uuid.uuid4(),
        recommendation_key="rec-key-001",
        provider=CloudProvider.GCP.value,
        title="Rightsize oversized GCE VM",
        description="Downsize e2-standard-8 to e2-standard-4",
        remediation_guide="Downsize VM via gcloud compute instances set-machine-type",
        strategy_id="compute_rightsizing",
        action_type=RecommendationAction.RIGHTSIZE.value,
        priority=Priority.P1.value,
        status=RecommendationStatus.PROPOSED.value,
        estimated_monthly_savings=Decimal("180.5000"),
        estimated_annual_savings=Decimal("2166.0000"),
        current_monthly_cost=Decimal("300.0000"),
        projected_monthly_cost=Decimal("119.5000"),
        created_at=now,
    )
    db_session.add(r1)

    db_session.commit()
    return db_session


def test_retrieve_billing_data(populated_db):
    """Verify safe retrieval and Decimal aggregation for billing records."""
    plan = QueryPlan(
        intent=CopilotIntent.TOTAL_CLOUD_SPEND,
        target_dataset="billing_records",
        filters={"provider": "AWS"},
        aggregations=["SUM:unblended_cost"],
        group_by=["provider"],
    )
    res = DataRetrievalEngine.execute(populated_db, plan)

    assert isinstance(res["total_metric"], Decimal)
    assert res["total_metric"] == Decimal("150.2500")
    assert res["record_count"] == 1
    assert len(res["breakdown"]) == 1
    assert res["breakdown"][0]["dimension"] == "AWS"
    assert res["breakdown"][0]["cost"] == Decimal("150.2500")

    # Verify citation generation
    citations = CitationBuilder.build_citations("billing_records", res["sample_records"])
    assert len(citations) == 1
    assert "Amazon EC2" in citations[0].description
    assert citations[0].source_table == "billing_records"


def test_retrieve_anomalies_data(populated_db):
    """Verify safe retrieval of cost anomalies."""
    plan = QueryPlan(
        intent=CopilotIntent.COST_ANOMALY_EXPLANATION,
        target_dataset="cost_anomalies",
        filters={"status": "OPEN"},
        aggregations=["SUM:estimated_excess_cost"],
        group_by=["anomaly_category"],
    )
    res = DataRetrievalEngine.execute(populated_db, plan)

    assert isinstance(res["total_metric"], Decimal)
    assert res["total_metric"] == Decimal("450.7500")
    assert res["record_count"] == 1
    assert res["breakdown"][0]["dimension"] == "SERVICE_SPIKE"

    citations = CitationBuilder.build_citations("cost_anomalies", res["sample_records"])
    assert len(citations) == 1
    assert "Amazon RDS" in citations[0].description


def test_retrieve_waste_data(populated_db):
    """Verify safe retrieval of cloud waste items."""
    plan = QueryPlan(
        intent=CopilotIntent.WASTE_DETECTION_ANALYSIS,
        target_dataset="waste_detections",
        filters={"status": "ACTIVE"},
        aggregations=["SUM:estimated_monthly_waste"],
        group_by=["waste_type"],
    )
    res = DataRetrievalEngine.execute(populated_db, plan)

    assert isinstance(res["total_metric"], Decimal)
    assert res["total_metric"] == Decimal("220.0000")
    assert res["record_count"] == 1
    assert res["breakdown"][0]["dimension"] == WasteType.IDLE_VM.value

    citations = CitationBuilder.build_citations("waste_detections", res["sample_records"])
    assert len(citations) == 1
    assert "vm-legacy-test" in citations[0].description


def test_retrieve_recommendations_data(populated_db):
    """Verify safe retrieval of advisory recommendations."""
    plan = QueryPlan(
        intent=CopilotIntent.OPTIMIZATION_RECOMMENDATIONS,
        target_dataset="recommendations",
        filters={"status": "PROPOSED"},
        aggregations=["SUM:estimated_monthly_savings"],
        group_by=["strategy_id"],
    )
    res = DataRetrievalEngine.execute(populated_db, plan)

    assert isinstance(res["total_metric"], Decimal)
    assert res["total_metric"] == Decimal("180.5000")
    assert res["record_count"] == 1

    citations = CitationBuilder.build_citations("recommendations", res["sample_records"])
    assert len(citations) == 1
    assert "Rightsize" in citations[0].description


def test_retrieve_resources_data(populated_db):
    """Verify safe inventory counts and breakdowns."""
    plan = QueryPlan(
        intent=CopilotIntent.RESOURCE_UTILIZATION,
        target_dataset="cloud_resources",
        filters={},
        aggregations=["COUNT:*"],
        group_by=["resource_type"],
    )
    res = DataRetrievalEngine.execute(populated_db, plan)

    assert res["record_count"] == 2
    assert len(res["breakdown"]) == 2

    citations = CitationBuilder.build_citations("cloud_resources", res["sample_records"])
    assert len(citations) == 2
