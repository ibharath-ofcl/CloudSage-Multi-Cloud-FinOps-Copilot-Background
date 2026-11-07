"""Add Advisory Recommendation Engine Extensions, Evidence, History, and Runs Tables

Revision ID: 007_advisory_recommendations_engine
Revises: 006_cost_anomaly_detection_engine
Create Date: 2026-11-07 17:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '007_advisory_recommendations_engine'
down_revision: Union[str, None] = '006_cost_anomaly_detection_engine'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to recommendations table
    op.add_column('recommendations', sa.Column('recommendation_key', sa.String(256), nullable=False, server_default=sa.text('gen_random_uuid()::text')))
    op.add_column('recommendations', sa.Column('account_id', sa.String(64), nullable=True))
    op.add_column('recommendations', sa.Column('region', sa.String(64), nullable=True))
    op.add_column('recommendations', sa.Column('service_name', sa.String(128), nullable=True))
    op.add_column('recommendations', sa.Column('service_category', sa.String(32), nullable=True))
    op.add_column('recommendations', sa.Column('resource_name', sa.String(256), nullable=True))
    op.add_column('recommendations', sa.Column('strategy_id', sa.String(64), nullable=False, server_default='advisory_strategy'))
    op.add_column('recommendations', sa.Column('strategy_version', sa.String(16), nullable=False, server_default='1.0'))
    op.add_column('recommendations', sa.Column('priority_score', sa.Numeric(5, 4), nullable=False, server_default='0.5000'))
    op.add_column('recommendations', sa.Column('risk_score', sa.Numeric(5, 4), nullable=False, server_default='0.2000'))
    op.add_column('recommendations', sa.Column('confidence_score', sa.Numeric(5, 4), nullable=False, server_default='1.0000'))
    op.add_column('recommendations', sa.Column('current_monthly_cost', sa.Numeric(18, 4), nullable=False, server_default='0.0000'))
    op.add_column('recommendations', sa.Column('projected_monthly_cost', sa.Numeric(18, 4), nullable=False, server_default='0.0000'))
    op.add_column('recommendations', sa.Column('currency', sa.String(3), nullable=False, server_default='USD'))
    op.add_column('recommendations', sa.Column('savings_calculation', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))
    op.add_column('recommendations', sa.Column('implementation_guidance', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))
    op.add_column('recommendations', sa.Column('assumptions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))
    op.add_column('recommendations', sa.Column('evidence_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))
    op.add_column('recommendations', sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))
    op.add_column('recommendations', sa.Column('review_reason', sa.String(512), nullable=True))
    op.add_column('recommendations', sa.Column('reviewed_by', sa.String(128), nullable=True))
    op.add_column('recommendations', sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('recommendations', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('recommendations', sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('recommendations', sa.Column('verified_savings', sa.Numeric(18, 4), nullable=True))
    op.add_column('recommendations', sa.Column('expiry_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('recommendations', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')))

    op.alter_column('recommendations', 'resource_id', nullable=True)

    op.create_index('idx_rec_strategy_status', 'recommendations', ['strategy_id', 'status'])
    op.create_index('idx_rec_key', 'recommendations', ['recommendation_key'])

    # 2. Create recommendation_evidence table
    op.create_table(
        'recommendation_evidence',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('recommendation_id', sa.Uuid(), nullable=False),
        sa.Column('evidence_type', sa.String(64), nullable=False),
        sa.Column('waste_detection_id', sa.Uuid(), nullable=True),
        sa.Column('anomaly_id', sa.Uuid(), nullable=True),
        sa.Column('resource_id', sa.String(512), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('telemetry_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('billing_record_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=False, server_default='1.0000'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['waste_detection_id'], ['waste_detections.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['anomaly_id'], ['cost_anomalies.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_rec_ev_rec_type', 'recommendation_evidence', ['recommendation_id', 'evidence_type'])

    # 3. Create recommendation_history table
    op.create_table(
        'recommendation_history',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('recommendation_id', sa.Uuid(), nullable=False),
        sa.Column('from_status', sa.String(32), nullable=True),
        sa.Column('to_status', sa.String(32), nullable=False),
        sa.Column('actor', sa.String(128), nullable=False),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['recommendation_id'], ['recommendations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_rec_hist_rec_time', 'recommendation_history', ['recommendation_id', 'created_at'])

    # 4. Create recommendation_runs table
    op.create_table(
        'recommendation_runs',
        sa.Column('run_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False, server_default='ALL'),
        sa.Column('scope', sa.String(64), nullable=False, server_default='FULL'),
        sa.Column('status', sa.String(32), nullable=False, server_default='PENDING'),
        sa.Column('total_evaluated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('recommendations_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('recommendations_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('recommendations_unchanged', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('recommendations_suppressed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_monthly_savings', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('total_annual_savings', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('strategy_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('run_id')
    )
    op.create_index('idx_rec_run_prov_status', 'recommendation_runs', ['provider', 'status'])
    op.create_index('idx_rec_run_started', 'recommendation_runs', ['started_at'])


def downgrade() -> None:
    op.drop_index('idx_rec_run_started', table_name='recommendation_runs')
    op.drop_index('idx_rec_run_prov_status', table_name='recommendation_runs')
    op.drop_table('recommendation_runs')

    op.drop_index('idx_rec_hist_rec_time', table_name='recommendation_history')
    op.drop_table('recommendation_history')

    op.drop_index('idx_rec_ev_rec_type', table_name='recommendation_evidence')
    op.drop_table('recommendation_evidence')

    op.drop_index('idx_rec_key', table_name='recommendations')
    op.drop_index('idx_rec_strategy_status', table_name='recommendations')

    for col in [
        'updated_at', 'expiry_at', 'verified_savings', 'verified_at', 'reviewed_at',
        'accepted_at', 'reviewed_by', 'review_reason', 'tags', 'evidence_summary',
        'assumptions', 'implementation_guidance', 'savings_calculation', 'currency',
        'projected_monthly_cost', 'current_monthly_cost', 'confidence_score',
        'risk_score', 'priority_score', 'strategy_version', 'strategy_id',
        'resource_name', 'service_category', 'service_name', 'region', 'account_id',
        'recommendation_key',
    ]:
        op.drop_column('recommendations', col)
