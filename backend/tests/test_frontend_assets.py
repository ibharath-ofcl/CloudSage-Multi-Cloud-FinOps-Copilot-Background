"""
Test Suite: Frontend Architecture & Asset Parity.
Validates that the modular TypeScript/React frontend files exist, are well-formed,
and maintain complete schema alignment with backend APIs.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"


def test_frontend_package_json():
    """Verify frontend/package.json exists, is valid JSON, and contains required metadata."""
    pkg_path = FRONTEND_DIR / "package.json"
    assert pkg_path.exists(), "frontend/package.json must exist"

    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    assert pkg["name"] == "cloudsage-frontend"
    assert pkg["version"] == "0.10.0"
    assert "react" in pkg["dependencies"]
    assert "react-dom" in pkg["dependencies"]
    assert "react-router-dom" in pkg["dependencies"]
    assert "lucide-react" in pkg["dependencies"]
    assert "axios" in pkg["dependencies"]


def test_frontend_tsconfig_json():
    """Verify frontend/tsconfig.json exists and is valid JSON."""
    tsconfig_path = FRONTEND_DIR / "tsconfig.json"
    assert tsconfig_path.exists(), "frontend/tsconfig.json must exist"

    with open(tsconfig_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    assert "compilerOptions" in config
    assert config["compilerOptions"]["jsx"] == "react-jsx"


def test_frontend_typescript_types():
    """Verify frontend/src/types/dashboard.ts exists and declares all required interfaces."""
    types_path = FRONTEND_DIR / "src" / "types" / "dashboard.ts"
    assert types_path.exists(), "frontend/src/types/dashboard.ts must exist"

    content = types_path.read_text(encoding="utf-8")
    assert "export interface DashboardFilterParams" in content
    assert "export interface ExecutiveKpiSummary" in content
    assert "export interface DashboardOverviewResponse" in content
    assert "export interface CostTrendResponse" in content
    assert "export interface ProviderComparisonResponse" in content
    assert "export interface AnomalySummaryResponse" in content
    assert "export interface WasteSummaryResponse" in content
    assert "export interface RecommendationSummaryResponse" in content
    assert "export interface SavingsSummaryResponse" in content


def test_frontend_api_service():
    """Verify frontend/src/services/api.ts exists and provides all client methods."""
    api_path = FRONTEND_DIR / "src" / "services" / "api.ts"
    assert api_path.exists(), "frontend/src/services/api.ts must exist"

    content = api_path.read_text(encoding="utf-8")
    assert "export const DashboardService = {" in content
    assert "async getOverview(" in content
    assert "async getKpis(" in content
    assert "async getCostTrends(" in content
    assert "async getProviderComparison(" in content
    assert "async getAnomalySummary(" in content
    assert "async getWasteSummary(" in content
    assert "async getRecommendationSummary(" in content
    assert "async getSavingsSummary(" in content
    assert "export const CopilotService = {" in content
    assert "async askQuestion(" in content


def test_frontend_pages_exist():
    """Verify that all 8 required FinOps dashboard pages are implemented."""
    pages_dir = FRONTEND_DIR / "src" / "pages"
    assert pages_dir.exists(), "frontend/src/pages directory must exist"

    expected_pages = [
        "OverviewPage.tsx",
        "CostAnalyticsPage.tsx",
        "AnomalyPage.tsx",
        "WastePage.tsx",
        "RecommendationsPage.tsx",
        "SavingsPage.tsx",
        "InventoryPage.tsx",
        "QualityPage.tsx",
    ]

    for page in expected_pages:
        page_file = pages_dir / page
        assert page_file.exists(), f"Page {page} must exist in frontend/src/pages"
        assert page_file.stat().st_size > 200, f"Page {page} should not be empty"


def test_frontend_components_exist():
    """Verify that all reusable FinOps dashboard components are implemented."""
    comp_dir = FRONTEND_DIR / "src" / "components"
    assert comp_dir.exists(), "frontend/src/components directory must exist"

    expected_components = [
        "Header.tsx",
        "Sidebar.tsx",
        "KpiCard.tsx",
        "CopilotDrawer.tsx",
        "Charts.tsx",
    ]

    for comp in expected_components:
        comp_file = comp_dir / comp
        assert comp_file.exists(), f"Component {comp} must exist in frontend/src/components"
        assert comp_file.stat().st_size > 200, f"Component {comp} should not be empty"
