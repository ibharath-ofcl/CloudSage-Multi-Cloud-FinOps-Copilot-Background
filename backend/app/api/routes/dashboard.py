"""
CloudSage Multi-Cloud FinOps Dashboard REST API Endpoints.
Provides 13 analytical aggregation endpoints, filter-aware CSV/JSON exports,
and mounts the interactive enterprise FinOps Command Center single-page web dashboard.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.app.core.database import get_sync_db
from backend.app.schemas.dashboard import (
    AnomalySummaryResponse,
    CostTrendResponse,
    DashboardFilterParams,
    DashboardOverviewResponse,
    DataQualitySummaryResponse,
    ExecutiveKpiSummary,
    IngestionSummaryResponse,
    InventorySummaryResponse,
    ProviderComparisonResponse,
    RecommendationSummaryResponse,
    ResourceCostsResponse,
    SavingsSummaryResponse,
    ServiceBreakdownResponse,
    WasteSummaryResponse,
)
from backend.app.services.dashboard import DashboardAnalyticsService

router = APIRouter(prefix="/dashboard", tags=["FinOps Dashboards & Visualizations"])


def _extract_filter_params(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    provider: Optional[str] = Query(None, description="AWS, AZURE, GCP, or ALL"),
    service: Optional[str] = Query(None, description="Service name filter"),
    account_id: Optional[str] = Query(None, description="Account / Subscription / Project ID"),
    region: Optional[str] = Query(None, description="Cloud region"),
    environment: Optional[str] = Query(None, description="Environment tag (prod, dev, staging)"),
    owner: Optional[str] = Query(None, description="Owner tag"),
    cost_center: Optional[str] = Query(None, description="Cost center tag"),
) -> DashboardFilterParams:
    return DashboardFilterParams(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        service=service,
        account_id=account_id,
        region=region,
        environment=environment,
        owner=owner,
        cost_center=cost_center,
    )


@router.get("/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves consolidated executive command center metrics."""
    return DashboardAnalyticsService.get_overview(db, filters)


@router.get("/kpis", response_model=ExecutiveKpiSummary)
def get_executive_kpis(
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves executive KPI cards summary."""
    return DashboardAnalyticsService.get_executive_kpis(db, filters)


@router.get("/cost-trends", response_model=CostTrendResponse)
@router.get("/trends", response_model=CostTrendResponse, include_in_schema=False)
def get_cost_trends(
    granularity: str = Query("DAILY", description="DAILY, WEEKLY, or MONTHLY"),
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves multi-cloud historical spending trends."""
    return DashboardAnalyticsService.get_cost_trends(db, filters, granularity=granularity)


@router.get("/provider-comparison", response_model=ProviderComparisonResponse)
def get_provider_comparison(
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves AWS, Azure, and GCP spending distribution and percentage shares."""
    return DashboardAnalyticsService.get_provider_comparison(db, filters)


@router.get("/service-breakdown", response_model=ServiceBreakdownResponse)
def get_service_breakdown(
    limit: int = Query(10, ge=1, le=50),
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves top-N cloud services and category distribution."""
    return DashboardAnalyticsService.get_service_breakdown(db, filters, limit=limit)


@router.get("/resource-costs", response_model=ResourceCostsResponse)
def get_resource_costs(
    limit: int = Query(20, ge=1, le=100),
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves top cost-driving cloud resources ranking and operational metadata."""
    return DashboardAnalyticsService.get_resource_costs(db, filters, limit=limit)


@router.get("/savings-summary", response_model=SavingsSummaryResponse)
@router.get("/savings", response_model=SavingsSummaryResponse, include_in_schema=False)
def get_savings_summary(
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves potential and verified savings with anti-double-counting guarantees."""
    return DashboardAnalyticsService.get_savings_summary(db, filters)


@router.get("/anomaly-summary", response_model=AnomalySummaryResponse)
@router.get("/anomalies", response_model=AnomalySummaryResponse, include_in_schema=False)
def get_anomaly_summary(
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves cost anomaly distribution and excess expenditure summary."""
    return DashboardAnalyticsService.get_anomaly_summary(db, filters)


@router.get("/waste-summary", response_model=WasteSummaryResponse)
@router.get("/waste", response_model=WasteSummaryResponse, include_in_schema=False)
def get_waste_summary(
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves infrastructure waste detection and monthly savings summary."""
    return DashboardAnalyticsService.get_waste_summary(db, filters)


@router.get("/recommendation-summary", response_model=RecommendationSummaryResponse)
@router.get("/recommendations", response_model=RecommendationSummaryResponse, include_in_schema=False)
def get_recommendation_summary(
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves advisory optimization recommendations priority distribution."""
    return DashboardAnalyticsService.get_recommendations_summary(db, filters)


@router.get("/inventory-summary", response_model=InventorySummaryResponse)
@router.get("/inventory", response_model=InventorySummaryResponse, include_in_schema=False)
def get_inventory_summary(
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves multi-cloud inventory counts and tag coverage metrics."""
    return DashboardAnalyticsService.get_inventory_summary(db, filters)


@router.get("/ingestion-summary", response_model=IngestionSummaryResponse)
def get_ingestion_summary(
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves billing ingestion pipeline runs and health summary."""
    return DashboardAnalyticsService.get_ingestion_summary(db, filters)


@router.get("/data-quality-summary", response_model=DataQualitySummaryResponse)
@router.get("/data-quality", response_model=DataQualitySummaryResponse, include_in_schema=False)
def get_data_quality_summary(
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Retrieves FOCUS 1.0 normalization and data quality compliance metrics."""
    return DashboardAnalyticsService.get_data_quality_summary(db, filters)


@router.get("/export")
def export_dashboard(
    format: str = Query("csv", description="csv or json"),
    section: str = Query("overview", description="overview, trends, services, providers"),
    filters: DashboardFilterParams = Depends(_extract_filter_params),
    db: Session = Depends(get_sync_db),
):
    """Exports filter-aware dashboard report in CSV or JSON format."""
    content, media_type = DashboardAnalyticsService.export_dashboard_data(
        db, filters=filters, export_format=format, section=section
    )
    ext = "csv" if format.lower() == "csv" else "json"
    filename = f"cloudsage_{section}_report_{date.today().isoformat()}.{ext}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/ui", response_class=HTMLResponse, tags=["Dashboard UI"])
def get_interactive_dashboard_ui():
    """Serves the interactive single-page CloudSage FinOps Command Center application."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CloudSage – Multi-Cloud FinOps Command Center</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; }
    .sidebar { background-color: #0f172a; }
    .card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 0.75rem; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05); }
    .active-nav { background-color: #1e293b; color: #38bdf8; border-left: 4px solid #38bdf8; }
    .kpi-title { font-size: 0.8125rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; }
    .kpi-value { font-size: 1.75rem; font-weight: 700; color: #0f172a; }
    .badge { font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.5rem; border-radius: 9999px; }
    .badge-aws { background: #ffedd5; color: #c2410c; }
    .badge-azure { background: #e0f2fe; color: #0369a1; }
    .badge-gcp { background: #fef08a; color: #854d0e; }
    .badge-critical { background: #fee2e2; color: #b91c1c; }
    .badge-high { background: #ffedd5; color: #c2410c; }
    .badge-medium { background: #fef9c3; color: #a16207; }
    .badge-low { background: #ecfdf5; color: #047857; }
    code.cli-snippet { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: #0f172a; color: #38bdf8; padding: 0.5rem 0.75rem; border-radius: 0.5rem; display: block; overflow-x: auto; font-size: 0.75rem; }
  </style>
</head>
<body class="flex h-screen overflow-hidden">
  <!-- Navigation Sidebar -->
  <aside class="sidebar w-64 flex flex-col z-20 transition-all duration-300">
    <div class="h-16 flex items-center px-6 border-b border-slate-800 gap-3">
      <i class="fa-solid fa-cloud-bolt text-sky-400 text-2xl"></i>
      <div>
        <h1 class="text-white font-bold text-lg tracking-tight">CloudSage</h1>
        <p class="text-xs text-slate-400 font-medium">FinOps Copilot v0.15.0</p>
      </div>
    </div>
    <nav class="flex-1 overflow-y-auto py-4 px-3 space-y-1">
      <a href="#overview" onclick="switchTab('overview')" id="nav-overview" class="active-nav flex items-center px-3 py-2.5 text-sm font-medium rounded-lg text-slate-300 hover:bg-slate-800 transition">
        <i class="fa-solid fa-gauge w-5 text-slate-400"></i><span class="ml-3">Overview</span>
      </a>
      <a href="#costs" onclick="switchTab('costs')" id="nav-costs" class="flex items-center px-3 py-2.5 text-sm font-medium rounded-lg text-slate-300 hover:bg-slate-800 transition">
        <i class="fa-solid fa-chart-pie w-5 text-slate-400"></i><span class="ml-3">Cloud Costs</span>
      </a>
      <a href="#anomalies" onclick="switchTab('anomalies')" id="nav-anomalies" class="flex items-center px-3 py-2.5 text-sm font-medium rounded-lg text-slate-300 hover:bg-slate-800 transition">
        <i class="fa-solid fa-triangle-exclamation w-5 text-slate-400"></i><span class="ml-3">Cost Anomalies</span>
      </a>
      <a href="#waste" onclick="switchTab('waste')" id="nav-waste" class="flex items-center px-3 py-2.5 text-sm font-medium rounded-lg text-slate-300 hover:bg-slate-800 transition">
        <i class="fa-solid fa-trash-can w-5 text-slate-400"></i><span class="ml-3">Waste Detection</span>
      </a>
      <a href="#recommendations" onclick="switchTab('recommendations')" id="nav-recommendations" class="flex items-center px-3 py-2.5 text-sm font-medium rounded-lg text-slate-300 hover:bg-slate-800 transition">
        <i class="fa-solid fa-lightbulb w-5 text-slate-400"></i><span class="ml-3">Recommendations</span>
      </a>
      <a href="#savings" onclick="switchTab('savings')" id="nav-savings" class="flex items-center px-3 py-2.5 text-sm font-medium rounded-lg text-slate-300 hover:bg-slate-800 transition">
        <i class="fa-solid fa-piggy-bank w-5 text-slate-400"></i><span class="ml-3">Savings & ROI</span>
      </a>
      <a href="#inventory" onclick="switchTab('inventory')" id="nav-inventory" class="flex items-center px-3 py-2.5 text-sm font-medium rounded-lg text-slate-300 hover:bg-slate-800 transition">
        <i class="fa-solid fa-server w-5 text-slate-400"></i><span class="ml-3">Resource Inventory</span>
      </a>
      <a href="#quality" onclick="switchTab('quality')" id="nav-quality" class="flex items-center px-3 py-2.5 text-sm font-medium rounded-lg text-slate-300 hover:bg-slate-800 transition">
        <i class="fa-solid fa-check-double w-5 text-slate-400"></i><span class="ml-3">FOCUS Quality</span>
      </a>
      <a href="#copilot" onclick="toggleCopilot()" class="flex items-center px-3 py-2.5 text-sm font-medium rounded-lg text-purple-300 hover:bg-slate-800 transition mt-4 bg-purple-950/40 border border-purple-800/40">
        <i class="fa-solid fa-wand-magic-sparkles w-5 text-purple-400"></i><span class="ml-3 font-semibold">AI Copilot</span>
      </a>
    </nav>
    <div class="p-4 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
      <span>FOCUS 1.0 Verified</span>
      <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
    </div>
  </aside>

  <!-- Main Content Wrapper -->
  <div class="flex-1 flex flex-col overflow-hidden">
    <!-- Header -->
    <header class="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shadow-sm z-10">
      <div class="flex items-center gap-4">
        <h2 id="page-title" class="text-xl font-bold text-slate-800">Executive Overview</h2>
        <span class="bg-slate-100 text-slate-600 text-xs px-2.5 py-1 rounded-full font-medium" id="freshness-badge">Fresh</span>
      </div>
      <div class="flex items-center gap-3">
        <!-- Global Provider Filter -->
        <select id="filter-provider" onchange="refreshDashboard()" class="text-sm bg-slate-50 border border-slate-300 rounded-lg px-3 py-1.5 font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-500">
          <option value="ALL">All Cloud Providers</option>
          <option value="AWS">Amazon Web Services</option>
          <option value="AZURE">Microsoft Azure</option>
          <option value="GCP">Google Cloud Platform</option>
        </select>

        <!-- Refresh Action -->
        <button onclick="refreshDashboard()" class="p-2 text-slate-600 hover:text-slate-900 bg-slate-50 border border-slate-300 rounded-lg hover:bg-slate-100 transition" title="Refresh Dashboard">
          <i class="fa-solid fa-arrows-rotate"></i>
        </button>

        <!-- Export Dropdown -->
        <button onclick="exportData('csv')" class="px-3 py-1.5 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition flex items-center gap-1.5">
          <i class="fa-solid fa-file-arrow-down text-slate-500"></i> Export CSV
        </button>

        <!-- Copilot Toggle -->
        <button onclick="toggleCopilot()" class="px-3.5 py-1.5 text-sm font-semibold text-white bg-purple-600 rounded-lg hover:bg-purple-700 shadow-sm transition flex items-center gap-2">
          <i class="fa-solid fa-sparkles"></i> Copilot
        </button>
      </div>
    </header>

    <!-- Scrollable Workspace -->
    <main class="flex-1 overflow-y-auto p-6 space-y-6">

      <!-- =================================================================== -->
      <!-- TAB 1: OVERVIEW -->
      <!-- =================================================================== -->
      <div id="tab-overview" class="tab-content space-y-6">
        <!-- KPI Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5" id="kpi-grid">
          <div class="card p-5 border-l-4 border-l-sky-500">
            <div class="flex justify-between items-start">
              <span class="kpi-title">Total Cloud Spend</span>
              <i class="fa-solid fa-wallet text-sky-500 text-lg"></i>
            </div>
            <div class="kpi-value mt-2" id="kpi-total-spend">$0.00</div>
            <p class="text-xs text-slate-500 mt-1 font-medium" id="kpi-total-sub">FOCUS normalized</p>
          </div>

          <div class="card p-5 border-l-4 border-l-indigo-500">
            <div class="flex justify-between items-start">
              <span class="kpi-title">Month-To-Date Spend</span>
              <i class="fa-solid fa-calendar-day text-indigo-500 text-lg"></i>
            </div>
            <div class="kpi-value mt-2" id="kpi-mtd-spend">$0.00</div>
            <p class="text-xs mt-1 font-semibold" id="kpi-mom-change"><span class="text-slate-500">0.0% MoM</span></p>
          </div>

          <div class="card p-5 border-l-4 border-l-amber-500">
            <div class="flex justify-between items-start">
              <span class="kpi-title">Identified Waste</span>
              <i class="fa-solid fa-trash-arrow-up text-amber-500 text-lg"></i>
            </div>
            <div class="kpi-value mt-2 text-amber-600" id="kpi-waste-sum">$0.00</div>
            <p class="text-xs text-slate-500 mt-1" id="kpi-waste-cnt">0 active waste items</p>
          </div>

          <div class="card p-5 border-l-4 border-l-emerald-500">
            <div class="flex justify-between items-start">
              <span class="kpi-title">Potential Monthly Savings</span>
              <i class="fa-solid fa-piggy-bank text-emerald-500 text-lg"></i>
            </div>
            <div class="kpi-value mt-2 text-emerald-600" id="kpi-savings-sum">$0.00</div>
            <p class="text-xs text-slate-500 mt-1" id="kpi-savings-ann">$0.00/yr opportunity</p>
          </div>
        </div>

        <!-- Charts Section: Trends & Provider Comparison -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div class="card p-6 lg:col-span-2">
            <div class="flex justify-between items-center mb-4">
              <div>
                <h3 class="font-bold text-slate-800">Multi-Cloud Daily Spending Trend</h3>
                <p class="text-xs text-slate-500 font-medium">Daily expenditure trajectory across active providers</p>
              </div>
              <div class="flex items-center gap-2">
                <span class="inline-flex items-center text-xs font-semibold text-slate-600"><span class="w-2.5 h-2.5 rounded-full bg-amber-500 mr-1.5"></span>Anomaly Spike</span>
              </div>
            </div>
            <div class="h-72">
              <canvas id="trendChart"></canvas>
            </div>
          </div>

          <div class="card p-6">
            <h3 class="font-bold text-slate-800 mb-1">Provider Distribution</h3>
            <p class="text-xs text-slate-500 font-medium mb-4">Percentage share of total spend</p>
            <div class="h-56 relative flex items-center justify-center">
              <canvas id="providerChart"></canvas>
            </div>
            <div class="mt-4 space-y-2" id="provider-breakdown-list"></div>
          </div>
        </div>

        <!-- Top Services & Advisory Action Center -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div class="card p-6">
            <h3 class="font-bold text-slate-800 mb-1">Top Cloud Service Cost Drivers</h3>
            <p class="text-xs text-slate-500 font-medium mb-4">Highest expenditure cloud services</p>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-sm">
                <thead class="text-xs uppercase bg-slate-50 text-slate-500 border-b">
                  <tr>
                    <th class="py-2.5 px-3">Service</th>
                    <th class="py-2.5 px-3">Provider</th>
                    <th class="py-2.5 px-3 text-right">Cost (USD)</th>
                    <th class="py-2.5 px-3 text-right">Share</th>
                  </tr>
                </thead>
                <tbody id="services-table-body" class="divide-y divide-slate-100 text-slate-700">
                  <tr><td colspan="4" class="text-center py-4 text-slate-400">Loading services...</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="card p-6 flex flex-col justify-between">
            <div>
              <div class="flex justify-between items-center mb-1">
                <h3 class="font-bold text-slate-800">Active FinOps Recommendations</h3>
                <span class="badge bg-emerald-100 text-emerald-800" id="rec-count-badge">0 Open</span>
              </div>
              <p class="text-xs text-slate-500 font-medium mb-4">Prioritized advisory savings proposals (Strictly non-destructive)</p>
              <div class="space-y-3" id="recommendation-list">
                <div class="text-center py-6 text-slate-400">No open recommendations.</div>
              </div>
            </div>
            <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Advisory Only Policy Enforced</span>
              <a href="#recommendations" onclick="switchTab('recommendations')" class="text-sky-600 font-semibold hover:underline">View All &rarr;</a>
            </div>
          </div>
        </div>
      </div>

      <!-- =================================================================== -->
      <!-- TAB 2: CLOUD COSTS -->
      <!-- =================================================================== -->
      <div id="tab-costs" class="tab-content space-y-6 hidden">
        <!-- Costs KPI Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div class="card p-5 border-l-4 border-l-sky-500">
            <span class="kpi-title">Total Multi-Cloud Spend</span>
            <div class="kpi-value mt-2" id="costs-total-spend">$0.00</div>
            <p class="text-xs text-slate-500 mt-1">Aggregated across active clouds</p>
          </div>
          <div class="card p-5 border-l-4 border-l-orange-500">
            <span class="kpi-title">AWS Expenditure</span>
            <div class="kpi-value mt-2 text-orange-600" id="costs-aws-spend">$0.00</div>
            <p class="text-xs text-slate-500 mt-1" id="costs-aws-share">0.0% of total</p>
          </div>
          <div class="card p-5 border-l-4 border-l-sky-600">
            <span class="kpi-title">Azure Expenditure</span>
            <div class="kpi-value mt-2 text-sky-700" id="costs-azure-spend">$0.00</div>
            <p class="text-xs text-slate-500 mt-1" id="costs-azure-share">0.0% of total</p>
          </div>
          <div class="card p-5 border-l-4 border-l-yellow-500">
            <span class="kpi-title">GCP Expenditure</span>
            <div class="kpi-value mt-2 text-yellow-600" id="costs-gcp-spend">$0.00</div>
            <p class="text-xs text-slate-500 mt-1" id="costs-gcp-share">0.0% of total</p>
          </div>
        </div>

        <!-- Category Spend Progress Bars -->
        <div class="card p-6">
          <h3 class="font-bold text-slate-800 mb-1">Expenditure by Service Category</h3>
          <p class="text-xs text-slate-500 mb-4 font-medium">Categorized according to FOCUS 1.0 taxonomy</p>
          <div id="costs-categories-container" class="space-y-4">
            <div class="text-center py-4 text-slate-400 text-xs">Loading category distribution...</div>
          </div>
        </div>

        <!-- Full Services Cost Drivers Table -->
        <div class="card p-6">
          <div class="flex justify-between items-center mb-4">
            <div>
              <h3 class="font-bold text-slate-800">All Cloud Services Cost Breakdown</h3>
              <p class="text-xs text-slate-500 font-medium">Detailed billing distribution sorted by expenditure</p>
            </div>
            <button onclick="exportData('csv')" class="text-xs font-semibold text-sky-600 hover:underline">
              <i class="fa-solid fa-download mr-1"></i> Export Services
            </button>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="text-xs uppercase bg-slate-50 text-slate-500 border-b">
                <tr>
                  <th class="py-3 px-3">Service Name</th>
                  <th class="py-3 px-3">Provider</th>
                  <th class="py-3 px-3">Category</th>
                  <th class="py-3 px-3 text-right">30-Day Cost (USD)</th>
                  <th class="py-3 px-3 text-right">% Share</th>
                </tr>
              </thead>
              <tbody id="costs-services-table-body" class="divide-y divide-slate-100 text-slate-700">
                <tr><td colspan="5" class="text-center py-4 text-slate-400">Loading services...</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Top Cost-Driving Cloud Resources -->
        <div class="card p-6">
          <h3 class="font-bold text-slate-800 mb-1">Top Cost-Driving Cloud Resources</h3>
          <p class="text-xs text-slate-500 mb-4 font-medium">Specific infrastructure assets generating the largest monthly spend</p>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="text-xs uppercase bg-slate-50 text-slate-500 border-b">
                <tr>
                  <th class="py-3 px-3">Resource Identifier</th>
                  <th class="py-3 px-3">Provider</th>
                  <th class="py-3 px-3">Service</th>
                  <th class="py-3 px-3">Region</th>
                  <th class="py-3 px-3">Status</th>
                  <th class="py-3 px-3 text-right">Monthly Spend</th>
                </tr>
              </thead>
              <tbody id="costs-resources-table-body" class="divide-y divide-slate-100 text-slate-700">
                <tr><td colspan="6" class="text-center py-4 text-slate-400">Loading resources...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- =================================================================== -->
      <!-- TAB 3: COST ANOMALIES -->
      <!-- =================================================================== -->
      <div id="tab-anomalies" class="tab-content space-y-6 hidden">
        <!-- Anomalies KPIs -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div class="card p-5 border-l-4 border-l-rose-500">
            <span class="kpi-title">Active Cost Anomalies</span>
            <div class="kpi-value mt-2 text-rose-600" id="anom-total-count">0</div>
            <p class="text-xs text-slate-500 mt-1">Requiring FinOps review</p>
          </div>
          <div class="card p-5 border-l-4 border-l-red-600">
            <span class="kpi-title">Critical Severity</span>
            <div class="kpi-value mt-2 text-red-600" id="anom-critical-count">0</div>
            <p class="text-xs text-slate-500 mt-1">Z-Score &ge; 4.0 deviation</p>
          </div>
          <div class="card p-5 border-l-4 border-l-orange-500">
            <span class="kpi-title">High Severity</span>
            <div class="kpi-value mt-2 text-orange-600" id="anom-high-count">0</div>
            <p class="text-xs text-slate-500 mt-1">Z-Score &ge; 3.0 deviation</p>
          </div>
          <div class="card p-5 border-l-4 border-l-amber-500">
            <span class="kpi-title">Total Excess Cost</span>
            <div class="kpi-value mt-2 text-amber-700" id="anom-excess-cost">$0.00</div>
            <p class="text-xs text-slate-500 mt-1">Cumulative anomalous surge</p>
          </div>
        </div>

        <!-- Anomalies Detailed List -->
        <div class="card p-6">
          <div class="flex justify-between items-center mb-4">
            <div>
              <h3 class="font-bold text-slate-800">Detected Cost Anomalies</h3>
              <p class="text-xs text-slate-500 font-medium">Statistical and time-series spending surges across AWS, Azure, and GCP</p>
            </div>
            <span class="text-xs bg-slate-100 text-slate-700 px-3 py-1 rounded-full font-semibold" id="anom-badge-status">Active Monitoring</span>
          </div>
          <div id="anomalies-list-container" class="space-y-4">
            <div class="text-center py-8 text-slate-400 text-sm">Loading detected anomalies...</div>
          </div>
        </div>
      </div>

      <!-- =================================================================== -->
      <!-- TAB 4: WASTE DETECTION -->
      <!-- =================================================================== -->
      <div id="tab-waste" class="tab-content space-y-6 hidden">
        <!-- Waste KPIs -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div class="card p-5 border-l-4 border-l-amber-500">
            <span class="kpi-title">Active Waste Findings</span>
            <div class="kpi-value mt-2 text-amber-600" id="waste-total-count">0</div>
            <p class="text-xs text-slate-500 mt-1">Heuristically verified</p>
          </div>
          <div class="card p-5 border-l-4 border-l-orange-500">
            <span class="kpi-title">Monthly Avoidable Waste</span>
            <div class="kpi-value mt-2 text-orange-600" id="waste-monthly-cost">$0.00</div>
            <p class="text-xs text-slate-500 mt-1">Direct monthly financial leakage</p>
          </div>
          <div class="card p-5 border-l-4 border-l-rose-500">
            <span class="kpi-title">Annualized Waste</span>
            <div class="kpi-value mt-2 text-rose-600" id="waste-annual-cost">$0.00</div>
            <p class="text-xs text-slate-500 mt-1">Projected 12-month drain</p>
          </div>
          <div class="card p-5 border-l-4 border-l-indigo-500">
            <span class="kpi-title">High-Severity Findings</span>
            <div class="kpi-value mt-2 text-indigo-600" id="waste-high-count">0</div>
            <p class="text-xs text-slate-500 mt-1">Immediate priority for cleanup</p>
          </div>
        </div>

        <!-- Waste Findings Table -->
        <div class="card p-6">
          <div class="flex justify-between items-center mb-4">
            <div>
              <h3 class="font-bold text-slate-800">Infrastructure Waste Findings</h3>
              <p class="text-xs text-slate-500 font-medium">Idle compute, unattached storage, and oversized virtual machines</p>
            </div>
            <span class="text-xs bg-amber-50 text-amber-800 border border-amber-200 px-3 py-1 rounded-full font-semibold">Strictly Advisory</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="text-xs uppercase bg-slate-50 text-slate-500 border-b">
                <tr>
                  <th class="py-3 px-3">Finding Title</th>
                  <th class="py-3 px-3">Waste Type</th>
                  <th class="py-3 px-3">Provider</th>
                  <th class="py-3 px-3">Severity</th>
                  <th class="py-3 px-3 text-right">Monthly Waste</th>
                  <th class="py-3 px-3">Status</th>
                </tr>
              </thead>
              <tbody id="waste-findings-table-body" class="divide-y divide-slate-100 text-slate-700">
                <tr><td colspan="6" class="text-center py-4 text-slate-400">Loading waste findings...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- =================================================================== -->
      <!-- TAB 5: RECOMMENDATIONS -->
      <!-- =================================================================== -->
      <div id="tab-recommendations" class="tab-content space-y-6 hidden">
        <!-- Recommendations KPIs -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div class="card p-5 border-l-4 border-l-emerald-500">
            <span class="kpi-title">Open Proposals</span>
            <div class="kpi-value mt-2 text-emerald-600" id="rec-tab-count">0</div>
            <p class="text-xs text-slate-500 mt-1">Awaiting engineering approval</p>
          </div>
          <div class="card p-5 border-l-4 border-l-teal-500">
            <span class="kpi-title">Potential Monthly Savings</span>
            <div class="kpi-value mt-2 text-teal-600" id="rec-tab-monthly">$0.00</div>
            <p class="text-xs text-slate-500 mt-1">Net achievable monthly reduction</p>
          </div>
          <div class="card p-5 border-l-4 border-l-sky-500">
            <span class="kpi-title">Potential Annual Savings</span>
            <div class="kpi-value mt-2 text-sky-600" id="rec-tab-annual">$0.00</div>
            <p class="text-xs text-slate-500 mt-1">12-month run-rate opportunity</p>
          </div>
          <div class="card p-5 border-l-4 border-l-indigo-500">
            <span class="kpi-title">Priority P1 Actionable</span>
            <div class="kpi-value mt-2 text-indigo-600" id="rec-tab-p1">0</div>
            <p class="text-xs text-slate-500 mt-1">Highest ROI with low risk</p>
          </div>
        </div>

        <!-- Recommendations Detailed List with Playbook CLI Snippets -->
        <div class="card p-6">
          <div class="flex justify-between items-center mb-4">
            <div>
              <h3 class="font-bold text-slate-800">Prioritized FinOps Optimization Proposals</h3>
              <p class="text-xs text-slate-500 font-medium">Evidence-backed rightsizing, termination, and commitment optimization</p>
            </div>
            <span class="text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 px-3 py-1 rounded-full font-semibold">Advisory Only Policy Enforced</span>
          </div>
          <div id="recommendations-full-list" class="space-y-4">
            <div class="text-center py-8 text-slate-400 text-sm">Loading recommendations...</div>
          </div>
        </div>
      </div>

      <!-- =================================================================== -->
      <!-- TAB 6: SAVINGS & ROI -->
      <!-- =================================================================== -->
      <div id="tab-savings" class="tab-content space-y-6 hidden">
        <!-- Savings KPIs -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div class="card p-5 border-l-4 border-l-emerald-500">
            <span class="kpi-title">Potential Monthly Savings</span>
            <div class="kpi-value mt-2 text-emerald-600" id="sav-monthly-sum">$0.00</div>
            <p class="text-xs text-slate-500 mt-1">Anti-double-counted net total</p>
          </div>
          <div class="card p-5 border-l-4 border-l-teal-500">
            <span class="kpi-title">Potential Annual Savings</span>
            <div class="kpi-value mt-2 text-teal-600" id="sav-annual-sum">$0.00</div>
            <p class="text-xs text-slate-500 mt-1">Annualized FinOps opportunity</p>
          </div>
          <div class="card p-5 border-l-4 border-l-amber-500">
            <span class="kpi-title">Identified Monthly Waste</span>
            <div class="kpi-value mt-2 text-amber-600" id="sav-waste-sum">$0.00</div>
            <p class="text-xs text-slate-500 mt-1">Sub-optimal cloud utilization</p>
          </div>
          <div class="card p-5 border-l-4 border-l-sky-500">
            <span class="kpi-title">Anti-Double-Counting</span>
            <div class="kpi-value mt-2 text-sky-600"><i class="fa-solid fa-shield-check mr-1.5"></i>Verified</div>
            <p class="text-xs text-slate-500 mt-1">Taxonomy strictly partitioned</p>
          </div>
        </div>

        <!-- Savings Distribution Panels -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div class="card p-6">
            <h3 class="font-bold text-slate-800 mb-1">Savings by Cloud Provider</h3>
            <p class="text-xs text-slate-500 mb-4 font-medium">Financial recovery potential by cloud ecosystem</p>
            <div id="savings-provider-container" class="space-y-3">
              <div class="text-center py-4 text-slate-400 text-xs">Loading savings by provider...</div>
            </div>
          </div>

          <div class="card p-6">
            <h3 class="font-bold text-slate-800 mb-1">Savings by Priority Tier</h3>
            <p class="text-xs text-slate-500 mb-4 font-medium">Triage prioritization distribution ($P1$ highest velocity)</p>
            <div id="savings-priority-container" class="space-y-3">
              <div class="text-center py-4 text-slate-400 text-xs">Loading priority breakdown...</div>
            </div>
          </div>
        </div>

        <!-- Anti-Double-Counting Taxonomy Framework -->
        <div class="card p-6 bg-slate-50/50">
          <h3 class="font-bold text-slate-800 mb-1 flex items-center gap-2">
            <i class="fa-solid fa-scale-balanced text-indigo-600"></i> FinOps Anti-Double-Counting Governance Framework
          </h3>
          <p class="text-xs text-slate-500 mb-4">Ensures financial metrics never conflate baseline spend, avoidable waste, and potential savings</p>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div class="p-4 bg-white border border-slate-200 rounded-lg">
              <span class="font-bold text-slate-800 block text-sm mb-1">1. Baseline Spend</span>
              <p class="text-slate-600 leading-relaxed">Actual historical expenditure extracted from FOCUS-normalized billing records with penny-accurate Decimal precision.</p>
            </div>
            <div class="p-4 bg-white border border-amber-200 rounded-lg">
              <span class="font-bold text-amber-900 block text-sm mb-1">2. Avoidable Waste</span>
              <p class="text-slate-600 leading-relaxed">Expenditure delivering zero or marginal utility (e.g., idle VMs, unattached disks) measured using actual billed cost.</p>
            </div>
            <div class="p-4 bg-white border border-emerald-200 rounded-lg">
              <span class="font-bold text-emerald-900 block text-sm mb-1">3. Potential Savings</span>
              <p class="text-slate-600 leading-relaxed">Conservative delta between baseline spend and post-remediation run-rate. Non-additive across mutually exclusive actions.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- =================================================================== -->
      <!-- TAB 7: RESOURCE INVENTORY -->
      <!-- =================================================================== -->
      <div id="tab-inventory" class="tab-content space-y-6 hidden">
        <!-- Inventory KPIs -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div class="card p-5 border-l-4 border-l-sky-500">
            <span class="kpi-title">Discovered Resources</span>
            <div class="kpi-value mt-2 text-sky-600" id="inv-total-count">0</div>
            <p class="text-xs text-slate-500 mt-1">Multi-cloud inventory topology</p>
          </div>
          <div class="card p-5 border-l-4 border-l-emerald-500">
            <span class="kpi-title">Tag Coverage Score</span>
            <div class="kpi-value mt-2 text-emerald-600" id="inv-tag-coverage">100.0%</div>
            <p class="text-xs text-slate-500 mt-1">Cost-center tag compliance</p>
          </div>
          <div class="card p-5 border-l-4 border-l-indigo-500">
            <span class="kpi-title">Active / Running</span>
            <div class="kpi-value mt-2 text-indigo-600" id="inv-active-count">0</div>
            <p class="text-xs text-slate-500 mt-1">Operational cloud workloads</p>
          </div>
          <div class="card p-5 border-l-4 border-l-amber-500">
            <span class="kpi-title">Untagged Assets</span>
            <div class="kpi-value mt-2 text-slate-700" id="inv-untagged-count">0</div>
            <p class="text-xs text-slate-500 mt-1">Missing governance metadata</p>
          </div>
        </div>

        <!-- Discovered Resources Table -->
        <div class="card p-6">
          <div class="flex justify-between items-center mb-4">
            <div>
              <h3 class="font-bold text-slate-800">Multi-Cloud Discovered Infrastructure</h3>
              <p class="text-xs text-slate-500 font-medium">Reconciled inventory across AWS, Microsoft Azure, and Google Cloud Platform</p>
            </div>
            <span class="text-xs bg-slate-100 text-slate-700 px-3 py-1 rounded-full font-semibold">Continuous Discovery</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="text-xs uppercase bg-slate-50 text-slate-500 border-b">
                <tr>
                  <th class="py-3 px-3">Resource Identifier</th>
                  <th class="py-3 px-3">Provider</th>
                  <th class="py-3 px-3">Service</th>
                  <th class="py-3 px-3">Type</th>
                  <th class="py-3 px-3">Region</th>
                  <th class="py-3 px-3">Status</th>
                  <th class="py-3 px-3">Owner / Cost Center</th>
                </tr>
              </thead>
              <tbody id="inventory-table-body" class="divide-y divide-slate-100 text-slate-700">
                <tr><td colspan="7" class="text-center py-4 text-slate-400">Loading multi-cloud inventory...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- =================================================================== -->
      <!-- TAB 8: FOCUS QUALITY -->
      <!-- =================================================================== -->
      <div id="tab-quality" class="tab-content space-y-6 hidden">
        <!-- Quality KPIs -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div class="card p-5 border-l-4 border-l-emerald-500">
            <span class="kpi-title">Overall Quality Score</span>
            <div class="kpi-value mt-2 text-emerald-600" id="qual-overall-score">100.0%</div>
            <p class="text-xs text-slate-500 mt-1">Grade: A+ (Production Ready)</p>
          </div>
          <div class="card p-5 border-l-4 border-l-teal-500">
            <span class="kpi-title">FOCUS 1.0 Compliance</span>
            <div class="kpi-value mt-2 text-teal-600" id="qual-focus-pct">100.0%</div>
            <p class="text-xs text-slate-500 mt-1">Full specification conformance</p>
          </div>
          <div class="card p-5 border-l-4 border-l-sky-500">
            <span class="kpi-title">Tag Hygiene Score</span>
            <div class="kpi-value mt-2 text-sky-600" id="qual-tag-score">100.0%</div>
            <p class="text-xs text-slate-500 mt-1">Standardized key-value taxonomy</p>
          </div>
          <div class="card p-5 border-l-4 border-l-indigo-500">
            <span class="kpi-title">Currency Uniformity</span>
            <div class="kpi-value mt-2 text-indigo-600" id="qual-curr-score">100.0%</div>
            <p class="text-xs text-slate-500 mt-1">Strict USD Decimal normalization</p>
          </div>
        </div>

        <!-- FOCUS 1.0 Specification Conformance Pillars -->
        <div class="card p-6">
          <h3 class="font-bold text-slate-800 mb-1">FOCUS™ 1.0 Data Pipeline Conformance</h3>
          <p class="text-xs text-slate-500 mb-6 font-medium">Verification of FinOps Open Cost & Usage Specification compliance</p>
          
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 text-xs">
            <div class="p-4 border border-slate-200 rounded-lg space-y-2">
              <div class="flex items-center gap-2 font-bold text-slate-800 text-sm">
                <i class="fa-solid fa-circle-check text-emerald-500"></i> 1. Column Standardization
              </div>
              <p class="text-slate-600 leading-relaxed">Normalizes AWS CUR, Azure Cost Export, and GCP BigQuery fields into canonical FOCUS columns: <code class="bg-slate-100 px-1 py-0.5 rounded">ProviderName</code>, <code class="bg-slate-100 px-1 py-0.5 rounded">BilledCost</code>, <code class="bg-slate-100 px-1 py-0.5 rounded">EffectiveCost</code>, <code class="bg-slate-100 px-1 py-0.5 rounded">ChargePeriodStart</code>.</p>
            </div>

            <div class="p-4 border border-slate-200 rounded-lg space-y-2">
              <div class="flex items-center gap-2 font-bold text-slate-800 text-sm">
                <i class="fa-solid fa-circle-check text-emerald-500"></i> 2. Zero-Float Precision
              </div>
              <p class="text-slate-600 leading-relaxed">Enforces Python <code class="bg-slate-100 px-1 py-0.5 rounded">Decimal</code> and PostgreSQL <code class="bg-slate-100 px-1 py-0.5 rounded">Numeric(18, 4)</code> across all financial calculations to prevent floating-point rounding drift.</p>
            </div>

            <div class="p-4 border border-slate-200 rounded-lg space-y-2">
              <div class="flex items-center gap-2 font-bold text-slate-800 text-sm">
                <i class="fa-solid fa-circle-check text-emerald-500"></i> 3. Currency Normalization
              </div>
              <p class="text-slate-600 leading-relaxed">Converts multi-currency invoices into standard USD baseline using daily reference exchange rates with audit tracing.</p>
            </div>

            <div class="p-4 border border-slate-200 rounded-lg space-y-2">
              <div class="flex items-center gap-2 font-bold text-slate-800 text-sm">
                <i class="fa-solid fa-circle-check text-emerald-500"></i> 4. Taxonomy Classification
              </div>
              <p class="text-slate-600 leading-relaxed">Maps heterogeneous cloud native services into 6 canonical categories: COMPUTE, STORAGE, DATABASE, NETWORKING, MANAGEMENT, AI_ML.</p>
            </div>

            <div class="p-4 border border-slate-200 rounded-lg space-y-2">
              <div class="flex items-center gap-2 font-bold text-slate-800 text-sm">
                <i class="fa-solid fa-circle-check text-emerald-500"></i> 5. Idempotent Deduplication
              </div>
              <p class="text-slate-600 leading-relaxed">SHA-256 fingerprinting ensures repeat billing ingestions are deduplicated without double-counting line items.</p>
            </div>

            <div class="p-4 border border-slate-200 rounded-lg space-y-2">
              <div class="flex items-center gap-2 font-bold text-slate-800 text-sm">
                <i class="fa-solid fa-circle-check text-emerald-500"></i> 6. Non-Destructive Advisory
              </div>
              <p class="text-slate-600 leading-relaxed">Platform is strictly read-only regarding cloud resources. Autonomous mutations are prohibited by design.</p>
            </div>
          </div>
        </div>
      </div>

    </main>
  </div>

  <!-- Copilot Sliding Drawer -->
  <div id="copilot-drawer" class="fixed inset-y-0 right-0 w-96 bg-white shadow-2xl border-l border-slate-200 z-50 transform translate-x-full transition-transform duration-300 flex flex-col">
    <div class="h-16 px-6 border-b border-slate-200 flex items-center justify-between bg-purple-900 text-white">
      <div class="flex items-center gap-2.5">
        <i class="fa-solid fa-wand-magic-sparkles text-purple-300"></i>
        <h3 class="font-bold text-base">FinOps Copilot</h3>
      </div>
      <button onclick="toggleCopilot()" class="text-purple-200 hover:text-white"><i class="fa-solid fa-xmark text-lg"></i></button>
    </div>
    <div class="flex-1 overflow-y-auto p-4 space-y-4" id="copilot-messages">
      <div class="p-3 bg-purple-50 rounded-lg border border-purple-100 text-xs text-purple-900 leading-relaxed">
        👋 <strong>Welcome to CloudSage Copilot!</strong> Ask me anything about multi-cloud spending, anomalies, waste, or recommendations.
      </div>
      <div class="space-y-2">
        <p class="text-xs font-bold text-slate-500 uppercase tracking-wider">Suggested Questions</p>
        <button onclick="askCopilot('Summarize our total cloud expenditure across all clouds.')" class="w-full text-left text-xs bg-slate-50 hover:bg-slate-100 border border-slate-200 p-2.5 rounded-lg text-slate-700 transition">
          📊 Summarize total cloud expenditure
        </button>
        <button onclick="askCopilot('Compare our spending between AWS and Azure.')" class="w-full text-left text-xs bg-slate-50 hover:bg-slate-100 border border-slate-200 p-2.5 rounded-lg text-slate-700 transition">
          ⚖️ Compare AWS vs Azure costs
        </button>
        <button onclick="askCopilot('What are our top 5 most expensive cloud services?')" class="w-full text-left text-xs bg-slate-50 hover:bg-slate-100 border border-slate-200 p-2.5 rounded-lg text-slate-700 transition">
          🔥 Top 5 most expensive services
        </button>
        <button onclick="askCopilot('What cloud waste was detected across accounts?')" class="w-full text-left text-xs bg-slate-50 hover:bg-slate-100 border border-slate-200 p-2.5 rounded-lg text-slate-700 transition">
          🗑️ What cloud waste was detected?
        </button>
      </div>
    </div>
    <div class="p-3 border-t border-slate-200 bg-slate-50">
      <div class="flex gap-2">
        <input type="text" id="copilot-input" placeholder="Ask a FinOps question..." onkeydown="if(event.key==='Enter') submitCopilotQuery()" class="flex-1 text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-500">
        <button onclick="submitCopilotQuery()" class="px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold transition"><i class="fa-solid fa-paper-plane"></i></button>
      </div>
      <p class="text-[10px] text-slate-400 mt-2 text-center">Grounded in database truth. Strictly advisory.</p>
    </div>
  </div>

  <!-- Dashboard JavaScript Logic -->
  <script>
    let trendChartInstance = null;
    let providerChartInstance = null;

    // Tab Navigation Controller
    function switchTab(tab) {
      // 1. Update navigation active state
      document.querySelectorAll('aside nav a').forEach(a => a.classList.remove('active-nav'));
      const activeNav = document.getElementById(`nav-${tab}`);
      if (activeNav) activeNav.classList.add('active-nav');

      // 2. Hide all tab containers & show selected tab
      document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
      const activeTabContent = document.getElementById(`tab-${tab}`);
      if (activeTabContent) {
        activeTabContent.classList.remove('hidden');
      }

      // 3. Update Header Title
      const titles = {
        overview: 'Executive Overview',
        costs: 'Cloud Costs & Spend Distribution',
        anomalies: 'Cost Anomaly Detection',
        waste: 'Cloud Waste Management',
        recommendations: 'Optimization Recommendations',
        savings: 'Savings & ROI Projections',
        inventory: 'Multi-Cloud Resource Inventory',
        quality: 'FOCUS 1.0 Data Quality & Governance'
      };
      document.getElementById('page-title').innerText = titles[tab] || 'FinOps Command Center';

      // 4. Update browser URL hash without causing a page jump
      if (window.location.hash !== `#${tab}`) {
        history.pushState(null, '', `#${tab}`);
      }

      // 5. If switching to overview, resize charts
      if (tab === 'overview') {
        if (trendChartInstance) trendChartInstance.resize();
        if (providerChartInstance) providerChartInstance.resize();
      }
    }

    // Main Data Refresh Orchestrator
    async function refreshDashboard() {
      const provider = document.getElementById('filter-provider').value;
      
      // Parallel fetch across endpoints
      await Promise.allSettled([
        loadOverviewData(provider),
        loadCostsData(provider),
        loadAnomaliesData(provider),
        loadWasteData(provider),
        loadRecommendationsData(provider),
        loadSavingsData(provider),
        loadInventoryData(provider),
        loadQualityData(provider)
      ]);
    }

    // 1. Overview Tab Data
    async function loadOverviewData(provider) {
      try {
        const res = await fetch(`/api/v1/dashboard/overview?provider=${provider}`);
        if (!res.ok) return;
        const data = await res.json();
        renderOverviewKpis(data.kpi);
        renderCharts(data.cost_trends, data.provider_comparison);
        renderServicesTable(data.top_services);
        renderRecommendationsSummary(data.recommendation_summary);
      } catch (err) {
        console.error('Failed loading overview:', err);
      }
    }

    function renderOverviewKpis(kpi) {
      document.getElementById('kpi-total-spend').innerText = `$${parseFloat(kpi.total_spend).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      document.getElementById('kpi-mtd-spend').innerText = `$${parseFloat(kpi.mtd_spend).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      document.getElementById('kpi-waste-sum').innerText = `$${parseFloat(kpi.identified_monthly_waste).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      document.getElementById('kpi-waste-cnt').innerText = `${kpi.identified_waste_count} active waste items`;
      document.getElementById('kpi-savings-sum').innerText = `$${parseFloat(kpi.potential_monthly_savings).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      document.getElementById('kpi-savings-ann').innerText = `$${parseFloat(kpi.potential_annual_savings).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}/yr opportunity`;

      const mom = parseFloat(kpi.mom_change_percentage);
      const momEl = document.getElementById('kpi-mom-change');
      if (mom > 0) {
        momEl.innerHTML = `<span class="text-rose-600 font-bold"><i class="fa-solid fa-arrow-trend-up mr-1"></i>+${mom}%</span> vs last month`;
      } else if (mom < 0) {
        momEl.innerHTML = `<span class="text-emerald-600 font-bold"><i class="fa-solid fa-arrow-trend-down mr-1"></i>${mom}%</span> vs last month`;
      } else {
        momEl.innerHTML = `<span class="text-slate-500 font-bold">0.0%</span> vs last month`;
      }
    }

    function renderCharts(trends, providers) {
      // Line Trend Chart
      const trendCtx = document.getElementById('trendChart').getContext('2d');
      if (trendChartInstance) trendChartInstance.destroy();

      const labels = trends.points.map(p => p.date);
      const totals = trends.points.map(p => parseFloat(p.total_cost));
      const aws = trends.points.map(p => parseFloat(p.aws_cost));
      const azure = trends.points.map(p => parseFloat(p.azure_cost));
      const gcp = trends.points.map(p => parseFloat(p.gcp_cost));

      trendChartInstance = new Chart(trendCtx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [
            { label: 'Total', data: totals, borderColor: '#0284c7', backgroundColor: 'rgba(2, 132, 199, 0.08)', borderWidth: 2.5, tension: 0.3, fill: true },
            { label: 'AWS', data: aws, borderColor: '#f97316', borderWidth: 1.5, borderDash: [4, 4], hidden: true },
            { label: 'Azure', data: azure, borderColor: '#0ea5e9', borderWidth: 1.5, borderDash: [4, 4], hidden: true },
            { label: 'GCP', data: gcp, borderColor: '#eab308', borderWidth: 1.5, borderDash: [4, 4], hidden: true }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: true, position: 'top', labels: { boxWidth: 12, font: { size: 11 } } } },
          scales: {
            y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { callback: v => '$' + v } },
            x: { grid: { display: false } }
          }
        }
      });

      // Provider Donut Chart
      const provCtx = document.getElementById('providerChart').getContext('2d');
      if (providerChartInstance) providerChartInstance.destroy();

      const provLabels = providers.providers.map(p => p.provider);
      const provCosts = providers.providers.map(p => parseFloat(p.cost));
      const colors = { 'AWS': '#f97316', 'AZURE': '#0ea5e9', 'GCP': '#eab308' };
      const bgColors = provLabels.map(p => colors[p] || '#94a3b8');

      providerChartInstance = new Chart(provCtx, {
        type: 'doughnut',
        data: {
          labels: provLabels,
          datasets: [{ data: provCosts, backgroundColor: bgColors, borderWidth: 2, borderColor: '#ffffff' }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '70%',
          plugins: { legend: { display: false } }
        }
      });

      const pList = document.getElementById('provider-breakdown-list');
      pList.innerHTML = providers.providers.map(p => `
        <div class="flex items-center justify-between text-xs py-1 border-b border-slate-50">
          <span class="flex items-center gap-2 font-semibold text-slate-700">
            <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${colors[p.provider] || '#94a3b8'}"></span>
            ${p.provider}
          </span>
          <span class="font-bold text-slate-800">$${parseFloat(p.cost).toLocaleString(undefined, {minimumFractionDigits: 2})} <span class="text-slate-400 font-normal">(${p.percentage}%)</span></span>
        </div>
      `).join('');
    }

    function renderServicesTable(services) {
      const tbody = document.getElementById('services-table-body');
      if (!services || services.services.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4 text-slate-400">No service spend recorded.</td></tr>';
        return;
      }
      tbody.innerHTML = services.services.map(s => `
        <tr class="hover:bg-slate-50 transition">
          <td class="py-2.5 px-3 font-semibold text-slate-800">${s.service_name}</td>
          <td class="py-2.5 px-3"><span class="badge badge-${s.provider.toLowerCase()}">${s.provider}</span></td>
          <td class="py-2.5 px-3 text-right font-bold">$${parseFloat(s.cost).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
          <td class="py-2.5 px-3 text-right text-slate-500">${s.percentage}%</td>
        </tr>
      `).join('');
    }

    function renderRecommendationsSummary(recs) {
      const badge = document.getElementById('rec-count-badge');
      badge.innerText = `${recs.total_open_recommendations} Open`;
      const list = document.getElementById('recommendation-list');

      const strats = Object.entries(recs.strategy_distribution);
      if (strats.length === 0) {
        list.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">No active recommendations.</div>';
        return;
      }
      list.innerHTML = strats.slice(0, 4).map(([strat, count]) => `
        <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
          <div>
            <span class="text-xs font-bold text-slate-800 capitalize">${strat.replace(/_/g, ' ')}</span>
            <p class="text-[11px] text-slate-500">${count} proposed optimizations</p>
          </div>
          <span class="text-xs font-bold text-emerald-600"><i class="fa-solid fa-bolt mr-1"></i>Actionable</span>
        </div>
      `).join('');
    }

    // 2. Costs Tab Data
    async function loadCostsData(provider) {
      try {
        const [servRes, resRes, provRes] = await Promise.all([
          fetch(`/api/v1/dashboard/service-breakdown?provider=${provider}&limit=50`).then(r => r.json()),
          fetch(`/api/v1/dashboard/resource-costs?provider=${provider}&limit=50`).then(r => r.json()),
          fetch(`/api/v1/dashboard/provider-comparison?provider=${provider}`).then(r => r.json())
        ]);

        const totalCost = parseFloat(servRes.total_spend || 0);
        document.getElementById('costs-total-spend').innerText = `$${totalCost.toLocaleString(undefined, {minimumFractionDigits: 2})}`;

        let awsCost = 0, azureCost = 0, gcpCost = 0;
        provRes.providers.forEach(p => {
          if (p.provider === 'AWS') { awsCost = parseFloat(p.cost); document.getElementById('costs-aws-share').innerText = `${p.percentage}% of total`; }
          if (p.provider === 'AZURE') { azureCost = parseFloat(p.cost); document.getElementById('costs-azure-share').innerText = `${p.percentage}% of total`; }
          if (p.provider === 'GCP') { gcpCost = parseFloat(p.cost); document.getElementById('costs-gcp-share').innerText = `${p.percentage}% of total`; }
        });
        document.getElementById('costs-aws-spend').innerText = `$${awsCost.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('costs-azure-spend').innerText = `$${azureCost.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('costs-gcp-spend').innerText = `$${gcpCost.toLocaleString(undefined, {minimumFractionDigits: 2})}`;

        // Category breakdown progress bars
        const catContainer = document.getElementById('costs-categories-container');
        const categories = Object.entries(servRes.categories || {});
        if (categories.length === 0) {
          catContainer.innerHTML = '<div class="text-center py-4 text-slate-400 text-xs">No category data.</div>';
        } else {
          catContainer.innerHTML = categories.map(([cat, amt]) => {
            const num = parseFloat(amt);
            const pct = totalCost > 0 ? ((num / totalCost) * 100).toFixed(1) : 0;
            return `
              <div>
                <div class="flex justify-between items-center text-xs font-semibold mb-1">
                  <span class="text-slate-700">${cat}</span>
                  <span class="text-slate-900">$${num.toLocaleString(undefined, {minimumFractionDigits: 2})} (${pct}%)</span>
                </div>
                <div class="w-full bg-slate-100 rounded-full h-2">
                  <div class="bg-sky-500 h-2 rounded-full" style="width: ${pct}%"></div>
                </div>
              </div>
            `;
          }).join('');
        }

        // Services Table
        const servTbody = document.getElementById('costs-services-table-body');
        servTbody.innerHTML = servRes.services.map(s => `
          <tr class="hover:bg-slate-50 transition">
            <td class="py-3 px-3 font-semibold text-slate-800">${s.service_name}</td>
            <td class="py-3 px-3"><span class="badge badge-${s.provider.toLowerCase()}">${s.provider}</span></td>
            <td class="py-3 px-3 text-slate-600">${s.service_category}</td>
            <td class="py-3 px-3 text-right font-bold text-slate-900">$${parseFloat(s.cost).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
            <td class="py-3 px-3 text-right text-slate-500 font-medium">${s.percentage}%</td>
          </tr>
        `).join('');

        // Resources Table
        const resTbody = document.getElementById('costs-resources-table-body');
        resTbody.innerHTML = (resRes.resources || []).map(r => `
          <tr class="hover:bg-slate-50 transition">
            <td class="py-3 px-3 font-mono text-xs text-sky-700 truncate max-w-xs" title="${r.resource_id}">${r.resource_id}</td>
            <td class="py-3 px-3"><span class="badge badge-${r.provider.toLowerCase()}">${r.provider}</span></td>
            <td class="py-3 px-3 text-slate-600">${r.service_name}</td>
            <td class="py-3 px-3 text-slate-500 text-xs">${r.region}</td>
            <td class="py-3 px-3"><span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700">${r.status}</span></td>
            <td class="py-3 px-3 text-right font-bold text-slate-900">$${parseFloat(r.monthly_cost).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
          </tr>
        `).join('');
      } catch (err) {
        console.error('Failed loading costs data:', err);
      }
    }

    // 3. Anomalies Tab Data
    async function loadAnomaliesData(provider) {
      try {
        const [summary, listRes] = await Promise.all([
          fetch(`/api/v1/dashboard/anomaly-summary?provider=${provider}`).then(r => r.json()),
          fetch(`/api/v1/anomaly-detection/anomalies`).then(r => r.json())
        ]);

        document.getElementById('anom-total-count').innerText = summary.total_active_anomalies || 0;
        document.getElementById('anom-critical-count').innerText = summary.critical_count || 0;
        document.getElementById('anom-high-count').innerText = summary.high_count || 0;
        document.getElementById('anom-excess-cost').innerText = `$${parseFloat(summary.total_excess_cost || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;

        const container = document.getElementById('anomalies-list-container');
        const items = listRes.items || [];
        if (items.length === 0) {
          container.innerHTML = '<div class="text-center py-8 text-slate-400 text-sm">No active cost anomalies detected.</div>';
          return;
        }

        container.innerHTML = items.map(a => `
          <div class="card p-5 border-l-4 border-l-${a.severity === 'CRITICAL' ? 'rose-500' : 'orange-500'} hover:shadow-md transition">
            <div class="flex justify-between items-start gap-3">
              <div>
                <div class="flex items-center gap-2 mb-1">
                  <span class="badge badge-${a.provider.toLowerCase()}">${a.provider}</span>
                  <span class="badge badge-${a.severity.toLowerCase()}">${a.severity}</span>
                  <span class="text-xs text-slate-400 font-mono">${a.anomaly_category}</span>
                </div>
                <h4 class="font-bold text-base text-slate-800">${a.title}</h4>
                <p class="text-xs text-slate-600 mt-1 leading-relaxed">${a.explanation}</p>
              </div>
              <div class="text-right whitespace-nowrap">
                <span class="text-xs text-slate-400 uppercase font-bold tracking-wider">Excess Surge</span>
                <div class="text-lg font-bold text-rose-600">+$${parseFloat(a.estimated_excess_cost).toFixed(2)}</div>
                <span class="text-[11px] text-slate-500">Actual: $${parseFloat(a.actual_cost).toFixed(2)} vs Exp: $${parseFloat(a.expected_cost).toFixed(2)}</span>
              </div>
            </div>
            <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span class="flex items-center gap-2">
                <i class="fa-solid fa-chart-simple text-slate-400"></i> Z-Score: <strong>${a.z_score}</strong>
                <span class="mx-1">&bull;</span> Date: <strong>${a.anomaly_date}</strong>
                <span class="mx-1">&bull;</span> Status: <span class="font-bold text-sky-700">${a.status}</span>
              </span>
              <button onclick="askCopilot('Investigate anomaly: ${a.title}')" class="px-3 py-1 bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 rounded font-semibold text-xs transition">
                <i class="fa-solid fa-wand-magic-sparkles mr-1"></i> Investigate with Copilot
              </button>
            </div>
          </div>
        `).join('');
      } catch (err) {
        console.error('Failed loading anomalies:', err);
      }
    }

    // 4. Waste Tab Data
    async function loadWasteData(provider) {
      try {
        const [summary, findings] = await Promise.all([
          fetch(`/api/v1/dashboard/waste-summary?provider=${provider}`).then(r => r.json()),
          fetch(`/api/v1/waste-detection/findings`).then(r => r.json())
        ]);

        const monthly = parseFloat(summary.total_monthly_waste || 0);
        document.getElementById('waste-total-count').innerText = summary.total_active_waste_items || 0;
        document.getElementById('waste-monthly-cost').innerText = `$${monthly.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('waste-annual-cost').innerText = `$${(monthly * 12).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('waste-high-count').innerText = summary.severity_distribution?.HIGH || 0;

        const tbody = document.getElementById('waste-findings-table-body');
        const items = Array.isArray(findings) ? findings : (findings.items || []);
        if (items.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-slate-400">No active waste items detected.</td></tr>';
          return;
        }

        tbody.innerHTML = items.map(w => `
          <tr class="hover:bg-slate-50 transition">
            <td class="py-3 px-3">
              <div class="font-bold text-slate-800">${w.finding_title}</div>
              <div class="text-xs text-slate-500 font-mono truncate max-w-sm" title="${w.resource_id}">${w.resource_id}</div>
            </td>
            <td class="py-3 px-3 font-semibold text-xs text-slate-700">${w.waste_type}</td>
            <td class="py-3 px-3"><span class="badge badge-${(w.provider || 'cloud').toLowerCase()}">${w.provider}</span></td>
            <td class="py-3 px-3"><span class="badge badge-${(w.severity || 'medium').toLowerCase()}">${w.severity}</span></td>
            <td class="py-3 px-3 text-right font-bold text-amber-600">$${parseFloat(w.estimated_monthly_savings || 0).toFixed(2)}/mo</td>
            <td class="py-3 px-3"><span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700">${w.status}</span></td>
          </tr>
        `).join('');
      } catch (err) {
        console.error('Failed loading waste data:', err);
      }
    }

    // 5. Recommendations Tab Data
    async function loadRecommendationsData(provider) {
      try {
        const [summary, recs] = await Promise.all([
          fetch(`/api/v1/dashboard/recommendation-summary?provider=${provider}`).then(r => r.json()),
          fetch(`/api/v1/recommendations`).then(r => r.json())
        ]);

        const monthly = parseFloat(summary.potential_monthly_savings || 0);
        document.getElementById('rec-tab-count').innerText = summary.total_open_recommendations || 0;
        document.getElementById('rec-tab-monthly').innerText = `$${monthly.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('rec-tab-annual').innerText = `$${(monthly * 12).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('rec-tab-p1').innerText = summary.priority_distribution?.P1 || 0;

        const container = document.getElementById('recommendations-full-list');
        const items = Array.isArray(recs) ? recs : (recs.items || []);
        if (items.length === 0) {
          container.innerHTML = '<div class="text-center py-8 text-slate-400 text-sm">No optimization recommendations available.</div>';
          return;
        }

        container.innerHTML = items.map(r => `
          <div class="card p-5 border-l-4 border-l-emerald-500 hover:shadow-md transition">
            <div class="flex justify-between items-start gap-4">
              <div>
                <div class="flex items-center gap-2 mb-1">
                  <span class="badge badge-${r.provider.toLowerCase()}">${r.provider}</span>
                  <span class="badge bg-indigo-100 text-indigo-800 font-bold">${r.priority}</span>
                  <span class="badge bg-slate-100 text-slate-700">${r.action_type}</span>
                  <span class="text-xs text-slate-500">Risk: <strong>${r.risk_level}</strong></span>
                </div>
                <h4 class="font-bold text-base text-slate-800">${r.title}</h4>
                <p class="text-xs text-slate-600 mt-1">${r.description}</p>
                <div class="text-xs font-mono text-slate-400 mt-1 truncate max-w-xl">${r.resource_id}</div>
              </div>
              <div class="text-right whitespace-nowrap">
                <span class="text-xs text-slate-400 uppercase font-bold tracking-wider">Estimated Savings</span>
                <div class="text-xl font-bold text-emerald-600">+$${parseFloat(r.estimated_monthly_savings).toFixed(2)}/mo</div>
                <span class="text-xs text-slate-500 font-medium">+$${parseFloat(r.estimated_annual_savings).toFixed(2)}/yr</span>
              </div>
            </div>
            ${r.remediation_guide ? `
              <div class="mt-4">
                <div class="flex justify-between items-center mb-1">
                  <span class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Advisory Remediation Playbook CLI</span>
                  <button onclick="navigator.clipboard.writeText('${r.remediation_guide.replace(/'/g, "\\\'")}')" class="text-xs text-sky-600 hover:underline">
                    <i class="fa-regular fa-copy mr-1"></i>Copy
                  </button>
                </div>
                <code class="cli-snippet">${r.remediation_guide}</code>
              </div>
            ` : ''}
          </div>
        `).join('');
      } catch (err) {
        console.error('Failed loading recommendations:', err);
      }
    }

    // 6. Savings Tab Data
    async function loadSavingsData(provider) {
      try {
        const res = await fetch(`/api/v1/dashboard/savings-summary?provider=${provider}`);
        if (!res.ok) return;
        const data = await res.json();

        document.getElementById('sav-monthly-sum').innerText = `$${parseFloat(data.potential_monthly_savings || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        document.getElementById('sav-annual-sum').innerText = `$${parseFloat(data.potential_annual_savings || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
        
        // Fetch waste summary for comparative card
        const wasteRes = await fetch(`/api/v1/dashboard/waste-summary?provider=${provider}`).then(r => r.json());
        document.getElementById('sav-waste-sum').innerText = `$${parseFloat(wasteRes.total_monthly_waste || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;

        // Providers
        const provContainer = document.getElementById('savings-provider-container');
        const pEntries = Object.entries(data.savings_by_provider || {});
        provContainer.innerHTML = pEntries.map(([p, amt]) => `
          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
            <span class="font-bold text-slate-700 flex items-center gap-2">
              <span class="badge badge-${p.toLowerCase()}">${p}</span>
            </span>
            <span class="font-bold text-emerald-600">+$${parseFloat(amt).toFixed(2)}/mo</span>
          </div>
        `).join('');

        // Priorities
        const prioContainer = document.getElementById('savings-priority-container');
        const prioEntries = Object.entries(data.savings_by_priority || {});
        prioContainer.innerHTML = prioEntries.map(([tier, amt]) => `
          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
            <span class="font-bold text-slate-800">${tier} Priority Tier</span>
            <span class="font-bold text-slate-900">$${parseFloat(amt).toFixed(2)}/mo</span>
          </div>
        `).join('');
      } catch (err) {
        console.error('Failed loading savings:', err);
      }
    }

    // 7. Inventory Tab Data
    async function loadInventoryData(provider) {
      try {
        const [summary, resources] = await Promise.all([
          fetch(`/api/v1/dashboard/inventory-summary?provider=${provider}`).then(r => r.json()),
          fetch(`/api/v1/inventory/resources`).then(r => r.json())
        ]);

        const items = Array.isArray(resources) ? resources : (resources.items || []);
        document.getElementById('inv-total-count').innerText = summary.total_resources || 0;
        document.getElementById('inv-tag-coverage').innerText = `${parseFloat(summary.tag_coverage_percentage || 100).toFixed(1)}%`;
        document.getElementById('inv-active-count').innerText = items.filter(r => r.status && r.status.toLowerCase().includes('run')).length || summary.total_resources;
        document.getElementById('inv-untagged-count').innerText = summary.untagged_resources_count || 0;

        const tbody = document.getElementById('inventory-table-body');
        if (items.length === 0) {
          tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-slate-400">No discovered resources.</td></tr>';
          return;
        }

        tbody.innerHTML = items.map(r => `
          <tr class="hover:bg-slate-50 transition">
            <td class="py-3 px-3 font-mono text-xs text-sky-700 truncate max-w-xs" title="${r.resource_id}">${r.resource_id}</td>
            <td class="py-3 px-3"><span class="badge badge-${r.provider.toLowerCase()}">${r.provider}</span></td>
            <td class="py-3 px-3 text-slate-700 text-xs font-semibold">${r.service_name}</td>
            <td class="py-3 px-3 text-slate-500 text-xs font-mono">${r.resource_type}</td>
            <td class="py-3 px-3 text-slate-600 text-xs">${r.region}</td>
            <td class="py-3 px-3"><span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-50 text-emerald-700">${r.status}</span></td>
            <td class="py-3 px-3 text-xs text-slate-600">${r.owner || 'DevOps'} (${r.tags?.cost_center || 'General'})</td>
          </tr>
        `).join('');
      } catch (err) {
        console.error('Failed loading inventory:', err);
      }
    }

    // 8. Quality Tab Data
    async function loadQualityData(provider) {
      try {
        const res = await fetch(`/api/v1/dashboard/data-quality-summary?provider=${provider}`);
        if (!res.ok) return;
        const q = await res.json();
        document.getElementById('qual-overall-score').innerText = `${parseFloat(q.overall_quality_score || 100).toFixed(1)}%`;
        document.getElementById('qual-focus-pct').innerText = `${parseFloat(q.focus_compliance_percentage || 100).toFixed(1)}%`;
        document.getElementById('qual-tag-score').innerText = `${parseFloat(q.tag_quality_score || 100).toFixed(1)}%`;
        document.getElementById('qual-curr-score').innerText = `${parseFloat(q.currency_uniformity_score || 100).toFixed(1)}%`;
      } catch (err) {
        console.error('Failed loading quality:', err);
      }
    }

    // Copilot Drawer
    function toggleCopilot() {
      const drawer = document.getElementById('copilot-drawer');
      drawer.classList.toggle('translate-x-full');
    }

    async function submitCopilotQuery() {
      const input = document.getElementById('copilot-input');
      const q = input.value.trim();
      if (!q) return;
      input.value = '';
      await askCopilot(q);
    }

    async function askCopilot(question) {
      const drawer = document.getElementById('copilot-drawer');
      if (drawer.classList.contains('translate-x-full')) {
        drawer.classList.remove('translate-x-full');
      }
      const msgContainer = document.getElementById('copilot-messages');
      msgContainer.innerHTML += `
        <div class="p-3 bg-slate-100 rounded-lg text-xs text-slate-800 ml-6 text-right">
          <strong>You:</strong> ${question}
        </div>
        <div class="p-3 bg-purple-50 rounded-lg text-xs text-purple-900 mr-6" id="loading-copilot">
          <i class="fa-solid fa-spinner fa-spin mr-1"></i> Analyzing FinOps database...
        </div>
      `;
      msgContainer.scrollTop = msgContainer.scrollHeight;

      try {
        const res = await fetch('/api/v1/copilot/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: question, user_id: 'dashboard_user' })
        });
        const data = await res.json();
        const loader = document.getElementById('loading-copilot');
        if (loader) loader.remove();

        msgContainer.innerHTML += `
          <div class="p-3 bg-white border border-purple-200 rounded-lg text-xs text-slate-800 mr-4 shadow-sm space-y-2">
            <div class="font-bold text-purple-900 flex items-center gap-1.5">
              <i class="fa-solid fa-wand-magic-sparkles text-purple-600"></i> CloudSage Copilot
            </div>
            <div class="text-slate-700 whitespace-pre-line leading-relaxed">${data.content}</div>
          </div>
        `;
        msgContainer.scrollTop = msgContainer.scrollHeight;
      } catch (err) {
        const loader = document.getElementById('loading-copilot');
        if (loader) loader.remove();
        msgContainer.innerHTML += `<div class="p-2 bg-rose-50 text-rose-700 text-xs rounded">Failed to query Copilot.</div>`;
      }
    }

    function exportData(fmt) {
      const provider = document.getElementById('filter-provider').value;
      window.location.href = `/api/v1/dashboard/export?format=${fmt}&section=overview&provider=${provider}`;
    }

    function handleHashRoute() {
      const hash = (window.location.hash || '').replace('#', '').trim();
      if (hash === 'copilot') {
        toggleCopilot();
      } else if (hash && document.getElementById(`tab-${hash}`)) {
        switchTab(hash);
      }
    }

    window.addEventListener('hashchange', handleHashRoute);
    window.addEventListener('popstate', handleHashRoute);

    // Auto-initialize on DOM ready
    window.addEventListener('DOMContentLoaded', () => {
      handleHashRoute();
      refreshDashboard();
    });
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
