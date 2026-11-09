"""Add Advanced Anomaly Investigation and Root Cause Analysis Models

Revision ID: 011_advanced_anomaly_investigation
Revises: 010_cost_anomaly_alerts_hub
Create Date: 2026-11-08 22:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '011_advanced_anomaly_investigation'
down_revision: Union[str, None] = '010_cost_anomaly_alerts_hub'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create investigation_cases table
    op.create_table(
        'investigation_cases',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('case_number', sa.String(length=32), nullable=False),
        sa.Column('anomaly_id', sa.Uuid(), nullable=False),
        sa.Column('alert_instance_id', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='NEW', nullable=False),
        sa.Column('priority', sa.String(length=16), server_default='MEDIUM', nullable=False),
        sa.Column('assigned_to', sa.String(length=128), nullable=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provider', sa.String(length=16), nullable=False),
        sa.Column('account_id', sa.String(length=64), nullable=False),
        sa.Column('service_name', sa.String(length=128), nullable=False),
        sa.Column('region', sa.String(length=64), nullable=True),
        sa.Column('resource_id', sa.String(length=512), nullable=True),
        sa.Column('excess_cost', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
        sa.Column('actual_cost', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
        sa.Column('expected_cost', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
        sa.Column('root_cause_summary', sa.Text(), nullable=True),
        sa.Column('verified_root_cause', sa.Text(), nullable=True),
        sa.Column('suspected_category', sa.String(length=64), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=128), nullable=False),
        sa.Column('updated_by', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by', sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(['alert_instance_id'], ['alert_instances.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['anomaly_id'], ['cost_anomalies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('case_number'),
    )
    op.create_index('idx_inv_account_status', 'investigation_cases', ['account_id', 'status'], unique=False)
    op.create_index('idx_inv_assigned', 'investigation_cases', ['assigned_to', 'status'], unique=False)
    op.create_index('idx_inv_prov_status', 'investigation_cases', ['provider', 'status'], unique=False)
    op.create_index('ix_investigation_cases_anomaly_id', 'investigation_cases', ['anomaly_id'], unique=False)
    op.create_index('ix_investigation_cases_case_number', 'investigation_cases', ['case_number'], unique=True)
    op.create_index('ix_investigation_cases_status', 'investigation_cases', ['status'], unique=False)
    op.create_index('ix_investigation_cases_priority', 'investigation_cases', ['priority'], unique=False)

    # 2. Create investigation_findings table
    op.create_table(
        'investigation_findings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('investigation_id', sa.Uuid(), nullable=False),
        sa.Column('finding_type', sa.String(length=32), server_default='FACT', nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('dimension', sa.String(length=64), nullable=True),
        sa.Column('financial_impact', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
        sa.Column('contribution_percentage', sa.Numeric(precision=8, scale=2), server_default='0.00', nullable=False),
        sa.Column('confidence_category', sa.String(length=32), server_default='MEDIUM', nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=5, scale=4), server_default='1.0000', nullable=False),
        sa.Column('evidence_source', sa.String(length=64), server_default='BILLING_RECORD', nullable=False),
        sa.Column('evidence_reference', sa.String(length=512), nullable=True),
        sa.Column('supporting_observations', sa.JSON(), nullable=False),
        sa.Column('contradictory_observations', sa.JSON(), nullable=False),
        sa.Column('suggested_next_step', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(length=128), server_default='system_engine', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigation_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_investigation_findings_investigation_id', 'investigation_findings', ['investigation_id'], unique=False)
    op.create_index('ix_investigation_findings_finding_type', 'investigation_findings', ['finding_type'], unique=False)
    op.create_index('ix_investigation_findings_confidence_category', 'investigation_findings', ['confidence_category'], unique=False)

    # 3. Create investigation_notes table
    op.create_table(
        'investigation_notes',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('investigation_id', sa.Uuid(), nullable=False),
        sa.Column('author', sa.String(length=128), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_system_generated', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigation_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_investigation_notes_investigation_id', 'investigation_notes', ['investigation_id'], unique=False)

    # 4. Create investigation_evidence_links table
    op.create_table(
        'investigation_evidence_links',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('investigation_id', sa.Uuid(), nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('entity_id', sa.String(length=512), nullable=False),
        sa.Column('relationship_role', sa.String(length=64), server_default='SUPPORTING_EVIDENCE', nullable=False),
        sa.Column('metadata_snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigation_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_inv_ev_type_id', 'investigation_evidence_links', ['entity_type', 'entity_id'], unique=False)
    op.create_index('ix_investigation_evidence_links_investigation_id', 'investigation_evidence_links', ['investigation_id'], unique=False)

    # 5. Create investigation_history table
    op.create_table(
        'investigation_history',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('investigation_id', sa.Uuid(), nullable=False),
        sa.Column('from_status', sa.String(length=32), nullable=True),
        sa.Column('to_status', sa.String(length=32), nullable=False),
        sa.Column('actor', sa.String(length=128), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['investigation_id'], ['investigation_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_investigation_history_investigation_id', 'investigation_history', ['investigation_id'], unique=False)
    op.create_index('ix_investigation_history_created_at', 'investigation_history', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('investigation_history')
    op.drop_table('investigation_evidence_links')
    op.drop_table('investigation_notes')
    op.drop_table('investigation_findings')
    op.drop_table('investigation_cases')
