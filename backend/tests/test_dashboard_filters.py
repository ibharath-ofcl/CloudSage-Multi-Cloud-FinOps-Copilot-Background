"""
Test Suite: Dashboard Multi-Dimensional Filtering.
Validates that all analytical queries correctly respect filters for:
- Provider (AWS, AZURE, GCP, ALL)
- Date range (start_date, end_date)
- Service name
- Account / Project ID
- Region
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from backend.app.schemas.dashboard import DashboardFilterParams
from backend.app.services.dashboard import DashboardAnalyticsService
from backend.tests.test_dashboard_analytics import populated_dashboard_db


def test_filter_by_provider_aws(populated_dashboard_db: Session):
    """Test filtering metrics strictly by AWS."""
    params = DashboardFilterParams(provider="AWS")
    kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, params)
    assert kpis.total_spend == Decimal("150.0000")

    trends = DashboardAnalyticsService.get_cost_trends(populated_dashboard_db, params)
    total_from_points = sum(p.total_cost for p in trends.points)
    assert total_from_points == Decimal("150.0000")


def test_filter_by_provider_azure(populated_dashboard_db: Session):
    """Test filtering metrics strictly by Azure."""
    params = DashboardFilterParams(provider="AZURE")
    kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, params)
    assert kpis.total_spend == Decimal("100.0000")


def test_filter_by_provider_gcp(populated_dashboard_db: Session):
    """Test filtering metrics strictly by GCP."""
    params = DashboardFilterParams(provider="GCP")
    kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, params)
    assert kpis.total_spend == Decimal("50.0000")


def test_filter_by_service_name(populated_dashboard_db: Session):
    """Test filtering by specific service name."""
    ec2_params = DashboardFilterParams(service="Elastic Compute")
    ec2_kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, ec2_params)
    assert ec2_kpis.total_spend == Decimal("150.0000")

    # Non-existent service should return 0 spend
    none_params = DashboardFilterParams(service="NonExistentService")
    none_kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, none_params)
    assert none_kpis.total_spend == Decimal("0.0000")


def test_filter_by_account_id(populated_dashboard_db: Session):
    """Test filtering by account / subscription / project ID."""
    acct_params = DashboardFilterParams(account_id="sub-azure-001")
    acct_kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, acct_params)
    assert acct_kpis.total_spend == Decimal("100.0000")


def test_filter_by_region(populated_dashboard_db: Session):
    """Test filtering by cloud region."""
    region_params = DashboardFilterParams(region="us-east-1")
    region_kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, region_params)
    assert region_kpis.total_spend == Decimal("150.0000")


def test_filter_by_date_range(populated_dashboard_db: Session):
    """Test filtering by charge period date range."""
    now = datetime.now(timezone.utc).date()

    # Yesterday to today
    recent_params = DashboardFilterParams(
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=1),
    )
    kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, recent_params)
    # captures Azure (100.00) + GCP (50.00) = 150.00
    assert kpis.total_spend == Decimal("150.0000")


def test_filter_combination_provider_and_region(populated_dashboard_db: Session):
    """Test composite multi-criteria filtering."""
    # AWS in us-east-1 -> 150.00
    params = DashboardFilterParams(provider="AWS", region="us-east-1")
    kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, params)
    assert kpis.total_spend == Decimal("150.0000")

    # AWS in us-west-2 -> 0.00
    mismatch_params = DashboardFilterParams(provider="AWS", region="us-west-2")
    mismatch_kpis = DashboardAnalyticsService.get_executive_kpis(populated_dashboard_db, mismatch_params)
    assert mismatch_kpis.total_spend == Decimal("0.0000")
