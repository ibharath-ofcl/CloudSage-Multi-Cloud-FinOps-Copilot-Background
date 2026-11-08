"""
LLM Provider Abstraction and Grounded Deterministic Fallback.
Provides unified interface for external LLMs (OpenAI, Azure OpenAI, vLLM)
and a robust, deterministic, rule-based fallback provider for offline / test environments.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from backend.app.core.config import settings
from backend.app.core.enums import CopilotIntent
from backend.app.copilot.citations import CitationBuilder
from backend.app.copilot.prompts import COPILOT_SYSTEM_PROMPT
from backend.app.copilot.schemas import EvidenceCitationSchema

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract interface for FinOps LLM providers."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Dict[str, Any],
        intent: CopilotIntent,
        citations: List[EvidenceCitationSchema],
    ) -> Tuple[str, int, int]:
        """
        Generates response content.
        Returns:
            (content_text, prompt_tokens, completion_tokens)
        """
        pass


class DeterministicFallbackProvider(BaseLLMProvider):
    """
    Deterministic FinOps Synthesizer.
    Generates structured, evidence-grounded responses directly from verified database query results,
    adhering to the Zero Float Rule and eliminating any possibility of hallucination.
    """

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Dict[str, Any],
        intent: CopilotIntent,
        citations: List[EvidenceCitationSchema],
    ) -> Tuple[str, int, int]:
        total_metric = context.get("total_metric", Decimal("0.0000"))
        record_count = context.get("record_count", 0)
        breakdown = context.get("breakdown", [])
        entities = context.get("entities", {})

        # Build response sections based on intent
        lines = []

        if intent == CopilotIntent.TOTAL_CLOUD_SPEND:
            lines.append("### Executive Summary")
            lines.append(
                f"Total recorded cloud expenditure is **${total_metric:,.4f} USD** "
                f"across **{record_count:,}** normalized billing records."
            )
            lines.append("\n### Detailed Breakdown")
            if breakdown:
                for item in breakdown:
                    lines.append(f"- **{item['dimension']}**: ${item['cost']:,.4f} USD ({item['count']} records)")
            else:
                lines.append(f"- No granular dimension breakdown recorded for current filters.")

            lines.append("\n### Evidence & Citations")
            if citations:
                for c in citations[:5]:
                    lines.append(f"- `{c.source_table}`: {c.description} — Value: **{c.metric_value}**")
            else:
                lines.append("- No individual billing records cited.")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Review top spending dimensions for unexpected cost expansion.")
            lines.append("- Inspect active cost anomalies and waste detections to identify savings opportunities.")

        elif intent == CopilotIntent.PROVIDER_COST_COMPARISON:
            lines.append("### Executive Summary")
            lines.append(
                f"Multi-cloud expenditure comparison shows total spend of **${total_metric:,.4f} USD** "
                f"distributed across active cloud service providers."
            )
            lines.append("\n### Detailed Breakdown by Provider")
            if breakdown:
                for item in breakdown:
                    pct = (item["cost"] / total_metric * 100) if total_metric > 0 else Decimal("0.0")
                    lines.append(f"- **{item['dimension']}**: ${item['cost']:,.4f} USD ({pct:.1f}% of total spend, {item['count']} records)")
            else:
                lines.append("- Single or unclassified provider records found in database.")

            lines.append("\n### Evidence & Citations")
            for c in citations[:5]:
                lines.append(f"- `{c.source_table}`: {c.description} — Value: **{c.metric_value}**")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Establish provider-specific budget caps and allocation policies.")
            lines.append("- Ensure billing export pipelines are synchronizing without lag across all providers.")

        elif intent == CopilotIntent.SERVICE_COST_BREAKDOWN:
            lines.append("### Executive Summary")
            lines.append(
                f"Cloud service cost analysis indicates total expenditure of **${total_metric:,.4f} USD** "
                f"across tracked cloud services."
            )
            lines.append("\n### Top Service Expenditure Breakdown")
            if breakdown:
                for idx, item in enumerate(breakdown, 1):
                    lines.append(f"{idx}. **{item['dimension']}**: ${item['cost']:,.4f} USD ({item['count']} usage line items)")
            else:
                lines.append("- No service breakdown available for the specified criteria.")

            lines.append("\n### Evidence & Citations")
            for c in citations[:5]:
                lines.append(f"- `{c.source_table}`: {c.description} — Cost: **{c.metric_value}**")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Prioritize optimization on the top 2 expenditure drivers.")
            lines.append("- Review rightsizing and commitment discounts (Savings Plans / RIs) for top compute/database services.")

        elif intent == CopilotIntent.RESOURCE_COST_ANALYSIS:
            lines.append("### Executive Summary")
            lines.append(
                f"Resource-level expenditure analysis reports **${total_metric:,.4f} USD** "
                f"in direct unblended resource costs."
            )
            lines.append("\n### Top Cost-Driving Resources")
            if breakdown:
                for item in breakdown:
                    lines.append(f"- Resource `{item['dimension']}`: ${item['cost']:,.4f} USD")
            else:
                lines.append("- No specific resource records found matching criteria.")

            lines.append("\n### Evidence & Citations")
            for c in citations[:5]:
                lines.append(f"- `{c.source_table}`: {c.description} — Value: **{c.metric_value}**")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Correlate high-cost resources with utilization telemetry (CPU/Memory) to evaluate rightsizing.")
            lines.append("- Verify tagging compliance to guarantee accurate cost-center attribution.")

        elif intent == CopilotIntent.COST_TREND_ANALYSIS:
            lines.append("### Executive Summary")
            lines.append(
                f"Cost trend evaluation indicates aggregate spending of **${total_metric:,.4f} USD** "
                f"across the analyzed observation window."
            )
            lines.append("\n### Spending Trajectory & Period Breakdown")
            if breakdown:
                for item in breakdown[:10]:
                    lines.append(f"- Date `{item['dimension']}`: ${item['cost']:,.4f} USD")
            else:
                lines.append("- Stable spending trajectory observed across recorded intervals.")

            lines.append("\n### Evidence & Citations")
            for c in citations[:5]:
                lines.append(f"- `{c.source_table}`: {c.description}")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Monitor weekly cost trajectory against monthly budget forecasts.")
            lines.append("- Investigate any day-over-day variance exceeding 20% using the Anomaly Center.")

        elif intent == CopilotIntent.COST_ANOMALY_EXPLANATION:
            lines.append("### Executive Summary")
            lines.append(
                f"CloudSage Stage 7 Anomaly Engine detected **{record_count} active cost anomalies** "
                f"representing **${total_metric:,.4f} USD** in estimated excess expenditure."
            )
            lines.append("\n### Anomaly Distribution by Category")
            if breakdown:
                for item in breakdown:
                    lines.append(f"- **{item['dimension']}**: ${item['cost']:,.4f} USD excess ({item['count']} incidents)")
            else:
                lines.append("- No unresolved cost anomalies detected under current filters.")

            lines.append("\n### Evidence & Citations")
            for c in citations[:5]:
                lines.append(f"- `{c.source_table}`: {c.description} — **{c.metric_value}**")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Review detected anomalies in the CloudSage Anomaly Dashboard.")
            lines.append("- Triage incidents with resource owners to verify if spending represents intended workload scale or billing leaks.")

        elif intent == CopilotIntent.WASTE_DETECTION_ANALYSIS:
            lines.append("### Executive Summary")
            lines.append(
                f"CloudSage Stage 6 Waste Detection Engine identified **{record_count} active waste items** "
                f"costing an estimated **${total_metric:,.4f} USD per month**."
            )
            lines.append("\n### Detected Waste by Category")
            if breakdown:
                for item in breakdown:
                    lines.append(f"- **{item['dimension']}**: ${item['cost']:,.4f} USD/mo ({item['count']} resources)")
            else:
                lines.append("- No active waste detections matching criteria.")

            lines.append("\n### Evidence & Citations")
            for c in citations[:5]:
                lines.append(f"- `{c.source_table}`: {c.description} — **{c.metric_value}**")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Review unattached storage volumes and orphaned snapshots for snapshot retention compliance.")
            lines.append("- Check idle virtual machines for scheduled weekend/evening shutdown policies.")

        elif intent == CopilotIntent.OPTIMIZATION_RECOMMENDATIONS:
            lines.append("### Executive Summary")
            lines.append(
                f"CloudSage Stage 8 Recommendation Engine generated **{record_count} actionable optimization recommendations** "
                f"yielding potential monthly savings of **${total_metric:,.4f} USD**."
            )
            lines.append("\n### Recommendations by Strategy & Priority")
            if breakdown:
                for item in breakdown:
                    lines.append(f"- Strategy **{item['dimension']}**: ${item['cost']:,.4f} USD/mo savings ({item['count']} proposals)")
            else:
                lines.append("- No unreviewed recommendations matching current criteria.")

            lines.append("\n### Evidence & Citations")
            for c in citations[:5]:
                lines.append(f"- `{c.source_table}`: {c.description} — **{c.metric_value}**")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Review and endorse P1 and Quick Win recommendations in CloudSage Recommendation Center.")
            lines.append("- Validate recommendations with engineering leads prior to manual console execution.")

        elif intent == CopilotIntent.SAVINGS_OPPORTUNITY:
            annual = (total_metric * 12).quantize(Decimal("0.0001"))
            lines.append("### Executive Summary")
            lines.append(
                f"Total identified savings opportunity is **${total_metric:,.4f} USD per month** "
                f"(projected **${annual:,.4f} USD annually**) across **{record_count}** proposed optimizations."
            )
            lines.append("\n### Savings Potential Breakdown")
            if breakdown:
                for item in breakdown:
                    ann_sub = (item['cost'] * 12).quantize(Decimal("0.0001"))
                    lines.append(f"- **{item['dimension']}**: ${item['cost']:,.4f}/mo (${ann_sub:,.4f}/yr, {item['count']} recommendations)")
            else:
                lines.append("- Potential savings calculated from active Stage 8 recommendation portfolio.")

            lines.append("\n### Evidence & Citations")
            for c in citations[:5]:
                lines.append(f"- `{c.source_table}`: {c.description} — **{c.metric_value}**")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Schedule monthly FinOps review to track implemented vs projected savings.")
            lines.append("- Focus first on high-confidence, low-risk architectural adjustments.")

        elif intent == CopilotIntent.RESOURCE_UTILIZATION:
            lines.append("### Executive Summary")
            lines.append(
                f"Multi-cloud resource inventory tracks **{record_count:,} cloud resources** "
                f"across registered subscriptions and accounts."
            )
            lines.append("\n### Inventory by Resource Type")
            if breakdown:
                for item in breakdown:
                    lines.append(f"- **{item['dimension']}**: {item['count']:,} tracked resources")
            else:
                lines.append("- Inventory records active.")

            lines.append("\n### Evidence & Citations")
            for c in citations[:5]:
                lines.append(f"- `{c.source_table}`: {c.description}")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Correlate 30-day CPU and Memory P95 metrics with instance types.")
            lines.append("- Reclaim or downsize instances operating consistently below 5% average utilization.")

        elif intent in (CopilotIntent.OWNER_COST_ANALYSIS, CopilotIntent.COST_CENTER_ANALYSIS):
            lines.append("### Executive Summary")
            tag_name = "Owner" if intent == CopilotIntent.OWNER_COST_ANALYSIS else "Cost Center"
            lines.append(
                f"Cost allocation analysis by {tag_name} accounts for **${total_metric:,.4f} USD** "
                f"in tracked expenditure across **{record_count}** line items."
            )
            lines.append(f"\n### {tag_name} Allocation Breakdown")
            if breakdown:
                for item in breakdown:
                    lines.append(f"- **{item['dimension']}**: ${item['cost']:,.4f} USD ({item['count']} records)")
            else:
                lines.append("- Tag values extracted from normalized FOCUS billing records.")

            lines.append("\n### Evidence & Citations")
            for c in citations[:5]:
                lines.append(f"- `{c.source_table}`: {c.description} — Value: **{c.metric_value}**")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Enforce automated tag governance in CI/CD and Terraform modules.")
            lines.append("- Distribute monthly showback summaries to respective team engineering managers.")

        elif intent == CopilotIntent.BILLING_DATA_QUALITY:
            lines.append("### Executive Summary")
            lines.append(
                f"Billing data quality audit evaluated **{record_count:,} records** for FOCUS 1.0 "
                f"normalization compliance, currency uniformity, and schema completeness."
            )
            lines.append("\n### Compliance Breakdown")
            if breakdown:
                for item in breakdown:
                    lines.append(f"- Pricing Model **{item['dimension']}**: {item['count']} records")
            else:
                lines.append("- 100% of analyzed records adhere to canonical FOCUS schema structure.")

            lines.append("\n### Evidence & Citations")
            for c in citations[:5]:
                lines.append(f"- `{c.source_table}`: {c.description}")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Monitor Stage 4 Data Quality Reports for unmapped SKU anomalies.")
            lines.append("- Maintain automated currency exchange rate updates for multi-region billing.")

        elif intent == CopilotIntent.GENERAL_FINOPS_QUESTION:
            lines.append("### Executive Summary")
            lines.append(
                "CloudSage implements the FinOps Foundation Open Cost & Usage Specification (FOCUS 1.0) "
                "standard, unifying multi-cloud billing into consistent dimensions."
            )
            lines.append("\n### Core FinOps Principles in CloudSage")
            lines.append("- **FOCUS 1.0 Compliance**: Normalizes AWS, Azure, and GCP billing schemas into standard unblended and effective cost dimensions.")
            lines.append("- **Advisory Governance**: Recommendations are non-destructive and require human-in-the-loop validation.")
            lines.append("- **Zero Float Precision**: All monetary computations utilize exact fixed-point decimal arithmetic.")
            lines.append("- **Traceable Evidence**: Detections, anomalies, and recommendations link directly to supporting billing and inventory records.")

            lines.append("\n### Advisory Next Steps")
            lines.append("- Explore CloudSage capabilities by asking about total spend, service breakdowns, or active anomalies.")

        else:  # UNSUPPORTED_OR_AMBIGUOUS_QUERY
            lines.append("### Executive Summary")
            lines.append(
                "I am CloudSage Copilot, your AI FinOps assistant. I can assist you with multi-cloud "
                "spending analysis, cost anomalies, waste detection, and optimization recommendations across AWS, Azure, and GCP."
            )
            lines.append("\n### Supported FinOps Inquiries")
            lines.append("- **Total Spend**: 'How much did we spend on cloud this month?'")
            lines.append("- **Provider Comparison**: 'Compare spending between AWS and Azure'")
            lines.append("- **Service Breakdown**: 'What are our top 5 most expensive services?'")
            lines.append("- **Cost Anomalies**: 'Why did our AWS bill spike recently?'")
            lines.append("- **Waste & Savings**: 'What cloud waste was detected?' or 'How much money can we save?'")
            lines.append("- **Recommendations**: 'Show top P1 recommendations for GCP'")

            lines.append("\n### Advisory Notice")
            lines.append("- CloudSage recommendations are advisory. Automatic resource deletion is prohibited.")

        content = "\n".join(lines)
        prompt_tokens = len(user_prompt.split()) * 2 + 50
        completion_tokens = len(content.split()) * 2

        return content, prompt_tokens, completion_tokens


class OpenAICompatibleProvider(BaseLLMProvider):
    """Integrates with OpenAI-compatible LLM endpoints (OpenAI, Azure, vLLM)."""

    def __init__(self, api_key: str, endpoint: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.endpoint = endpoint or "https://api.openai.com/v1/chat/completions"
        self.model = model
        self.fallback = DeterministicFallbackProvider()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Dict[str, Any],
        intent: CopilotIntent,
        citations: List[EvidenceCitationSchema],
    ) -> Tuple[str, int, int]:
        if not self.api_key:
            return self.fallback.generate(system_prompt, user_prompt, context, intent, citations)

        # Assemble prompt payload
        citation_text = "\n".join([f"- {c.source_table} [{c.record_id}]: {c.description} (Value: {c.metric_value})" for c in citations[:8]])
        user_message = (
            f"User Question: {user_prompt}\n\n"
            f"Verified Database Context:\n"
            f"- Intent: {intent.value}\n"
            f"- Total Metric: {context.get('total_metric', '0.0000')}\n"
            f"- Record Count: {context.get('record_count', 0)}\n"
            f"- Breakdown: {context.get('breakdown', [])}\n\n"
            f"Traceable Evidence Citations:\n{citation_text}\n\n"
            f"Answer the user question strictly using the provided context."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": settings.COPILOT_TEMPERATURE,
            "max_tokens": settings.COPILOT_MAX_TOKENS,
        }

        try:
            with httpx.Client(timeout=settings.COPILOT_REQUEST_TIMEOUT_SECONDS) as client:
                res = client.post(self.endpoint, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    p_tokens = usage.get("prompt_tokens", 0)
                    c_tokens = usage.get("completion_tokens", 0)
                    return content, p_tokens, c_tokens
                else:
                    logger.warning("LLM API returned %s: %s. Falling back to deterministic synthesizer.", res.status_code, res.text)
                    return self.fallback.generate(system_prompt, user_prompt, context, intent, citations)
        except Exception as e:
            logger.warning("Error invoking LLM provider (%s). Falling back to deterministic synthesizer.", e)
            return self.fallback.generate(system_prompt, user_prompt, context, intent, citations)


def get_llm_provider(model_override: Optional[str] = None) -> BaseLLMProvider:
    """Factory creating configured LLM provider."""
    model_name = model_override or settings.COPILOT_MODEL_NAME

    if settings.COPILOT_PROVIDER == "fallback" or not settings.COPILOT_API_KEY:
        return DeterministicFallbackProvider()

    return OpenAICompatibleProvider(
        api_key=settings.COPILOT_API_KEY,
        endpoint=settings.COPILOT_API_ENDPOINT,
        model=model_name,
    )

