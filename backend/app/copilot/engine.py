"""
Central AI FinOps Copilot Engine for CloudSage.
Orchestrates the complete 8-step pipeline:
1. Security & Advisory Guardrails
2. Intent Classification & Entity Extraction
3. Contextual Conversation Memory Resolution
4. Safe Analytical Query Planning
5. Read-Only Cross-Stage Data Retrieval (Zero Float Rule)
6. Structured Evidence Citation Generation
7. LLM Prompt Synthesis (Provider or Deterministic Fallback)
8. Output Sanitization, Message Persistence & Operational Audit Logging
"""

from datetime import datetime, timezone
from decimal import Decimal
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.enums import CloudProvider, CopilotIntent, MessageRole
from backend.app.copilot.citations import CitationBuilder
from backend.app.copilot.conversation import ConversationManager
from backend.app.copilot.data_retrieval import DataRetrievalEngine
from backend.app.copilot.guardrails import CopilotGuardrails
from backend.app.copilot.intent import IntentClassifier
from backend.app.copilot.llm_provider import get_llm_provider
from backend.app.copilot.prompts import COPILOT_SYSTEM_PROMPT, EXPLAIN_SYSTEM_PROMPT
from backend.app.copilot.query_planner import QueryPlanner
from backend.app.copilot.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    CopilotCapabilitiesResponse,
    CopilotExplainRequest,
    CopilotExplainResponse,
    CopilotHealthResponse,
    CopilotUsageStats,
    EvidenceCitationSchema,
)
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord
from backend.app.models.copilot import (
    CopilotConversation,
    CopilotMessage,
    CopilotUsageLog,
)
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection

logger = logging.getLogger(__name__)


class CopilotEngine:
    """Enterprise-grade multi-cloud FinOps Copilot orchestration engine."""

    def __init__(self):
        self.guardrails = CopilotGuardrails()
        self.classifier = IntentClassifier()
        self.planner = QueryPlanner()
        self.retrieval = DataRetrievalEngine()
        self.citation_builder = CitationBuilder()
        self.conversation_mgr = ConversationManager()

    def process_chat(self, db: Session, request: ChatMessageRequest) -> ChatMessageResponse:
        """Executes full end-to-end FinOps Copilot conversational turn."""
        start_time = time.time()

        # Step 1: Guardrail Validation
        is_safe, error_category, explanation = self.guardrails.validate_query(request.query)
        if not is_safe:
            # Handle violation safely without external API call or analytical execution
            conv = self.conversation_mgr.get_or_create_conversation(
                db, request.conversation_id, request.user_id
            )
            # Save user prompt
            self.conversation_mgr.save_message(
                db=db,
                conversation_id=conv.id,
                role=MessageRole.USER,
                content=request.query,
                intent="GUARDRAIL_VIOLATION",
            )
            # Save assistant refusal
            duration_ms = int((time.time() - start_time) * 1000)
            ast_msg = self.conversation_mgr.save_message(
                db=db,
                conversation_id=conv.id,
                role=MessageRole.ASSISTANT,
                content=explanation or "Query cannot be processed due to safety guardrails.",
                intent="GUARDRAIL_VIOLATION",
                execution_duration_ms=duration_ms,
                model_name="copilot-guardrails",
                provider="internal",
            )
            self.conversation_mgr.record_usage(
                db=db,
                model_name="copilot-guardrails",
                provider="internal",
                prompt_tokens=len(request.query.split()),
                completion_tokens=len(ast_msg.content.split()),
                execution_duration_ms=duration_ms,
                user_id=request.user_id,
                conversation_id=str(conv.id),
                status=f"blocked_{error_category}",
            )
            return ChatMessageResponse(
                conversation_id=conv.id,
                message_id=ast_msg.id,
                role=MessageRole.ASSISTANT,
                content=ast_msg.content,
                intent="GUARDRAIL_VIOLATION",
                query_plan=None,
                evidence_citations=[],
                tokens_used=0,
                execution_duration_ms=duration_ms,
                model_name="copilot-guardrails",
                provider="internal",
                created_at=ast_msg.created_at,
            )

        # Step 2 & 3: Intent Classification & Entity Extraction
        intent = self.classifier.classify(request.query)
        raw_entities = self.classifier.extract_entities(request.query)

        # Step 4: Conversation Session Retrieval/Creation
        conv = self.conversation_mgr.get_or_create_conversation(
            db, request.conversation_id, request.user_id
        )

        # Save user message
        self.conversation_mgr.save_message(
            db=db,
            conversation_id=conv.id,
            role=MessageRole.USER,
            content=request.query,
            intent=intent.value,
        )

        # Step 5: Multi-Turn Context Resolution (Entity carry-over)
        entities = self.conversation_mgr.resolve_follow_up_context(
            db, conv.id, raw_entities
        )

        # Step 6: Safe Analytical Query Planning
        plan = self.planner.plan(intent, entities)

        # Step 7: Safe Read-Only Data Retrieval (Zero Float Rule)
        retrieval_results = self.retrieval.execute(db, plan)

        # Step 8: Structured Evidence Citation Generation
        citations = self.citation_builder.build_citations(
            target_dataset=plan.target_dataset,
            sample_records=retrieval_results.get("sample_records", []),
        )

        # Step 9: LLM Prompt Synthesis
        llm = get_llm_provider(model_override=request.model)
        context_payload = {
            "total_metric": retrieval_results.get("total_metric", Decimal("0.0000")),
            "record_count": retrieval_results.get("record_count", 0),
            "breakdown": retrieval_results.get("breakdown", []),
            "entities": entities,
        }

        generated_text, p_tokens, c_tokens = llm.generate(
            system_prompt=COPILOT_SYSTEM_PROMPT,
            user_prompt=request.query,
            context=context_payload,
            intent=intent,
            citations=citations,
        )

        # Step 10: Output Sanitization & Advisory Disclaimer Enforcement
        sanitized_text = self.guardrails.sanitize_output(generated_text)
        final_text = self.guardrails.enforce_advisory_disclaimer(sanitized_text)

        # Step 11: Save Assistant Turn
        duration_ms = int((time.time() - start_time) * 1000)
        total_tokens = p_tokens + c_tokens
        model_name = request.model or settings.COPILOT_MODEL_NAME
        provider_name = settings.COPILOT_PROVIDER if settings.COPILOT_API_KEY else "deterministic-fallback"

        serialized_entities = {
            k: (v.isoformat() if isinstance(v, datetime) else str(v) if isinstance(v, Decimal) else v)
            for k, v in entities.items()
        }

        ast_msg = self.conversation_mgr.save_message(
            db=db,
            conversation_id=conv.id,
            role=MessageRole.ASSISTANT,
            content=final_text,
            intent=intent.value,
            query_plan=plan.to_schema().model_dump(),
            evidence_citations=[c.model_dump() for c in citations],
            tokens_used=total_tokens,
            execution_duration_ms=duration_ms,
            model_name=model_name,
            provider=provider_name,
            raw_metadata={"entities": serialized_entities},
        )

        # Step 12: Record Operational Metrics
        self.conversation_mgr.record_usage(
            db=db,
            model_name=model_name,
            provider=provider_name,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            execution_duration_ms=duration_ms,
            user_id=request.user_id,
            conversation_id=str(conv.id),
            status="success",
        )

        # Step 13: Return Structured Chat Response
        return ChatMessageResponse(
            conversation_id=conv.id,
            message_id=ast_msg.id,
            role=MessageRole.ASSISTANT,
            content=final_text,
            intent=intent.value,
            query_plan=plan.to_schema(),
            evidence_citations=citations,
            tokens_used=total_tokens,
            execution_duration_ms=duration_ms,
            model_name=model_name,
            provider=provider_name,
            created_at=ast_msg.created_at,
        )

    def explain_entity(self, db: Session, request: CopilotExplainRequest) -> CopilotExplainResponse:
        """Generates detailed FinOps explainability analysis for a specific finding."""
        t_type = request.target_type.lower()
        t_id = request.target_id.strip()

        citations: List[EvidenceCitationSchema] = []
        financial_impact: Dict[str, Any] = {}
        title = f"Explanation of {t_type.capitalize()} {t_id}"
        explanation_lines = []
        advisory_rec = None

        if t_type == "anomaly":
            try:
                target_uuid = uuid.UUID(t_id)
                anomaly = db.execute(
                    select(CostAnomaly).where(CostAnomaly.id == target_uuid)
                ).scalar_one_or_none()
            except Exception:
                anomaly = None

            if anomaly:
                title = f"Cost Anomaly on {anomaly.provider} {anomaly.service_name} ({anomaly.anomaly_category})"
                excess = Decimal(str(anomaly.estimated_excess_cost)).quantize(Decimal("0.0001"))
                financial_impact = {
                    "estimated_excess_cost": str(excess),
                    "currency": "USD",
                    "severity": str(anomaly.severity),
                    "status": str(anomaly.status),
                }
                explanation_lines.append(f"### Root Cause Analysis")
                explanation_lines.append(
                    f"A **{anomaly.severity}** cost anomaly was detected on **{anomaly.provider} {anomaly.service_name}** "
                    f"under category **{anomaly.anomaly_category}**. Estimated unexpected expenditure is **${excess:,.4f} USD**."
                )
                explanation_lines.append(f"The spending deviated significantly from baseline expectations.")
                advisory_rec = (
                    f"Verify whether the spending jump on {anomaly.service_name} correlates with a scheduled deployment "
                    f"or campaign. If unintended, inspect provisioned capacity and set up budget threshold alerts."
                )
                citations.append(
                    EvidenceCitationSchema(
                        source_table="cost_anomalies",
                        record_id=str(anomaly.id),
                        description=f"Stage 7 Anomaly: {anomaly.provider} {anomaly.service_name} ({anomaly.anomaly_category})",
                        metric_value=f"${excess} excess",
                        confidence=0.98,
                    )
                )
            else:
                explanation_lines.append(f"No cost anomaly record found matching identifier '{t_id}'.")

        elif t_type == "waste":
            try:
                target_uuid = uuid.UUID(t_id)
                waste = db.execute(
                    select(WasteDetection).where(WasteDetection.id == target_uuid)
                ).scalar_one_or_none()
            except Exception:
                waste = None

            if waste:
                title = f"Cloud Waste Detection: {waste.provider} {waste.waste_type} ({waste.resource_id})"
                monthly = Decimal(str(waste.estimated_monthly_waste)).quantize(Decimal("0.0001"))
                annual = (monthly * 12).quantize(Decimal("0.0001"))
                financial_impact = {
                    "estimated_monthly_waste": str(monthly),
                    "estimated_annual_waste": str(annual),
                    "currency": "USD",
                    "severity": str(waste.severity),
                }
                explanation_lines.append(f"### Waste Analysis")
                explanation_lines.append(
                    f"CloudSage Stage 6 detected **{waste.waste_type}** on resource `{waste.resource_id}` "
                    f"in **{waste.provider}**. Incurring an estimated waste of **${monthly:,.4f} USD/mo** "
                    f"(**${annual:,.4f} USD/yr**)."
                )
                advisory_rec = (
                    f"Evaluate if resource `{waste.resource_id}` is still in active use. "
                    f"For unattached storage or orphaned snapshots, consider archiving or deleting via cloud console."
                )
                citations.append(
                    EvidenceCitationSchema(
                        source_table="waste_detections",
                        record_id=str(waste.id),
                        description=f"Stage 6 Waste: {waste.provider} {waste.waste_type} (Resource: {waste.resource_id})",
                        metric_value=f"${monthly}/month waste",
                        confidence=1.0,
                    )
                )
            else:
                explanation_lines.append(f"No waste detection record found matching identifier '{t_id}'.")

        elif t_type == "recommendation":
            try:
                target_uuid = uuid.UUID(t_id)
                rec = db.execute(
                    select(Recommendation).where(Recommendation.id == target_uuid)
                ).scalar_one_or_none()
            except Exception:
                rec = None

            if rec:
                title = f"Advisory Recommendation: [{rec.priority}] {rec.title}"
                monthly = Decimal(str(rec.estimated_monthly_savings)).quantize(Decimal("0.0001"))
                annual = Decimal(str(rec.estimated_annual_savings)).quantize(Decimal("0.0001"))
                financial_impact = {
                    "estimated_monthly_savings": str(monthly),
                    "estimated_annual_savings": str(annual),
                    "currency": rec.currency,
                    "priority": str(rec.priority),
                    "status": str(rec.status),
                }
                explanation_lines.append(f"### Advisory Recommendation Breakdown")
                explanation_lines.append(
                    f"Optimization strategy **{rec.strategy_id}** on **{rec.provider}** suggests: "
                    f"**{rec.description}**."
                )
                explanation_lines.append(
                    f"Potential savings: **${monthly:,.4f} USD/month** (**${annual:,.4f} USD/year**). "
                    f"Assigned priority: **{rec.priority}**."
                )
                advisory_rec = (
                    f"Review implementation guidance in CloudSage Recommendation Center. "
                    f"CloudSage does not execute cloud mutations automatically; review with system administrators."
                )
                citations.append(
                    EvidenceCitationSchema(
                        source_table="recommendations",
                        record_id=str(rec.id),
                        description=f"Stage 8 Recommendation: {rec.title} ({rec.strategy_id})",
                        metric_value=f"${monthly}/month savings",
                        confidence=1.0,
                    )
                )
            else:
                explanation_lines.append(f"No recommendation record found matching identifier '{t_id}'.")

        else:
            explanation_lines.append(f"Entity type '{t_type}' explanation is not currently supported.")

        return CopilotExplainResponse(
            target_type=t_type,
            target_id=t_id,
            title=title,
            explanation="\n".join(explanation_lines),
            evidence_citations=citations,
            financial_impact=financial_impact,
            advisory_recommendation=advisory_rec,
        )

    def get_capabilities(self) -> CopilotCapabilitiesResponse:
        """Returns the capabilities and supported configurations of the Copilot."""
        return CopilotCapabilitiesResponse(
            supported_intents=[intent.value for intent in CopilotIntent],
            supported_providers=[p.value for p in CloudProvider],
            supported_aggregations=["SUM", "COUNT", "AVG", "MIN", "MAX"],
            guardrails_enabled=True,
            advisory_mode=True,
            active_model=settings.COPILOT_MODEL_NAME,
            active_provider=settings.COPILOT_PROVIDER if settings.COPILOT_API_KEY else "deterministic-fallback",
        )

    def get_health(self, db: Session) -> CopilotHealthResponse:
        """Performs Copilot service health checks."""
        db_healthy = True
        try:
            db.execute(select(1)).one()
        except Exception:
            db_healthy = False

        provider_status = "active_live" if settings.COPILOT_API_KEY else "active_deterministic_fallback"

        return CopilotHealthResponse(
            status="healthy" if db_healthy else "degraded",
            database_connected=db_healthy,
            provider_status=provider_status,
            active_model=settings.COPILOT_MODEL_NAME,
            timestamp=datetime.now(timezone.utc),
        )

    def get_usage_stats(self, db: Session) -> CopilotUsageStats:
        """Aggregates Copilot usage metrics and token telemetry."""
        total_queries = db.execute(select(func.count(CopilotUsageLog.id))).scalar() or 0
        total_tokens = db.execute(select(func.coalesce(func.sum(CopilotUsageLog.total_tokens), 0))).scalar() or 0
        avg_latency = float(db.execute(select(func.coalesce(func.avg(CopilotUsageLog.execution_duration_ms), 0.0))).scalar() or 0.0)

        # Provider breakdown
        p_stmt = select(CopilotUsageLog.provider, func.count(CopilotUsageLog.id)).group_by(CopilotUsageLog.provider)
        prov_dict = {str(p): int(cnt) for p, cnt in db.execute(p_stmt).all()}

        # Intent breakdown
        i_stmt = select(CopilotMessage.intent, func.count(CopilotMessage.id)).where(CopilotMessage.intent.isnot(None)).group_by(CopilotMessage.intent)
        intent_dict = {str(i): int(cnt) for i, cnt in db.execute(i_stmt).all()}

        return CopilotUsageStats(
            total_queries=int(total_queries),
            total_tokens=int(total_tokens),
            average_latency_ms=round(avg_latency, 2),
            provider_breakdown=prov_dict,
            intent_breakdown=intent_dict,
        )


_copilot_engine_instance: Optional[CopilotEngine] = None


def get_copilot_engine() -> CopilotEngine:
    """Returns the singleton CopilotEngine instance."""
    global _copilot_engine_instance
    if _copilot_engine_instance is None:
        _copilot_engine_instance = CopilotEngine()
    return _copilot_engine_instance
