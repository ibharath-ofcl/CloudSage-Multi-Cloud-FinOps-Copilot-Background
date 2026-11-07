"""
Test Suite: Dashboard Analytics Service.
Validates aggregations, Zero Float Rule, anti-double-counting, multi-period trend calculations,
and CSV/JSON export functionality.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy.orm import Session

from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection
from backend.app.schemas.dashboard import DashboardFilterParams
from backend.app.services.dashboard import DashboardAnalyticsService


@pytest.fixture
def populated_dashboard_db(db_session: Session) -> Session:
    """Populate test database with a known, controlled multi-cloud dataset."""
    now = datetime.now(timezone.utc)
    today = now.date()

    # 1. Discovered Cloud Resources
    res1 = CloudResource(
        resource_id="arn:aws:ec2:us-east-1:123456789012:instance/i-001",
        provider="AWS",
        account_id="123456789012",
        service_name="Amazon Elastic Compute Cloud",
        service_category="COMPUTE",
        resource_type="ec2:instance",
        region="us-east-1",
        status="active",
        owner="DevOps",
        environment="production",
        tags={"environment": "production", "owner": "DevOps", "cost_center": "CC-101"},
    )
    res2 = CloudResource(
        resource_id="/subscriptions/sub-azure-001/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm-002",
        provider="AZURE",
        account_id="sub-azure-001",
        service_name="Virtual Machines",
        service_category="COMPUTE",
        resource_type="compute:vm",
        region="eastus",
        status="stopped",
        owner=None,
        environment="unknown",
        tags={},  # Untagged
    )
    db_session.add_all([res1, res2])
    db_session.flush()

    # 2. Billing Records across AWS, Azure, GCP
    b1 = BillingRecord(
        record_id=uuid.uuid4(),
        provider="AWS",
        billing_account_id="123456789012",
        subscription_id="sub-aws-1",
        resource_id=res1.resource_id,
        service_category="COMPUTE",
        service_name="Amazon Elastic Compute Cloud",
        region="us-east-1",
        usage_start_time=now - timedelta(days=2),
        usage_end_time=now - timedelta(days=1),
        usage_quantity=Decimal("24.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("150.0000"),
        currency="USD",
        tags={"environment": "production", "owner": "DevOps", "cost_center": "CC-101"},
    )
    b2 = BillingRecord(
        record_id=uuid.uuid4(),
        provider="AZURE",
        billing_account_id="sub-azure-001",
        subscription_id="sub-azure-001",
        resource_id=res2.resource_id,
        service_category="COMPUTE",
        service_name="Virtual Machines",
        region="eastus",
        usage_start_time=now - timedelta(days=1),
        usage_end_time=now,
        usage_quantity=Decimal("24.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("100.0000"),
        currency="USD",
        tags={"environment": "production", "owner": "Finance", "cost_center": "CC-102"},
    )
    b3 = BillingRecord(
        record_id=uuid.uuid4(),
        provider="GCP",
        billing_account_id="proj-gcp-001",
        subscription_id="proj-gcp-001",
        resource_id="//compute.googleapis.com/projects/proj-gcp-001/zones/us-central1-a/instances/gcp-003",
        service_category="COMPUTE",
        service_name="Compute Engine",
        region="us-central1",
        usage_start_time=now,
        usage_end_time=now,
        usage_quantity=Decimal("12.0"),
        usage_unit="HOURS",
        unblended_cost=Decimal("50.0000"),
        currency="USD",
        tags={"environment": "development", "owner": "DataTeam", "cost_center": "CC-103"},
    )
    db_session.add_all([b1, b2, b3])

    # 3. Waste Findings
    w1 = WasteDetection(
        resource_id=res1.resource_id,
        provider="AWS",
        account_id="123456789012",
        waste_type="IDLE_VM",
        finding_title="Idle Compute Instance",
        explanation="Average CPU utilization under 1.5% for 14 consecutive days",
        severity="HIGH",
        status="ACTIVE",
        estimated_monthly_waste=Decimal("45.0000"),
    )
    w2 = WasteDetection(
        resource_id=res2.resource_id,
        provider="AZURE",
        account_id="sub-azure-001",
        waste_type="UNATTACHED_DISK",
        finding_title="Unattached Managed Disk",
        explanation="Managed disk unattached from any VM",
        severity="MEDIUM",
        status="RESOLVED",
        estimated_monthly_waste=Decimal("30.0000"),
    )
    db_session.add_all([w1, w2])

    # 4. Anomaly Records
    a1 = CostAnomaly(
        provider="AWS",
        account_id="123456789012",
        service_category="STORAGE",
        service_name="Amazon S3",
        region="us-east-1",
        anomaly_category="SERVICE_SPIKE",
        title="Unusual S3 Storage Spike",
        explanation="Massive unexpected API call spike in S3 standard storage",
        anomaly_date=today,
        actual_cost=Decimal("80.0000"),
        expected_cost=Decimal("20.0000"),
        estimated_excess_cost=Decimal("60.0000"),
        severity="CRITICAL",
        status="OPEN",
        z_score=Decimal("4.0000"),
    )
    a2 = CostAnomaly(
        provider="GCP",
        account_id="proj-gcp-001",
        service_category="STORAGE",
        service_name="Cloud Storage",
        region="us-central1",
        anomaly_category="SERVICE_SPIKE",
        title="Cloud Storage Egress Surge",
        explanation="Egress network spike during database export",
        anomaly_date=today - timedelta(days=8),
        actual_cost=Decimal("35.0000"),
        expected_cost=Decimal("15.0000"),
        estimated_excess_cost=Decimal("20.0000"),
        severity="MEDIUM",
        status="RESOLVED",
        z_score=Decimal("2.3300"),
    )
    db_session.add_all([a1, a2])

    # 5. Recommendation Records
    r1 = Recommendation(
        resource_id=res1.resource_id,
        provider="AWS",
        account_id="123456789012",
        region="us-east-1",
        service_name="Amazon Elastic Compute Cloud",
        title="Rightsize over-provisioned instance",
        description="Downsize instance from m5.2xlarge to m5.large",
        remediation_guide="aws ec2 modify-instance-attribute --instance-id i-001",
        action_type="RIGHTSIZE",
        priority="P1",
        status="PROPOSED",
        estimated_monthly_savings=Decimal("70.0000"),
        estimated_annual_savings=Decimal("840.0000"),
        implementation_effort="LOW",
    )
    r2 = Recommendation(
        resource_id=res2.resource_id,
        provider="AZURE",
        account_id="sub-azure-001",
        region="eastus",
        service_name="Virtual Machines",
        title="Terminate unattached disk",
        description="Remove unattached managed disk",
        remediation_guide="az disk delete --name disk1",
        action_type="TERMINATE",
        priority="P2",
        status="IMPLEMENTED",
        estimated_monthly_savings=Decimal("25.0000"),
        estimated_annual_savings=Decimal("300.0000"),
        verified_savings=Decimal("25.0000"),
        implementation_effort="LOW",
    )
    db_session.add_all([r1, r2])

    db_session.commit()
    return db_session


def test_dashboard_executive_kpis_zero_float_rule(populated_dashboard_db: Session):
    """Test that executive KPIs strictly obey the Zero Float Rule (Decimal arithmetic)."""
    kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, DashboardFilterParams())

    # Total spend must match sum of Decimal("150") + Decimal("100") + Decimal("50") = Decimal("300.0000")
    assert kpis.total_spend == Decimal("300.0000")
    assert kpis.identified_monthly_waste == Decimal("45.0000")
    assert kpis.anomalous_excess_cost == Decimal("60.0000")
    assert kpis.potential_monthly_savings == Decimal("95.0000")
    assert kpis.verified_realized_savings == Decimal("25.0000")


def test_dashboard_anti_double_counting(populated_dashboard_db: Session):
    """
    Ensure anti-double-counting principle:
    Waste ($45.00), Anomaly impact ($60.00), and Potential Savings ($95.00)
    remain completely distinct and are never summed into total expenditure ($300.00).
    """
    kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, DashboardFilterParams())

    assert kpis.total_spend == Decimal("300.0000")
    assert kpis.identified_monthly_waste != kpis.total_spend
    assert kpis.potential_monthly_savings != kpis.identified_monthly_waste
    assert (kpis.identified_monthly_waste + kpis.potential_monthly_savings) != kpis.total_spend


def test_dashboard_spend_trends_daily_and_monthly(populated_dashboard_db: Session):
    """Test daily and monthly spend trend aggregations."""
    # Daily trends
    daily_res = DashboardAnalyticsService.get_cost_trends(
        populated_dashboard_db, DashboardFilterParams(), granularity="DAILY"
    )
    assert daily_res.granularity == "DAILY"
    assert len(daily_res.points) >= 1
    total_from_points = sum(p.total_cost for p in daily_res.points)
    assert total_from_points == Decimal("300.0000")

    # Monthly trends
    monthly_res = DashboardAnalyticsService.get_cost_trends(
        populated_dashboard_db, DashboardFilterParams(), granularity="MONTHLY"
    )
    assert monthly_res.granularity == "MONTHLY"
    assert len(monthly_res.points) >= 1


def test_dashboard_provider_comparison(populated_dashboard_db: Session):
    """Test multi-cloud cross-provider comparison breakdown."""
    comp = DashboardAnalyticsService.get_provider_comparison(populated_dashboard_db, DashboardFilterParams())

    assert len(comp.providers) == 3
    provider_map = {p.provider: p for p in comp.providers}

    assert "AWS" in provider_map
    assert "AZURE" in provider_map
    assert "GCP" in provider_map

    assert provider_map["AWS"].cost == Decimal("150.0000")
    assert provider_map["AWS"].percentage == Decimal("50.00")

    assert provider_map["AZURE"].cost == Decimal("100.0000")
    assert provider_map["AZURE"].percentage == Decimal("33.33")

    assert provider_map["GCP"].cost == Decimal("50.0000")
    assert provider_map["GCP"].percentage == Decimal("16.67")


def test_dashboard_service_breakdown(populated_dashboard_db: Session):
    """Test top service spending breakdown."""
    res = DashboardAnalyticsService.get_service_breakdown(populated_dashboard_db, DashboardFilterParams())

    assert len(res.services) == 3
    top_svc = res.services[0]
    assert top_svc.service_name == "Amazon Elastic Compute Cloud"
    assert top_svc.cost == Decimal("150.0000")
    assert top_svc.percentage == Decimal("50.00")


def test_dashboard_anomaly_summary(populated_dashboard_db: Session):
    """Test anomaly summary filtering and aggregation."""
    summary = DashboardAnalyticsService.get_anomaly_summary(populated_dashboard_db, DashboardFilterParams())

    assert summary.total_active_anomalies == 1
    assert summary.critical_count == 1
    assert summary.total_excess_cost == Decimal("60.0000")
    assert summary.open_vs_resolved.get("OPEN") == 1


def test_dashboard_waste_summary(populated_dashboard_db: Session):
    """Test waste detection summary calculations."""
    summary = DashboardAnalyticsService.get_waste_summary(populated_dashboard_db, DashboardFilterParams())

    assert summary.total_active_waste_items == 1  # 1 ACTIVE finding
    assert summary.total_monthly_waste == Decimal("45.0000")
    assert summary.waste_by_type.get("IDLE_VM") == Decimal("45.0000")
    assert summary.severity_distribution.get("HIGH") == 1


def test_dashboard_recommendation_summary(populated_dashboard_db: Session):
    """Test recommendation summary calculations."""
    summary = DashboardAnalyticsService.get_recommendations_summary(populated_dashboard_db, DashboardFilterParams())

    assert summary.total_open_recommendations == 1  # 1 PROPOSED/OPEN
    assert summary.potential_monthly_savings == Decimal("70.0000")
    assert summary.priority_distribution.get("P1") == 1


def test_dashboard_savings_summary(populated_dashboard_db: Session):
    """Test potential vs realized savings calculations."""
    savings = DashboardAnalyticsService.get_savings_summary(populated_dashboard_db, DashboardFilterParams())

    assert savings.potential_monthly_savings == Decimal("95.0000")
    assert savings.potential_annual_savings == Decimal("1140.0000")
    assert savings.verified_realized_savings == Decimal("25.0000")


def test_dashboard_inventory_summary(populated_dashboard_db: Session):
    """Test inventory summary metrics."""
    inv = DashboardAnalyticsService.get_inventory_summary(populated_dashboard_db, DashboardFilterParams())

    assert inv.total_resources == 2
    assert inv.resources_by_provider.get("AWS") == 1
    assert inv.resources_by_provider.get("AZURE") == 1
    assert inv.untagged_resources_count == 1
    assert inv.tag_coverage_percentage == Decimal("50.00")


def test_dashboard_data_quality_summary(populated_dashboard_db: Session):
    """Test data quality and FOCUS compliance scoring."""
    dq = DashboardAnalyticsService.get_data_quality_summary(populated_dashboard_db, DashboardFilterParams())

    assert dq.focus_compliance_percentage == Decimal("100.00")
    assert dq.currency_uniformity_score == Decimal("100.00")


def test_dashboard_overview_aggregation(populated_dashboard_db: Session):
    """Test unified overview payload generation."""
    overview = DashboardAnalyticsService.get_overview(populated_dashboard_db, DashboardFilterParams())

    assert overview.kpi.total_spend == Decimal("300.0000")
    assert len(overview.provider_comparison.providers) == 3
    assert len(overview.top_services.services) == 3
    assert len(overview.copilot_suggested_questions) >= 5


def test_dashboard_export_csv_and_json(populated_dashboard_db: Session):
    """Test export functionality for both CSV and JSON formats."""
    # Export CSV
    csv_text, media_csv = DashboardAnalyticsService.export_dashboard_data(
        populated_dashboard_db, filters=DashboardFilterParams(), export_format="csv", section="overview"
    )
    assert media_csv == "text/csv"
    assert "KPI Metric,Value,Currency" in csv_text
    assert "Total Cloud Spend,300.0000,USD" in csv_text

    # Export JSON
    json_text, media_json = DashboardAnalyticsService.export_dashboard_data(
        populated_dashboard_db, filters=DashboardFilterParams(), export_format="json", section="overview"
    )
    assert media_json == "application/json"
    assert '"total_spend": "300.0000"' in json_text
