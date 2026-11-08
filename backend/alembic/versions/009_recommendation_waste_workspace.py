"""Add Recommendation Waste Workspace columns and Savings Overrides Table

Revision ID: 009_recommendation_waste_workspace
Revises: 008_ai_finops_copilot
Create Date: 2026-11-07 23:58:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '009_recommendation_waste_workspace'
down_revision: Union[str, None] = '008_ai_finops_copilot'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add workspace columns to recommendations
    op.add_column('recommendations', sa.Column('snooze_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('recommendations', sa.Column('assigned_to', sa.String(128), nullable=True))
    op.add_column('recommendations', sa.Column('external_ticket_ref', sa.String(128), nullable=True))
    op.add_column('recommendations', sa.Column('revised_monthly_savings', sa.Numeric(18, 4), nullable=True))
    op.add_column('recommendations', sa.Column('is_savings_overridden', sa.Boolean(), server_default='false', nullable=False))
    op.create_index('idx_rec_assigned', 'recommendations', ['assigned_to'])
    op.create_index('idx_rec_ticket', 'recommendations', ['external_ticket_ref'])

    # 2. Add workspace triage columns to waste_detections
    op.add_column('waste_detections', sa.Column('assigned_to', sa.String(128), nullable=True))
    op.add_column('waste_detections', sa.Column('resolved_by', sa.String(128), nullable=True))
    op.add_column('waste_detections', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('waste_detections', sa.Column('reopened_by', sa.String(128), nullable=True))
    op.add_column('waste_detections', sa.Column('reopened_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('waste_detections', sa.Column('action_notes', sa.Text(), nullable=True))
    op.create_index('idx_waste_assigned', 'waste_detections', ['assigned_to'])

    # 3. Create recommendation_savings_overrides table
    op.create_table(
        'recommendation_savings_overrides',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('recommendation_id', sa.Uuid(), nullable=False),
        sa.Column('original_monthly_savings', sa.Numeric(18, 4), nullable=False),
        sa.Column('proposed_monthly_savings', sa.Numeric(18, 4), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('proposed_by', sa.String(128), nullable=False),
        sa.Column('approved_by', sa.String(128), nullable=True),
        sa.Column('status', sa.String(32), server_default='PROPOSED', nullable=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_rec_override_rec_status', 'recommendation_savings_overrides', ['recommendation_id', 'status'])
    op.create_index('idx_rec_override_created', 'recommendation_savings_overrides', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_rec_override_created', table_name='recommendation_savings_overrides')
    op.drop_index('idx_rec_override_rec_status', table_name='recommendation_savings_overrides')
    op.drop_table('recommendation_savings_overrides')

    op.drop_index('idx_waste_assigned', table_name='waste_detections')
    op.drop_column('waste_detections', 'action_notes')
    op.drop_column('waste_detections', 'reopened_at')
    op.drop_column('waste_detections', 'reopened_by')
    op.drop_column('waste_detections', 'resolved_at')
    op.drop_column('waste_detections', 'resolved_by')
    op.drop_column('waste_detections', 'assigned_to')

    op.drop_index('idx_rec_ticket', table_name='recommendations')
    op.drop_index('idx_rec_assigned', table_name='recommendations')
    op.drop_column('recommendations', 'is_savings_overridden')
    op.drop_column('recommendations', 'revised_monthly_savings')
    op.drop_column('recommendations', 'external_ticket_ref')
    op.drop_column('recommendations', 'assigned_to')
    op.drop_column('recommendations', 'snooze_until')
