"""
Conversation Session and Memory Manager for CloudSage AI FinOps Copilot.
Handles conversation lifecycle, chronological turn storage, feedback persistence,
and multi-turn analytical context resolution (entity carry-over).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app.core.enums import MessageRole
from backend.app.models.copilot import (
    CopilotConversation,
    CopilotFeedback,
    CopilotMessage,
    CopilotUsageLog,
)


class ConversationManager:
    """Manages Copilot conversations, message persistence, and contextual memory."""

    @classmethod
    def get_or_create_conversation(
        cls,
        db: Session,
        conversation_id: Optional[uuid.UUID] = None,
        user_id: Optional[str] = "default_user",
        title: Optional[str] = None,
    ) -> CopilotConversation:
        """Retrieves an existing conversation or initializes a new one."""
        if conversation_id:
            conv = db.execute(
                select(CopilotConversation).where(CopilotConversation.id == conversation_id)
            ).scalar_one_or_none()
            if conv:
                return conv

        new_conv = CopilotConversation(
            id=conversation_id or uuid.uuid4(),
            user_id=user_id,
            title=title or "FinOps Analysis",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)
        return new_conv

    @classmethod
    def get_conversation(
        cls,
        db: Session,
        conversation_id: uuid.UUID,
        user_id: Optional[str] = None,
    ) -> Optional[CopilotConversation]:
        """Retrieves a conversation by ID, optionally validating user_id."""
        stmt = select(CopilotConversation).where(CopilotConversation.id == conversation_id)
        if user_id:
            stmt = stmt.where(CopilotConversation.user_id == user_id)
        return db.execute(stmt).scalar_one_or_none()

    @classmethod
    def list_conversations(
        cls,
        db: Session,
        user_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[CopilotConversation]:
        """Lists conversations ordered by updated_at desc."""
        stmt = select(CopilotConversation).order_by(CopilotConversation.updated_at.desc())
        if user_id:
            stmt = stmt.where(CopilotConversation.user_id == user_id)
        stmt = stmt.limit(limit).offset(offset)
        return list(db.execute(stmt).scalars().all())

    @classmethod
    def delete_conversation(
        cls,
        db: Session,
        conversation_id: uuid.UUID,
        user_id: Optional[str] = None,
    ) -> bool:
        """Deletes a conversation and its messages."""
        conv = cls.get_conversation(db, conversation_id, user_id)
        if not conv:
            return False
        db.delete(conv)
        db.commit()
        return True

    @classmethod
    def save_message(
        cls,
        db: Session,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        intent: Optional[str] = None,
        query_plan: Optional[Dict[str, Any]] = None,
        evidence_citations: Optional[List[Dict[str, Any]]] = None,
        tokens_used: int = 0,
        execution_duration_ms: int = 0,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        raw_metadata: Optional[Dict[str, Any]] = None,
    ) -> CopilotMessage:
        """Persists a message in the conversation thread."""
        msg = CopilotMessage(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            intent=intent,
            query_plan=query_plan or {},
            evidence_citations=evidence_citations or [],
            tokens_used=tokens_used,
            execution_duration_ms=execution_duration_ms,
            model_name=model_name,
            provider=provider,
            raw_metadata=raw_metadata or {},
            created_at=datetime.now(timezone.utc),
        )
        db.add(msg)

        # Update conversation timestamp
        conv = db.execute(
            select(CopilotConversation).where(CopilotConversation.id == conversation_id)
        ).scalar_one_or_none()
        if conv:
            conv.updated_at = datetime.now(timezone.utc)
            # Update title from first user query if still default
            if conv.title == "FinOps Analysis" and role == MessageRole.USER:
                clean_title = content.strip().split("\n")[0][:60]
                if clean_title:
                    conv.title = clean_title

        db.commit()
        db.refresh(msg)
        return msg

    @classmethod
    def record_feedback(
        cls,
        db: Session,
        message_id: uuid.UUID,
        rating: int,
        feedback_text: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> CopilotFeedback:
        """Records or updates user feedback rating for a specific message."""
        existing = db.execute(
            select(CopilotFeedback).where(CopilotFeedback.message_id == message_id)
        ).scalar_one_or_none()

        if existing:
            existing.rating = rating
            existing.feedback_text = feedback_text
            db.commit()
            db.refresh(existing)
            return existing

        feedback = CopilotFeedback(
            id=uuid.uuid4(),
            message_id=message_id,
            user_id=user_id,
            rating=rating,
            feedback_text=feedback_text,
            created_at=datetime.now(timezone.utc),
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback

    @classmethod
    def record_usage(
        cls,
        db: Session,
        model_name: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        execution_duration_ms: int,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        status: str = "success",
    ) -> CopilotUsageLog:
        """Records operational audit metrics for an analytical turn."""
        log = CopilotUsageLog(
            id=uuid.uuid4(),
            user_id=user_id,
            conversation_id=conversation_id,
            model_name=model_name,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            execution_duration_ms=execution_duration_ms,
            status=status,
            created_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()
        return log

    @classmethod
    def resolve_follow_up_context(
        cls,
        db: Session,
        conversation_id: uuid.UUID,
        current_entities: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Inspects preceding messages in this conversation to carry forward entities
        (e.g., active cloud provider, service, or resource) if not specified in current prompt.
        """
        # Fetch last 3 messages
        messages = list(
            db.execute(
                select(CopilotMessage)
                .where(CopilotMessage.conversation_id == conversation_id)
                .order_by(CopilotMessage.created_at.desc())
                .limit(3)
            ).scalars().all()
        )

        resolved = dict(current_entities)

        # If current query didn't specify provider, check last assistant or user query plan
        if not resolved.get("providers"):
            for m in messages:
                if m.query_plan and isinstance(m.query_plan, dict):
                    filters = m.query_plan.get("filters", {})
                    if "provider" in filters:
                        prov = filters["provider"]
                        if isinstance(prov, list):
                            resolved["providers"] = prov
                        else:
                            resolved["providers"] = [prov]
                        break

        # If current query didn't specify service, check last message filters
        if not resolved.get("services"):
            for m in messages:
                if m.query_plan and isinstance(m.query_plan, dict):
                    filters = m.query_plan.get("filters", {})
                    if "service_name" in filters:
                        svc = filters["service_name"]
                        if isinstance(svc, list):
                            resolved["services"] = svc
                        else:
                            resolved["services"] = [svc]
                        break

        return resolved
