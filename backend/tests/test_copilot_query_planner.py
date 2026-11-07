"""
Unit Tests for Copilot Safe Analytical Query Planner.
Verifies target dataset allowlists, aggregation operations, grouping rules,
and Pydantic serialization.
"""

from datetime import datetime, timezone
import pytest

from backend.app.core.enums import CopilotIntent
from backend.app.copilot.query_planner import (
    ALLOWED_AGGREGATIONS,
    ALLOWED_DATASETS,
    QueryPlan,
    QueryPlanner,
)


def test_query_plan_total_cloud_spend():
    """Verify query plan for total spend points to billing_records."""
    entities = {"providers": ["AWS"], "time_window": "last_30_days"}
    plan = QueryPlanner.plan(CopilotIntent.TOTAL_CLOUD_SPEND, entities)

    assert plan.target_dataset == "billing_records"
    assert "SUM:unblended_cost" in plan.aggregations
    assert plan.filters.get("provider") == "AWS"
    assert plan.target_dataset in ALLOWED_DATASETS


def test_query_plan_provider_comparison():
    """Verify provider comparison plan groups by provider."""
    entities = {}
    plan = QueryPlanner.plan(CopilotIntent.PROVIDER_COST_COMPARISON, entities)

    assert plan.target_dataset == "billing_records"
    assert "provider" in plan.group_by
    assert "SUM:unblended_cost" in plan.aggregations


def test_query_plan_cost_anomalies():
    """Verify anomaly explanation queries cost_anomalies dataset."""
    entities = {"providers": ["Azure"]}
    plan = QueryPlanner.plan(CopilotIntent.COST_ANOMALY_EXPLANATION, entities)

    assert plan.target_dataset == "cost_anomalies"
    assert "COUNT:*" in plan.aggregations
    assert plan.filters.get("status") == "OPEN"


def test_query_plan_waste_detection():
    """Verify waste detection queries waste_detections dataset."""
    entities = {}
    plan = QueryPlanner.plan(CopilotIntent.WASTE_DETECTION_ANALYSIS, entities)

    assert plan.target_dataset == "waste_detections"
    assert "waste_type" in plan.group_by
    assert plan.filters.get("status") == "ACTIVE"


def test_query_plan_recommendations():
    """Verify optimization recommendations plan queries recommendations dataset."""
    entities = {"providers": ["GCP"]}
    plan = QueryPlanner.plan(CopilotIntent.OPTIMIZATION_RECOMMENDATIONS, entities)

    assert plan.target_dataset == "recommendations"
    assert plan.filters.get("provider") == "GCP"
    assert "strategy_id" in plan.group_by


def test_query_plan_to_schema():
    """Verify serialization to Pydantic QueryPlanSchema."""
    entities = {"providers": ["AWS"]}
    plan = QueryPlanner.plan(CopilotIntent.SERVICE_COST_BREAKDOWN, entities)
    schema = plan.to_schema()

    assert schema.intent == CopilotIntent.SERVICE_COST_BREAKDOWN.value
    assert schema.target_dataset == "billing_records"
    assert "service_name" in schema.group_by
