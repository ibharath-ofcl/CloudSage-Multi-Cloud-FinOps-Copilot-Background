"""
CloudSage AI FinOps Copilot Package.
Exports CopilotEngine, Benchmark suite, schemas, and intent classifier.
"""

from backend.app.copilot.benchmarks import BENCHMARK_QUESTIONS, run_benchmark_evaluation
from backend.app.copilot.conversation import ConversationManager
from backend.app.copilot.data_retrieval import DataRetrievalEngine
from backend.app.copilot.engine import CopilotEngine, get_copilot_engine
from backend.app.copilot.guardrails import CopilotGuardrails
from backend.app.copilot.intent import IntentClassifier
from backend.app.copilot.llm_provider import (
    BaseLLMProvider,
    DeterministicFallbackProvider,
    OpenAICompatibleProvider,
    get_llm_provider,
)
from backend.app.copilot.query_planner import QueryPlan, QueryPlanner
from backend.app.copilot.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    CopilotCapabilitiesResponse,
    CopilotExplainRequest,
    CopilotExplainResponse,
    CopilotFeedbackRequest,
    CopilotFeedbackResponse,
    CopilotHealthResponse,
    CopilotMessageResponse,
    CopilotUsageStats,
    EvidenceCitationSchema,
    QueryPlanSchema,
)

__all__ = [
    "CopilotEngine",
    "get_copilot_engine",
    "ConversationManager",
    "DataRetrievalEngine",
    "QueryPlanner",
    "QueryPlan",
    "IntentClassifier",
    "CopilotGuardrails",
    "BaseLLMProvider",
    "DeterministicFallbackProvider",
    "OpenAICompatibleProvider",
    "get_llm_provider",
    "BENCHMARK_QUESTIONS",
    "run_benchmark_evaluation",
    "ChatMessageRequest",
    "ChatMessageResponse",
    "ConversationCreate",
    "ConversationResponse",
    "ConversationDetailResponse",
    "CopilotMessageResponse",
    "CopilotFeedbackRequest",
    "CopilotFeedbackResponse",
    "CopilotUsageStats",
    "CopilotCapabilitiesResponse",
    "CopilotHealthResponse",
    "CopilotExplainRequest",
    "CopilotExplainResponse",
    "EvidenceCitationSchema",
    "QueryPlanSchema",
]
