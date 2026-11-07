"""
Safe Analytical Query Planner for CloudSage AI FinOps Copilot.
Constructs deterministic, allowlisted query plans from classified intents and extracted entities.
Guarantees strictly read-only execution without exposing raw SQL or schema internals.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.core.enums import CopilotIntent
from backend.app.copilot.schemas import QueryPlanSchema

# Allowlisted target datasets
ALLOWED_DATASETS = {
    "billing_records",
    "cloud_resources",
    "waste_detections",
    "cost_anomalies",
    "recommendations",
}

# Allowlisted aggregation functions
ALLOWED_AGGREGATIONS = {"SUM", "COUNT", "AVG", "MIN", "MAX"}

# Allowlisted grouping fields per dataset
ALLOWED_GROUP_FIELDS = {
    "billing_records": {"provider", "service_name", "region", "pricing_model", "usage_start_time"},
    "cloud_resources": {"provider", "resource_type", "region", "status"},
    "waste_detections": {"provider", "waste_type", "severity", "status"},
    "cost_anomalies": {"provider", "anomaly_category", "severity", "status"},
    "recommendations": {"provider", "strategy_id", "priority", "status", "action"},
}


@dataclass
class QueryPlan:
    """Internal representation of an analytical execution plan."""
    intent: CopilotIntent
    target_dataset: str
    filters: Dict[str, Any] = field(default_factory=dict)
    aggregations: List[str] = field(default_factory=list)
    group_by: List[str] = field(default_factory=list)
    time_range: Dict[str, Any] = field(default_factory=dict)
    order_by: Optional[str] = None
    limit: int = 10

    def to_schema(self) -> QueryPlanSchema:
        """Serializes to Pydantic QueryPlanSchema."""
        return QueryPlanSchema(
            intent=self.intent.value,
            target_dataset=self.target_dataset,
            filters=self.filters,
            aggregations=self.aggregations,
            group_by=self.group_by,
            time_range=self.time_range,
        )


class QueryPlanner:
    """Generates safe analytical query plans based on intent and entities."""

    @classmethod
    def plan(cls, intent: CopilotIntent, entities: Dict[str, Any]) -> QueryPlan:
        """Produces a deterministic, allowlisted QueryPlan."""
        providers = entities.get("providers", [])
        services = entities.get("services", [])
        time_window = entities.get("time_window", "last_30_days")
        start_time = entities.get("start_time")
        end_time = entities.get("end_time")

        base_filters: Dict[str, Any] = {}
        if providers:
            base_filters["provider"] = providers[0] if len(providers) == 1 else providers
        if services:
            base_filters["service_name"] = services[0] if len(services) == 1 else services

        time_range = {}
        if start_time:
            time_range["start_time"] = start_time.isoformat() if isinstance(start_time, datetime) else str(start_time)
        if end_time:
            time_range["end_time"] = end_time.isoformat() if isinstance(end_time, datetime) else str(end_time)

        # Plan according to intent
        if intent == CopilotIntent.TOTAL_CLOUD_SPEND:
            return QueryPlan(
                intent=intent,
                target_dataset="billing_records",
                filters=base_filters,
                aggregations=["SUM:unblended_cost", "COUNT:*"],
                group_by=["provider"],
                time_range=time_range,
                order_by="SUM:unblended_cost DESC",
                limit=10,
            )

        elif intent == CopilotIntent.PROVIDER_COST_COMPARISON:
            return QueryPlan(
                intent=intent,
                target_dataset="billing_records",
                filters={},
                aggregations=["SUM:unblended_cost", "COUNT:*"],
                group_by=["provider"],
                time_range=time_range,
                order_by="SUM:unblended_cost DESC",
                limit=5,
            )

        elif intent == CopilotIntent.SERVICE_COST_BREAKDOWN:
            return QueryPlan(
                intent=intent,
                target_dataset="billing_records",
                filters=base_filters,
                aggregations=["SUM:unblended_cost", "COUNT:*"],
                group_by=["service_name"],
                time_range=time_range,
                order_by="SUM:unblended_cost DESC",
                limit=10,
            )

        elif intent == CopilotIntent.RESOURCE_COST_ANALYSIS:
            res_filters = dict(base_filters)
            if entities.get("resource_ids"):
                res_filters["resource_id"] = entities["resource_ids"][0]
            return QueryPlan(
                intent=intent,
                target_dataset="billing_records",
                filters=res_filters,
                aggregations=["SUM:unblended_cost"],
                group_by=["resource_id"],
                time_range=time_range,
                order_by="SUM:unblended_cost DESC",
                limit=10,
            )

        elif intent == CopilotIntent.COST_TREND_ANALYSIS:
            return QueryPlan(
                intent=intent,
                target_dataset="billing_records",
                filters=base_filters,
                aggregations=["SUM:unblended_cost"],
                group_by=["usage_start_time"],
                time_range=time_range,
                order_by="usage_start_time ASC",
                limit=30,
            )

        elif intent == CopilotIntent.COST_ANOMALY_EXPLANATION:
            anom_filters = {"status": "OPEN"}
            if providers:
                anom_filters["provider"] = providers[0]
            return QueryPlan(
                intent=intent,
                target_dataset="cost_anomalies",
                filters=anom_filters,
                aggregations=["COUNT:*", "SUM:estimated_excess_cost"],
                group_by=["anomaly_category"],
                time_range=time_range,
                order_by="estimated_excess_cost DESC",
                limit=10,
            )

        elif intent == CopilotIntent.WASTE_DETECTION_ANALYSIS:
            waste_filters = {"status": "ACTIVE"}
            if providers:
                waste_filters["provider"] = providers[0]
            return QueryPlan(
                intent=intent,
                target_dataset="waste_detections",
                filters=waste_filters,
                aggregations=["COUNT:*", "SUM:estimated_monthly_waste"],
                group_by=["waste_type"],
                time_range=time_range,
                order_by="estimated_monthly_waste DESC",
                limit=10,
            )

        elif intent == CopilotIntent.OPTIMIZATION_RECOMMENDATIONS:
            rec_filters = {"status": "OPEN"}
            if providers:
                rec_filters["provider"] = providers[0]
            return QueryPlan(
                intent=intent,
                target_dataset="recommendations",
                filters=rec_filters,
                aggregations=["COUNT:*", "SUM:estimated_monthly_savings"],
                group_by=["strategy_id", "priority"],
                time_range=time_range,
                order_by="estimated_monthly_savings DESC",
                limit=10,
            )

        elif intent == CopilotIntent.SAVINGS_OPPORTUNITY:
            return QueryPlan(
                intent=intent,
                target_dataset="recommendations",
                filters={"status": "OPEN"},
                aggregations=["SUM:estimated_monthly_savings", "SUM:estimated_annual_savings", "COUNT:*"],
                group_by=["provider"],
                time_range=time_range,
                order_by="estimated_monthly_savings DESC",
                limit=5,
            )

        elif intent == CopilotIntent.RESOURCE_UTILIZATION:
            return QueryPlan(
                intent=intent,
                target_dataset="cloud_resources",
                filters=base_filters,
                aggregations=["COUNT:*"],
                group_by=["resource_type", "status"],
                time_range=time_range,
                limit=10,
            )

        elif intent in (CopilotIntent.OWNER_COST_ANALYSIS, CopilotIntent.COST_CENTER_ANALYSIS):
            tag_filters = dict(base_filters)
            if entities.get("owner"):
                tag_filters["owner"] = entities["owner"]
            if entities.get("cost_center"):
                tag_filters["cost_center"] = entities["cost_center"]
            return QueryPlan(
                intent=intent,
                target_dataset="billing_records",
                filters=tag_filters,
                aggregations=["SUM:unblended_cost", "COUNT:*"],
                group_by=["provider"],
                time_range=time_range,
                limit=10,
            )

        elif intent == CopilotIntent.BILLING_DATA_QUALITY:
            return QueryPlan(
                intent=intent,
                target_dataset="billing_records",
                filters={"provider": providers[0] if providers else "ALL"},
                aggregations=["COUNT:*"],
                group_by=["pricing_model"],
                time_range=time_range,
                limit=10,
            )

        # Default for GENERAL_FINOPS_QUESTION or UNSUPPORTED
        return QueryPlan(
            intent=intent,
            target_dataset="billing_records",
            filters={},
            aggregations=["COUNT:*"],
            group_by=[],
            time_range=time_range,
            limit=0,
        )
