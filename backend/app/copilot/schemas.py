"""
Pydantic Schemas for CloudSage AI FinOps Copilot.
Validates chat requests, response payloads, conversations, query plans,
evidence citations, feedback, and analytical explainability endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import CopilotIntent, MessageRole


class EvidenceCitationSchema(BaseModel):
    """Traceable cross-stage database evidence citation."""
    model_config = ConfigDict(from_attributes=True)

    source_table: str = Field(..., description="Underlying database table or canonical model name")
    record_id: Optional[str] = Field(None, description="Primary key or identifier of the cited entity")
    description: str = Field(..., description="Human-readable summary of the factual evidence")
    metric_value: Optional[str] = Field(None, description="Exact financial or resource metric value cited")
    confidence: float = Field(default=1.0, description="Verification confidence score (0.0 to 1.0)")


class QueryPlanSchema(BaseModel):
    """Deterministic, allowlisted analytical query plan."""
    model_config = ConfigDict(from_attributes=True)

    intent: str = Field(..., description="FinOps intent for this query plan")
    target_dataset: str = Field(..., description="Target dataset/table (e.g. billing_records, recommendations)")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Safe parameterized filters")
    aggregations: List[str] = Field(default_factory=list, description="Allowlisted aggregation operations")
    group_by: List[str] = Field(default_factory=list, description="Allowlisted grouping fields")
    time_range: Dict[str, Any] = Field(default_factory=dict, description="Validated temporal boundaries")


class ChatMessageRequest(BaseModel):
    """User prompt to the AI FinOps Copilot."""
    query: str = Field(..., min_length=1, max_length=2000, description="User's natural language question")
    conversation_id: Optional[uuid.UUID] = Field(None, description="Optional existing conversation UUID to continue")
    user_id: Optional[str] = Field("default_user", description="Authenticated user or service identity")
    model: Optional[str] = Field(None, description="Optional model override")


class ChatMessageResponse(BaseModel):
    """Comprehensive grounded response from CloudSage Copilot."""
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    conversation_id: uuid.UUID
    message_id: uuid.UUID
    role: str = MessageRole.ASSISTANT
    content: str
    intent: str
    query_plan: Optional[QueryPlanSchema] = None
    evidence_citations: List[EvidenceCitationSchema] = Field(default_factory=list)
    tokens_used: int = 0
    execution_duration_ms: int = 0
    model_name: str
    provider: str
    advisory_disclaimer: str = (
        "CloudSage recommendations are strictly advisory. "
        "No automatic cloud resource modification or deletion is performed."
    )
    created_at: datetime


class ConversationCreate(BaseModel):
    """Request payload to initiate a new Copilot conversation session."""
    title: Optional[str] = Field("FinOps Analysis", max_length=255)
    user_id: Optional[str] = Field("default_user", max_length=100)


class ConversationResponse(BaseModel):
    """Summary of a Copilot conversation session."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[str]
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class CopilotMessageResponse(BaseModel):
    """Detail of a single chat turn in conversation history."""
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    intent: Optional[str] = None
    query_plan: Optional[Dict[str, Any]] = None
    evidence_citations: List[Dict[str, Any]] = Field(default_factory=list)
    tokens_used: int = 0
    execution_duration_ms: int = 0
    model_name: Optional[str] = None
    provider: Optional[str] = None
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    """Full detail of a conversation session including chronological message turns."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[str]
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[CopilotMessageResponse] = Field(default_factory=list)


class CopilotFeedbackRequest(BaseModel):
    """User feedback payload rating a Copilot response."""
    message_id: uuid.UUID
    rating: int = Field(..., ge=-1, le=1, description="1 for positive/thumbs up, -1 for negative/thumbs down")
    feedback_text: Optional[str] = Field(None, max_length=2000, description="Optional textual commentary")
    user_id: Optional[str] = Field(None, max_length=100)


class CopilotFeedbackResponse(BaseModel):
    """Confirmation of recorded user feedback."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message_id: uuid.UUID
    rating: int
    feedback_text: Optional[str] = None
    created_at: datetime


class CopilotUsageStats(BaseModel):
    """Usage and performance telemetry for the Copilot service."""
    total_queries: int = 0
    total_tokens: int = 0
    average_latency_ms: float = 0.0
    provider_breakdown: Dict[str, int] = Field(default_factory=dict)
    intent_breakdown: Dict[str, int] = Field(default_factory=dict)


class CopilotCapabilitiesResponse(BaseModel):
    """Operational capabilities and security configuration of the Copilot."""
    supported_intents: List[str]
    supported_providers: List[str]
    supported_aggregations: List[str]
    guardrails_enabled: bool = True
    advisory_mode: bool = True
    active_model: str
    active_provider: str


class CopilotHealthResponse(BaseModel):
    """Health check status of the Copilot system."""
    status: str
    database_connected: bool
    provider_status: str
    active_model: str
    timestamp: datetime


class CopilotExplainRequest(BaseModel):
    """Request to generate detailed AI explanation for a specific domain entity."""
    target_type: str = Field(..., description="Target entity type: 'anomaly', 'waste', 'recommendation', 'resource', or 'billing'")
    target_id: str = Field(..., description="UUID or identifier of the entity to explain")
    user_id: Optional[str] = Field("default_user", max_length=100)


class CopilotExplainResponse(BaseModel):
    """Structured AI explanation of a specific FinOps finding."""
    target_type: str
    target_id: str
    title: str
    explanation: str
    evidence_citations: List[EvidenceCitationSchema] = Field(default_factory=list)
    financial_impact: Dict[str, Any] = Field(default_factory=dict)
    advisory_recommendation: Optional[str] = None
    advisory_disclaimer: str = (
        "CloudSage recommendations are strictly advisory. "
        "No automatic cloud resource modification or deletion is performed."
    )
