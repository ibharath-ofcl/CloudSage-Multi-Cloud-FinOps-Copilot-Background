"""
Unit Tests for Copilot Conversation Management and Contextual Memory.
Verifies conversation lifecycle, chronological turn storage, feedback tracking,
usage audit logging, and multi-turn entity carry-over.
"""

from decimal import Decimal
import uuid
import pytest

from backend.app.core.enums import MessageRole
from backend.app.copilot.conversation import ConversationManager
from backend.app.models.copilot import CopilotConversation, CopilotMessage


def test_conversation_lifecycle(db_session):
    """Verify creating, fetching, listing, and deleting conversations."""
    # 1. Create
    conv = ConversationManager.get_or_create_conversation(
        db_session, user_id="alice", title="AWS Billing Q3"
    )
    assert conv.id is not None
    assert conv.user_id == "alice"
    assert conv.title == "AWS Billing Q3"

    # 2. Fetch
    fetched = ConversationManager.get_conversation(db_session, conv.id)
    assert fetched is not None
    assert fetched.id == conv.id

    # 3. List
    conv_list = ConversationManager.list_conversations(db_session, user_id="alice")
    assert len(conv_list) == 1
    assert conv_list[0].id == conv.id

    # 4. Delete
    deleted = ConversationManager.delete_conversation(db_session, conv.id)
    assert deleted is True
    assert ConversationManager.get_conversation(db_session, conv.id) is None


def test_save_messages_and_auto_title(db_session):
    """Verify message turn persistence and title auto-generation from first prompt."""
    conv = ConversationManager.get_or_create_conversation(db_session, user_id="bob")
    assert conv.title == "FinOps Analysis"

    # Save user message
    msg1 = ConversationManager.save_message(
        db=db_session,
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="What is our total spend on Google Cloud?",
        intent="TOTAL_CLOUD_SPEND",
    )
    assert msg1.id is not None
    assert msg1.role == MessageRole.USER.value

    # Verify conversation title was updated
    refreshed_conv = ConversationManager.get_conversation(db_session, conv.id)
    assert "What is our total spend on Google Cloud?" in refreshed_conv.title

    # Save assistant message
    msg2 = ConversationManager.save_message(
        db=db_session,
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT.value,
        content="Total spend is $1,200.0000 USD.",
        intent="TOTAL_CLOUD_SPEND",
        tokens_used=120,
        execution_duration_ms=45,
    )
    assert msg2.id is not None
    assert msg2.tokens_used == 120

    # Verify message count and ordering
    conv_detail = ConversationManager.get_conversation(db_session, conv.id)
    assert len(conv_detail.messages) == 2
    assert conv_detail.messages[0].id == msg1.id
    assert conv_detail.messages[1].id == msg2.id


def test_record_feedback(db_session):
    """Verify user feedback rating and updates."""
    conv = ConversationManager.get_or_create_conversation(db_session, user_id="carol")
    msg = ConversationManager.save_message(
        db=db_session,
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT.value,
        content="Optimization advice content.",
    )

    # Initial rating (thumbs up)
    fb1 = ConversationManager.record_feedback(
        db=db_session,
        message_id=msg.id,
        rating=1,
        feedback_text="Very accurate and helpful!",
        user_id="carol",
    )
    assert fb1.rating == 1
    assert fb1.feedback_text == "Very accurate and helpful!"

    # Update rating (thumbs down)
    fb2 = ConversationManager.record_feedback(
        db=db_session,
        message_id=msg.id,
        rating=-1,
        feedback_text="Actually cost numbers changed.",
        user_id="carol",
    )
    assert fb2.id == fb1.id
    assert fb2.rating == -1


def test_multi_turn_entity_carry_over(db_session):
    """Verify that prior message filters carry over in follow-up queries."""
    conv = ConversationManager.get_or_create_conversation(db_session, user_id="dave")

    # Turn 1: User asks about AWS EC2
    ConversationManager.save_message(
        db=db_session,
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content="How much did we spend on AWS EC2?",
    )
    ConversationManager.save_message(
        db=db_session,
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT.value,
        content="AWS EC2 cost $500.",
        query_plan={"filters": {"provider": "AWS", "service_name": "Amazon EC2"}},
    )

    # Turn 2: Follow-up question without explicit provider or service
    follow_up_entities = {"providers": [], "services": [], "time_window": "last_7_days"}
    resolved = ConversationManager.resolve_follow_up_context(db_session, conv.id, follow_up_entities)

    assert resolved["providers"] == ["AWS"]
    assert resolved["services"] == ["Amazon EC2"]


def test_record_usage_log(db_session):
    """Verify recording of token telemetry in copilot_usage_logs."""
    conv = ConversationManager.get_or_create_conversation(db_session, user_id="eve")
    log = ConversationManager.record_usage(
        db=db_session,
        model_name="gpt-4o-mini",
        provider="openai",
        prompt_tokens=85,
        completion_tokens=140,
        execution_duration_ms=320,
        user_id="eve",
        conversation_id=str(conv.id),
        status="success",
    )
    assert log.id is not None
    assert log.total_tokens == 225
    assert log.status == "success"
