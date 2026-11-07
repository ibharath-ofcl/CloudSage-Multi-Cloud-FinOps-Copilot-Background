"""Add AI FinOps Copilot Conversations, Messages, Feedback, and Usage Tables

Revision ID: 008_ai_finops_copilot
Revises: 007_advisory_recommendations_engine
Create Date: 2026-11-07 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '008_ai_finops_copilot'
down_revision: Union[str, None] = '007_advisory_recommendations_engine'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create copilot_conversations table
    op.create_table(
        'copilot_conversations',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('title', sa.String(255), nullable=False, server_default='FinOps Analysis'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_copilot_conv_user', 'copilot_conversations', ['user_id'])
    op.create_index('idx_copilot_conv_updated', 'copilot_conversations', ['updated_at'])

    # 2. Create copilot_messages table
    op.create_table(
        'copilot_messages',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('conversation_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.String(32), nullable=False, server_default='USER'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('intent', sa.String(64), nullable=True),
        sa.Column('query_plan', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('evidence_citations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('execution_duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('model_name', sa.String(100), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('raw_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['conversation_id'], ['copilot_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_copilot_msg_conv_time', 'copilot_messages', ['conversation_id', 'created_at'])
    op.create_index('idx_copilot_msg_intent', 'copilot_messages', ['intent'])

    # 3. Create copilot_feedback table
    op.create_table(
        'copilot_feedback',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('message_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['message_id'], ['copilot_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('message_id')
    )
    op.create_index('idx_copilot_fb_rating', 'copilot_feedback', ['rating'])

    # 4. Create copilot_usage_logs table
    op.create_table(
        'copilot_usage_logs',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('conversation_id', sa.String(100), nullable=True),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('execution_duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='success'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_copilot_usage_created', 'copilot_usage_logs', ['created_at'])
    op.create_index('idx_copilot_usage_model', 'copilot_usage_logs', ['model_name'])


def downgrade() -> None:
    op.drop_index('idx_copilot_usage_model', table_name='copilot_usage_logs')
    op.drop_index('idx_copilot_usage_created', table_name='copilot_usage_logs')
    op.drop_table('copilot_usage_logs')

    op.drop_index('idx_copilot_fb_rating', table_name='copilot_feedback')
    op.drop_table('copilot_feedback')

    op.drop_index('idx_copilot_msg_intent', table_name='copilot_messages')
    op.drop_index('idx_copilot_msg_conv_time', table_name='copilot_messages')
    op.drop_table('copilot_messages')

    op.drop_index('idx_copilot_conv_updated', table_name='copilot_conversations')
    op.drop_index('idx_copilot_conv_user', table_name='copilot_conversations')
    op.drop_table('copilot_conversations')
