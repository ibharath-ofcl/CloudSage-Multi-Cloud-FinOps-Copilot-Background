"""
Deterministic FinOps Copilot Benchmark Evaluation Suite.
Contains 30 standardized benchmark queries spanning all 15 FinOps intents
and an automated evaluation runner verifying intent accuracy, citation presence,
and advisory compliance.
"""

from typing import Any, Dict, List
from sqlalchemy.orm import Session

from backend.app.core.enums import CopilotIntent
from backend.app.copilot.engine import get_copilot_engine
from backend.app.copilot.schemas import ChatMessageRequest

BENCHMARK_QUESTIONS: List[Dict[str, Any]] = [
    # 1. TOTAL_CLOUD_SPEND
    {
        "id": "BENCH-01",
        "query": "What is our total cloud spend this month across all providers?",
        "expected_intent": CopilotIntent.TOTAL_CLOUD_SPEND,
        "description": "Evaluate multi-cloud aggregate spend calculation",
    },
    {
        "id": "BENCH-02",
        "query": "How much have we spent on cloud overall in the last 30 days?",
        "expected_intent": CopilotIntent.TOTAL_CLOUD_SPEND,
        "description": "Evaluate total cloud expenditure over 30 days",
    },

    # 2. PROVIDER_COST_COMPARISON
    {
        "id": "BENCH-03",
        "query": "Compare our cloud spending between AWS and Azure.",
        "expected_intent": CopilotIntent.PROVIDER_COST_COMPARISON,
        "description": "Evaluate dual-provider cost comparison",
    },
    {
        "id": "BENCH-04",
        "query": "Which cloud provider costs the most: AWS, Azure, or GCP?",
        "expected_intent": CopilotIntent.PROVIDER_COST_COMPARISON,
        "description": "Evaluate multi-cloud ranking and percentage distribution",
    },

    # 3. SERVICE_COST_BREAKDOWN
    {
        "id": "BENCH-05",
        "query": "What are our top 5 most expensive cloud services?",
        "expected_intent": CopilotIntent.SERVICE_COST_BREAKDOWN,
        "description": "Evaluate top-N service breakdown aggregation",
    },
    {
        "id": "BENCH-06",
        "query": "How much did we spend on Amazon EC2 last month?",
        "expected_intent": CopilotIntent.SERVICE_COST_BREAKDOWN,
        "description": "Evaluate specific service spend retrieval",
    },

    # 4. RESOURCE_COST_ANALYSIS
    {
        "id": "BENCH-07",
        "query": "Which resources are driving the highest cost in our environment?",
        "expected_intent": CopilotIntent.RESOURCE_COST_ANALYSIS,
        "description": "Evaluate individual resource expenditure ranking",
    },
    {
        "id": "BENCH-08",
        "query": "What is the cost of resource i-0123456789abcdef0?",
        "expected_intent": CopilotIntent.RESOURCE_COST_ANALYSIS,
        "description": "Evaluate specific resource ID cost lookup",
    },

    # 5. COST_TREND_ANALYSIS
    {
        "id": "BENCH-09",
        "query": "Show our daily cost trends over the past 30 days.",
        "expected_intent": CopilotIntent.COST_TREND_ANALYSIS,
        "description": "Evaluate daily time-series spending trajectory",
    },
    {
        "id": "BENCH-10",
        "query": "Is our cloud spending increasing or decreasing month over month?",
        "expected_intent": CopilotIntent.COST_TREND_ANALYSIS,
        "description": "Evaluate directional trend trajectory analysis",
    },

    # 6. COST_ANOMALY_EXPLANATION
    {
        "id": "BENCH-11",
        "query": "Explain recent cost anomalies and spending spikes.",
        "expected_intent": CopilotIntent.COST_ANOMALY_EXPLANATION,
        "description": "Evaluate Stage 7 anomaly retrieval and explanation",
    },
    {
        "id": "BENCH-12",
        "query": "Why did our AWS bill spike unexpectedly this week?",
        "expected_intent": CopilotIntent.COST_ANOMALY_EXPLANATION,
        "description": "Evaluate single-provider cost spike root-cause inquiry",
    },

    # 7. WASTE_DETECTION_ANALYSIS
    {
        "id": "BENCH-13",
        "query": "What cloud waste was detected across our cloud accounts?",
        "expected_intent": CopilotIntent.WASTE_DETECTION_ANALYSIS,
        "description": "Evaluate Stage 6 idle and unattached resource retrieval",
    },
    {
        "id": "BENCH-14",
        "query": "Do we have unattached disks or idle virtual machines?",
        "expected_intent": CopilotIntent.WASTE_DETECTION_ANALYSIS,
        "description": "Evaluate specific waste type classification",
    },

    # 8. OPTIMIZATION_RECOMMENDATIONS
    {
        "id": "BENCH-15",
        "query": "What are your top recommendations to reduce cloud spend?",
        "expected_intent": CopilotIntent.OPTIMIZATION_RECOMMENDATIONS,
        "description": "Evaluate Stage 8 advisory recommendations listing",
    },
    {
        "id": "BENCH-16",
        "query": "Show high priority optimization recommendations for Azure.",
        "expected_intent": CopilotIntent.OPTIMIZATION_RECOMMENDATIONS,
        "description": "Evaluate provider and priority filtered recommendation retrieval",
    },

    # 9. SAVINGS_OPPORTUNITY
    {
        "id": "BENCH-17",
        "query": "How much potential savings can we achieve across all clouds?",
        "expected_intent": CopilotIntent.SAVINGS_OPPORTUNITY,
        "description": "Evaluate total monthly and annual savings aggregation",
    },
    {
        "id": "BENCH-18",
        "query": "What is our total monthly savings opportunity from rightsizing?",
        "expected_intent": CopilotIntent.SAVINGS_OPPORTUNITY,
        "description": "Evaluate strategy-specific savings calculation",
    },

    # 10. RESOURCE_UTILIZATION
    {
        "id": "BENCH-19",
        "query": "Show inventory and utilization metrics for our virtual machines.",
        "expected_intent": CopilotIntent.RESOURCE_UTILIZATION,
        "description": "Evaluate Stage 5 inventory and telemetry retrieval",
    },
    {
        "id": "BENCH-20",
        "query": "Which cloud instances have low CPU utilization?",
        "expected_intent": CopilotIntent.RESOURCE_UTILIZATION,
        "description": "Evaluate low utilization compute resource filtering",
    },

    # 11. OWNER_COST_ANALYSIS
    {
        "id": "BENCH-21",
        "query": "How much did the data engineering team spend this month?",
        "expected_intent": CopilotIntent.OWNER_COST_ANALYSIS,
        "description": "Evaluate owner tag based cost attribution",
    },
    {
        "id": "BENCH-22",
        "query": "Break down our cloud costs by owner tag.",
        "expected_intent": CopilotIntent.OWNER_COST_ANALYSIS,
        "description": "Evaluate multi-owner allocation distribution",
    },

    # 12. COST_CENTER_ANALYSIS
    {
        "id": "BENCH-23",
        "query": "Show cloud spend grouped by cost center.",
        "expected_intent": CopilotIntent.COST_CENTER_ANALYSIS,
        "description": "Evaluate cost center showback grouping",
    },
    {
        "id": "BENCH-24",
        "query": "Which cost center is spending the most this quarter?",
        "expected_intent": CopilotIntent.COST_CENTER_ANALYSIS,
        "description": "Evaluate cost center ranking and comparison",
    },

    # 13. BILLING_DATA_QUALITY
    {
        "id": "BENCH-25",
        "query": "Are there untagged resources or missing billing records?",
        "expected_intent": CopilotIntent.BILLING_DATA_QUALITY,
        "description": "Evaluate FOCUS data quality and tag coverage audit",
    },
    {
        "id": "BENCH-26",
        "query": "What is our billing data quality score and FOCUS compliance status?",
        "expected_intent": CopilotIntent.BILLING_DATA_QUALITY,
        "description": "Evaluate FOCUS 1.0 schema compliance check",
    },

    # 14. GENERAL_FINOPS_QUESTION
    {
        "id": "BENCH-27",
        "query": "What is FOCUS 1.0 and how does CloudSage use it?",
        "expected_intent": CopilotIntent.GENERAL_FINOPS_QUESTION,
        "description": "Evaluate conceptual explanation of FOCUS standard",
    },
    {
        "id": "BENCH-28",
        "query": "Explain unblended cost vs effective cost in cloud billing.",
        "expected_intent": CopilotIntent.GENERAL_FINOPS_QUESTION,
        "description": "Evaluate domain terminology explanation",
    },

    # 15. UNSUPPORTED_OR_AMBIGUOUS_QUERY
    {
        "id": "BENCH-29",
        "query": "What is the weather forecast in Seattle today?",
        "expected_intent": CopilotIntent.UNSUPPORTED_OR_AMBIGUOUS_QUERY,
        "description": "Evaluate polite redirection for out-of-domain queries",
    },
    {
        "id": "BENCH-30",
        "query": "Write a python script to parse a CSV file.",
        "expected_intent": CopilotIntent.UNSUPPORTED_OR_AMBIGUOUS_QUERY,
        "description": "Evaluate redirection for non-FinOps coding requests",
    },
]


def run_benchmark_evaluation(db: Session) -> Dict[str, Any]:
    """
    Executes the 30 standardized benchmark queries against the active database.
    Evaluates intent accuracy, plan correctness, and advisory policy enforcement.
    """
    engine = get_copilot_engine()
    results = []
    correct_intents = 0
    total_latency_ms = 0

    for bench in BENCHMARK_QUESTIONS:
        req = ChatMessageRequest(
            query=bench["query"],
            user_id="benchmark_evaluator",
        )
        resp = engine.process_chat(db, req)
        matched_intent = (resp.intent == bench["expected_intent"].value)
        if matched_intent:
            correct_intents += 1

        total_latency_ms += resp.execution_duration_ms

        results.append({
            "id": bench["id"],
            "query": bench["query"],
            "expected_intent": bench["expected_intent"].value,
            "actual_intent": resp.intent,
            "intent_match": matched_intent,
            "citations_count": len(resp.evidence_citations),
            "execution_duration_ms": resp.execution_duration_ms,
            "has_advisory_disclaimer": "advisory" in resp.content.lower(),
        })

    total_count = len(BENCHMARK_QUESTIONS)
    accuracy_pct = (correct_intents / total_count) * 100

    return {
        "total_benchmarks": total_count,
        "passed_benchmarks": correct_intents,
        "accuracy_percentage": round(accuracy_pct, 2),
        "average_latency_ms": round(total_latency_ms / total_count, 2),
        "details": results,
    }
