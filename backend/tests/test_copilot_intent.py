"""
Unit Tests for FinOps Intent Classification and Entity Extraction.
Tests classification across all 15 FinOps intents and entity parsing for providers,
services, time windows, resource IDs, and tags.
"""

import pytest
from backend.app.core.enums import CloudProvider, CopilotIntent
from backend.app.copilot.intent import IntentClassifier


def test_classify_all_15_intents():
    """Verify that representative queries for all 15 intents map correctly."""
    test_cases = [
        ("What is our total cloud spend this month?", CopilotIntent.TOTAL_CLOUD_SPEND),
        ("Compare cloud spending between AWS and Azure", CopilotIntent.PROVIDER_COST_COMPARISON),
        ("Show me the top 5 most expensive services", CopilotIntent.SERVICE_COST_BREAKDOWN),
        ("What is the cost of resource i-0123456789?", CopilotIntent.RESOURCE_COST_ANALYSIS),
        ("What are our daily spending cost trends?", CopilotIntent.COST_TREND_ANALYSIS),
        ("Why did our AWS bill spike with a cost anomaly?", CopilotIntent.COST_ANOMALY_EXPLANATION),
        ("What cloud waste was detected across accounts?", CopilotIntent.WASTE_DETECTION_ANALYSIS),
        ("What are your top recommendations to optimize cloud spend?", CopilotIntent.OPTIMIZATION_RECOMMENDATIONS),
        ("How much potential savings can we achieve?", CopilotIntent.SAVINGS_OPPORTUNITY),
        ("Show underutilized instances with low CPU utilization", CopilotIntent.RESOURCE_UTILIZATION),
        ("Break down costs by owner tag", CopilotIntent.OWNER_COST_ANALYSIS),
        ("Show spending by cost center 1042", CopilotIntent.COST_CENTER_ANALYSIS),
        ("What is our billing data quality score?", CopilotIntent.BILLING_DATA_QUALITY),
        ("What is FOCUS 1.0 specification?", CopilotIntent.GENERAL_FINOPS_QUESTION),
        ("What is the weather like in New York today?", CopilotIntent.UNSUPPORTED_OR_AMBIGUOUS_QUERY),
    ]

    for query, expected_intent in test_cases:
        classified = IntentClassifier.classify(query)
        assert classified == expected_intent, f"Failed for query '{query}': expected {expected_intent}, got {classified}"


def test_extract_entities_providers():
    """Verify cloud provider extraction across AWS, Azure, and GCP."""
    res1 = IntentClassifier.extract_entities("Show AWS EC2 costs")
    assert CloudProvider.AWS.value in res1["providers"]

    res2 = IntentClassifier.extract_entities("Compare Azure and GCP expenditure")
    assert CloudProvider.AZURE.value in res2["providers"]
    assert CloudProvider.GCP.value in res2["providers"]


def test_extract_entities_services():
    """Verify service entity extraction."""
    res = IntentClassifier.extract_entities("How much did Amazon EC2, S3, and BigQuery cost?")
    assert "Amazon EC2" in res["services"]
    assert "Amazon S3" in res["services"]
    assert "BigQuery" in res["services"]


def test_extract_entities_resource_ids():
    """Verify resource ID pattern extraction."""
    query = "Inspect cost of i-0123456789abcdef0 and vol-0987654321fedcba0"
    res = IntentClassifier.extract_entities(query)
    assert "i-0123456789abcdef0" in res["resource_ids"]
    assert "vol-0987654321fedcba0" in res["resource_ids"]


def test_extract_entities_time_windows():
    """Verify time window extraction and datetime calculation."""
    res_7d = IntentClassifier.extract_entities("Cost over the last 7 days")
    assert res_7d["time_window"] == "last_7_days"
    assert res_7d["start_time"] is not None

    res_yesterday = IntentClassifier.extract_entities("Show spend for yesterday")
    assert res_yesterday["time_window"] == "yesterday"

    res_last_month = IntentClassifier.extract_entities("Spending during last month")
    assert res_last_month["time_window"] == "last_month"


def test_extract_entities_owner_and_cost_center():
    """Verify owner tag and cost center extraction."""
    res = IntentClassifier.extract_entities("Show costs for owner: analytics_team and cost-center: CC-9988")
    assert res["owner"] == "analytics_team"
    assert res["cost_center"] == "CC-9988"
