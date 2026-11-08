"""
CloudSage AI FinOps Copilot REST API Endpoints.
Provides 10 enterprise endpoints for conversational FinOps inquiries,
multi-turn conversation management, explainability, feedback, and telemetry.
"""

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_sync_db
from backend.app.copilot.conversation import ConversationManager
from backend.app.copilot.engine import get_copilot_engine
from backend.app.copilot.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
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
)

router = APIRouter(prefix="/copilot", tags=["AI FinOps Copilot"])


@router.post("/chat", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK)
def copilot_chat(
    payload: ChatMessageRequest,
    db: Session = Depends(get_sync_db),
):
    """
    Submits a natural language FinOps question to the Copilot.
    Validates guardrails, classifies intent, plans analytical query, retrieves database evidence,
    and synthesizes a grounded response citing exact metrics.
    """
    engine = get_copilot_engine()
    return engine.process_chat(db, payload)


@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(
    user_id: Optional[str] = Query(None, description="Optional user filter"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
):
    """Lists saved Copilot conversation threads."""
    convs = ConversationManager.list_conversations(db, user_id=user_id, limit=limit, offset=offset)
    return [
        ConversationResponse(
            id=c.id,
            user_id=c.user_id,
            title=c.title,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=len(c.messages) if c.messages else 0,
        )
        for c in convs
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation_detail(
    conversation_id: uuid.UUID,
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_sync_db),
):
    """Retrieves full conversation history and message turns."""
    conv = ConversationManager.get_conversation(db, conversation_id, user_id=user_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    messages = [
        CopilotMessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            intent=m.intent,
            query_plan=m.query_plan,
            evidence_citations=m.evidence_citations or [],
            tokens_used=m.tokens_used,
            execution_duration_ms=m.execution_duration_ms,
            model_name=m.model_name,
            provider=m.provider,
            created_at=m.created_at,
        )
        for m in conv.messages
    ]

    return ConversationDetailResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages,
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_200_OK)
def delete_conversation(
    conversation_id: uuid.UUID,
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_sync_db),
):
    """Deletes a Copilot conversation thread."""
    deleted = ConversationManager.delete_conversation(db, conversation_id, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )
    return {"status": "success", "message": f"Conversation '{conversation_id}' deleted."}


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageResponse)
def send_conversation_message(
    conversation_id: uuid.UUID,
    payload: ChatMessageRequest,
    db: Session = Depends(get_sync_db),
):
    """Appends a new turn to an existing conversation thread."""
    payload.conversation_id = conversation_id
    engine = get_copilot_engine()
    return engine.process_chat(db, payload)


@router.get("/capabilities", response_model=CopilotCapabilitiesResponse)
def get_capabilities():
    """Retrieves operational capabilities, supported intents, and guardrail policies."""
    engine = get_copilot_engine()
    return engine.get_capabilities()


@router.get("/health", response_model=CopilotHealthResponse)
def get_health(db: Session = Depends(get_sync_db)):
    """Health check endpoint for Copilot backend and underlying providers."""
    engine = get_copilot_engine()
    return engine.get_health(db)


@router.get("/usage", response_model=CopilotUsageStats)
def get_usage(db: Session = Depends(get_sync_db)):
    """Retrieves token usage, execution latency, and intent distribution telemetry."""
    engine = get_copilot_engine()
    return engine.get_usage_stats(db)


@router.post("/feedback", response_model=CopilotFeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: CopilotFeedbackRequest,
    db: Session = Depends(get_sync_db),
):
    """Records user satisfaction rating and feedback on a Copilot message."""
    fb = ConversationManager.record_feedback(
        db=db,
        message_id=payload.message_id,
        rating=payload.rating,
        feedback_text=payload.feedback_text,
        user_id=payload.user_id,
    )
    return CopilotFeedbackResponse(
        id=fb.id,
        message_id=fb.message_id,
        rating=fb.rating,
        feedback_text=fb.feedback_text,
        created_at=fb.created_at,
    )


@router.post("/explain", response_model=CopilotExplainResponse, status_code=status.HTTP_200_OK)
def explain_finding(
    payload: CopilotExplainRequest,
    db: Session = Depends(get_sync_db),
):
    """
    Produces detailed FinOps technical and business explainability analysis
    for a specific cost anomaly, waste detection, recommendation, or billing entity.
    """
    engine = get_copilot_engine()
    return engine.explain_entity(db, payload)

