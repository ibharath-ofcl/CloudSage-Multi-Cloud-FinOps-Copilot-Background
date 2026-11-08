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
  </style>
</head>
<body class="flex h-screen overflow-hidden">
  <!-- Navigation Sidebar -->
  <aside class="sidebar w-64 flex flex-col z-20 transition-all duration-300">
    <div class="h-16 flex items-center px-6 border-b border-slate-800 gap-3">
      <i class="fa-solid fa-cloud-bolt text-sky-400 text-2xl"></i>
      <div>
        <h1 class="text-white font-bold text-lg tracking-tight">CloudSage</h1>
        <p class="text-xs text-slate-400 font-medium">FinOps Copilot v0.10.0</p>
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
      <!-- KPI Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5" id="kpi-grid">
        <!-- 1. Total Spend -->
        <div class="card p-5 border-l-4 border-l-sky-500">
          <div class="flex justify-between items-start">
            <span class="kpi-title">Total Cloud Spend</span>
            <i class="fa-solid fa-wallet text-sky-500 text-lg"></i>
          </div>
          <div class="kpi-value mt-2" id="kpi-total-spend">$0.00</div>
          <p class="text-xs text-slate-500 mt-1 font-medium" id="kpi-total-sub">FOCUS normalized</p>
        </div>

        <!-- 2. MTD Spend & MoM Change -->
        <div class="card p-5 border-l-4 border-l-indigo-500">
          <div class="flex justify-between items-start">
            <span class="kpi-title">Month-To-Date Spend</span>
            <i class="fa-solid fa-calendar-day text-indigo-500 text-lg"></i>
          </div>
          <div class="kpi-value mt-2" id="kpi-mtd-spend">$0.00</div>
          <p class="text-xs mt-1 font-semibold" id="kpi-mom-change"><span class="text-slate-500">0.0% MoM</span></p>
        </div>

        <!-- 3. Active Waste -->
        <div class="card p-5 border-l-4 border-l-amber-500">
          <div class="flex justify-between items-start">
            <span class="kpi-title">Identified Waste</span>
            <i class="fa-solid fa-trash-arrow-up text-amber-500 text-lg"></i>
          </div>
          <div class="kpi-value mt-2 text-amber-600" id="kpi-waste-sum">$0.00</div>
          <p class="text-xs text-slate-500 mt-1" id="kpi-waste-cnt">0 active waste items</p>
        </div>

        <!-- 4. Potential Monthly Savings -->
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
        <!-- Historical Cost Trend -->
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

        <!-- Provider Distribution Donut -->
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
        <!-- Top Cost Drivers -->
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

        <!-- Advisory Recommendations & Anomalies -->
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

    async function fetchOverview() {
      const provider = document.getElementById('filter-provider').value;
      const url = `/api/v1/dashboard/overview?provider=${provider}`;
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('API failure');
        return await res.json();
      } catch (err) {
        console.error('Failed to fetch dashboard overview:', err);
        return null;
      }
    }

    function renderKpis(kpi) {
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
      // 1. Trend Chart
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

      // 2. Provider Donut Chart
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

      // Render Provider Legend & Percentages
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

    function renderServices(services) {
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

    function renderRecommendations(recs) {
      const badge = document.getElementById('rec-count-badge');
      badge.innerText = `${recs.total_open_recommendations} Open`;
      const list = document.getElementById('recommendation-list');

      // Strategies distribution pills
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

    async function refreshDashboard() {
      const data = await fetchOverview();
      if (!data) return;
      renderKpis(data.kpi);
      renderCharts(data.cost_trends, data.provider_comparison);
      renderServices(data.top_services);
      renderRecommendations(data.recommendation_summary);
    }

    function switchTab(tab) {
      document.querySelectorAll('aside nav a').forEach(a => a.classList.remove('active-nav'));
      const activeEl = document.getElementById(`nav-${tab}`);
      if (activeEl) activeEl.classList.add('active-nav');
      document.getElementById('page-title').innerText = tab.charAt(0).toUpperCase() + tab.slice(1);
    }

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
      const msgContainer = document.getElementById('copilot-messages');
      // Append User Message
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
        document.getElementById('loading-copilot').remove();

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
        document.getElementById('loading-copilot').remove();
        msgContainer.innerHTML += `<div class="p-2 bg-rose-50 text-rose-700 text-xs rounded">Failed to query Copilot.</div>`;
      }
    }

    function exportData(fmt) {
      const provider = document.getElementById('filter-provider').value;
      window.location.href = `/api/v1/dashboard/export?format=${fmt}&section=overview&provider=${provider}`;
    }

    // Auto-initialize on load
    window.addEventListener('DOMContentLoaded', refreshDashboard);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
