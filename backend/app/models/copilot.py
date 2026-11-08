"""
CloudSage AI FinOps Copilot Models.
Persists conversational memory, chat messages with analytical query plans,
grounded citations, user feedback, and model token usage logs.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from backend.app.core.database import Base
from backend.app.core.enums import MessageRole

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class CopilotConversation(Base):
    """
    User conversation session with CloudSage AI FinOps Copilot.
    Encapsulates sequential chat turns and multi-turn analytical context.
    """
    __tablename__ = "copilot_conversations"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id = Column(
        String(100),
        nullable=True,
        index=True,
        doc="Identity of authenticated user or tenant initiating session",
    )
    title = Column(
        String(255),
        nullable=False,
        default="FinOps Analysis",
        doc="Human-readable title or generated summary topic of discussion",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    messages = relationship(
        "CopilotMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="CopilotMessage.created_at",
    )

    __table_args__ = (
        Index("idx_copilot_conv_user", "user_id"),
        Index("idx_copilot_conv_updated", "updated_at"),
    )


class CopilotMessage(Base):
    """
    Single conversational turn in a Copilot session.
    Stores the user prompt or assistant response, executed query plans,
    evidence citations, and token telemetry.
    """
    __tablename__ = "copilot_messages"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    conversation_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("copilot_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        String(32),
        nullable=False,
        default=MessageRole.USER,
        doc="Role: USER, ASSISTANT, or SYSTEM",
    )
    content = Column(
        Text,
        nullable=False,
        doc="Full verbatim content of user query or assistant response",
    )
    intent = Column(
        String(64),
        nullable=True,
        doc="Classified FinOps intent category",
    )
    query_plan = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Deterministic structured query plan executed against backend data",
    )
    evidence_citations = Column(
        JSON_TYPE,
        nullable=False,
        default=list,
        doc="Cross-stage database rows, metrics, and records cited in response",
    )
    tokens_used = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Combined prompt and completion tokens consumed",
    )
    execution_duration_ms = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Total roundtrip analytical execution latency in milliseconds",
    )
    model_name = Column(
        String(100),
        nullable=True,
        doc="Model ID utilized (e.g. gpt-4o-mini or deterministic-fallback)",
    )
    provider = Column(
        String(50),
        nullable=True,
        doc="LLM backend provider (e.g. openai, azure, fallback)",
    )
    raw_metadata = Column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        doc="Additional debug telemetry, extracted entities, or tool metadata",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    conversation = relationship(
        "CopilotConversation",
        back_populates="messages",
    )
    feedback = relationship(
        "CopilotFeedback",
        back_populates="message",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        Index("idx_copilot_msg_conv_time", "conversation_id", "created_at"),
        Index("idx_copilot_msg_intent", "intent"),
    )


class CopilotFeedback(Base):
    """
    User satisfaction rating and commentary on a Copilot assistant message.
    Supports continuous reinforcement and accuracy evaluation.
    """
    __tablename__ = "copilot_feedback"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    message_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("copilot_messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id = Column(
        String(100),
        nullable=True,
        doc="User providing feedback",
    )
    rating = Column(
        Integer,
        nullable=False,
        doc="1 for thumbs up (helpful), -1 for thumbs down (unhelpful/incorrect)",
    )
    feedback_text = Column(
        Text,
        nullable=True,
        doc="Optional user critique or qualitative evaluation",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    message = relationship(
        "CopilotMessage",
        back_populates="feedback",
    )

    __table_args__ = (
        Index("idx_copilot_fb_rating", "rating"),
    )


class CopilotUsageLog(Base):
    """
    Audit log tracking token usage, latency, and status across Copilot invocations.
    Enables cost tracking and operational monitoring of the FinOps Copilot itself.
    """
    __tablename__ = "copilot_usage_logs"

    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id = Column(
        String(100),
        nullable=True,
        index=True,
    )
    conversation_id = Column(
        String(100),
        nullable=True,
        index=True,
    )
    model_name = Column(
        String(100),
        nullable=False,
    )
    provider = Column(
        String(50),
        nullable=False,
    )
    prompt_tokens = Column(
        Integer,
        nullable=False,
        default=0,
    )
    completion_tokens = Column(
        Integer,
        nullable=False,
        default=0,
    )
    total_tokens = Column(
        Integer,
        nullable=False,
        default=0,
    )
    execution_duration_ms = Column(
        Integer,
        nullable=False,
        default=0,
    )
    status = Column(
        String(50),
        nullable=False,
        default="success",
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        Index("idx_copilot_usage_created", "created_at"),
        Index("idx_copilot_usage_model", "model_name"),
    )

