"""Add Waste Detection Engine Extensions and Waste Detection Runs Table

Revision ID: 005_waste_detection_engine
Revises: 004_resource_inventory
Create Date: 2026-11-07 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '005_waste_detection_engine'
down_revision: Union[str, None] = '004_resource_inventory'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to waste_detections
    op.add_column('waste_detections', sa.Column('account_id', sa.String(64), nullable=True))
    op.add_column('waste_detections', sa.Column('resource_type', sa.String(64), nullable=True))
    op.add_column('waste_detections', sa.Column('detector_id', sa.String(64), nullable=True))
    op.add_column('waste_detections', sa.Column('detector_version', sa.String(16), nullable=False, server_default='1.0'))
    op.add_column('waste_detections', sa.Column('finding_title', sa.String(256), nullable=True))
    op.add_column('waste_detections', sa.Column('explanation', sa.Text(), nullable=True))
    op.add_column('waste_detections', sa.Column('confidence_score', sa.Numeric(5, 4), nullable=False, server_default='1.0000'))
    op.add_column('waste_detections', sa.Column('currency', sa.String(8), nullable=False, server_default='USD'))
    op.add_column('waste_detections', sa.Column('original_currency', sa.String(8), nullable=True))
    op.add_column('waste_detections', sa.Column('original_cost', sa.Numeric(18, 4), nullable=True))
    op.add_column('waste_detections', sa.Column('observation_window_days', sa.Integer(), nullable=False, server_default='7'))
    op.add_column('waste_detections', sa.Column('data_quality_status', sa.String(32), nullable=False, server_default='VERIFIED'))
    op.add_column('waste_detections', sa.Column('requires_human_review', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('waste_detections', sa.Column('first_detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column('waste_detections', sa.Column('last_evaluated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    op.create_index('idx_waste_detector_status', 'waste_detections', ['detector_id', 'status'])
    op.create_index('idx_waste_res_type', 'waste_detections', ['resource_id', 'waste_type'])
    op.create_index('idx_waste_account_id', 'waste_detections', ['account_id'])

    # 2. Create waste_detection_runs table
    op.create_table(
        'waste_detection_runs',
        sa.Column('run_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider', sa.String(16), nullable=False, server_default='ALL'),
        sa.Column('status', sa.String(32), nullable=False, server_default='PENDING'),
        sa.Column('total_resources_evaluated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('findings_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('findings_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('findings_unchanged', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_estimated_monthly_savings', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('detector_summary', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('error_details', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_waste_run_prov_status', 'waste_detection_runs', ['provider', 'status'])
    op.create_index('idx_waste_run_started', 'waste_detection_runs', ['started_at'])


def downgrade() -> None:
    op.drop_table('waste_detection_runs')
    op.drop_index('idx_waste_account_id', table_name='waste_detections')
    op.drop_index('idx_waste_res_type', table_name='waste_detections')
    op.drop_index('idx_waste_detector_status', table_name='waste_detections')
    op.drop_column('waste_detections', 'last_evaluated_at')
    op.drop_column('waste_detections', 'first_detected_at')
    op.drop_column('waste_detections', 'requires_human_review')
    op.drop_column('waste_detections', 'data_quality_status')
    op.drop_column('waste_detections', 'observation_window_days')
    op.drop_column('waste_detections', 'original_cost')
    op.drop_column('waste_detections', 'original_currency')
    op.drop_column('waste_detections', 'currency')
    op.drop_column('waste_detections', 'confidence_score')
    op.drop_column('waste_detections', 'explanation')
    op.drop_column('waste_detections', 'finding_title')
    op.drop_column('waste_detections', 'detector_version')
    op.drop_column('waste_detections', 'detector_id')
    op.drop_column('waste_detections', 'resource_type')
    op.drop_column('waste_detections', 'account_id')
