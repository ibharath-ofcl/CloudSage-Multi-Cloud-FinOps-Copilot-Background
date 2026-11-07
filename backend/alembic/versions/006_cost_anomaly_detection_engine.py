"""Add Cost Anomaly Detection Engine Extensions, Cost Baselines, and Anomaly Detection Runs Tables

Revision ID: 006_cost_anomaly_detection_engine
Revises: 005_waste_detection_engine
Create Date: 2026-11-07 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '006_cost_anomaly_detection_engine'
down_revision: Union[str, None] = '005_waste_detection_engine'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to cost_anomalies
    op.add_column('cost_anomalies', sa.Column('detector_id', sa.String(64), nullable=False, server_default='statistical_anomaly_detector'))
    op.add_column('cost_anomalies', sa.Column('detector_version', sa.String(16), nullable=False, server_default='1.0.0'))
    op.add_column('cost_anomalies', sa.Column('resource_id', sa.String(512), nullable=True))
    op.add_column('cost_anomalies', sa.Column('sku', sa.String(128), nullable=True))
    op.add_column('cost_anomalies', sa.Column('anomaly_category', sa.String(64), nullable=False, server_default='SERVICE_SPIKE'))
    op.add_column('cost_anomalies', sa.Column('title', sa.String(256), nullable=True))
    op.add_column('cost_anomalies', sa.Column('explanation', sa.Text(), nullable=True))
    op.add_column('cost_anomalies', sa.Column('detection_method', sa.String(64), nullable=False, server_default='Z_SCORE'))
    op.add_column('cost_anomalies', sa.Column('absolute_deviation', sa.Numeric(18, 4), nullable=False, server_default='0.0000'))
    op.add_column('cost_anomalies', sa.Column('estimated_excess_cost', sa.Numeric(18, 4), nullable=False, server_default='0.0000'))
    op.add_column('cost_anomalies', sa.Column('projected_monthly_impact', sa.Numeric(18, 4), nullable=False, server_default='0.0000'))
    op.add_column('cost_anomalies', sa.Column('currency', sa.String(3), nullable=False, server_default='USD'))
    op.add_column('cost_anomalies', sa.Column('baseline_window_days', sa.Integer(), nullable=False, server_default='30'))
    op.add_column('cost_anomalies', sa.Column('observation_window_days', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('cost_anomalies', sa.Column('confidence_score', sa.Numeric(5, 4), nullable=False, server_default='1.0000'))
    op.add_column('cost_anomalies', sa.Column('baseline_metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'))
    op.add_column('cost_anomalies', sa.Column('contributing_resources', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))
    op.add_column('cost_anomalies', sa.Column('source_billing_references', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))
    op.add_column('cost_anomalies', sa.Column('dismissal_reason', sa.String(512), nullable=True))
    op.add_column('cost_anomalies', sa.Column('dismissed_by', sa.String(128), nullable=True))
    op.add_column('cost_anomalies', sa.Column('resolution_reason', sa.String(512), nullable=True))
    op.add_column('cost_anomalies', sa.Column('resolved_by', sa.String(128), nullable=True))
    op.add_column('cost_anomalies', sa.Column('investigation_notes', sa.Text(), nullable=True))
    op.add_column('cost_anomalies', sa.Column('first_detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column('cost_anomalies', sa.Column('last_detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column('cost_anomalies', sa.Column('reopened_at', sa.DateTime(timezone=True), nullable=True))

    op.create_index('idx_anomaly_cat_severity', 'cost_anomalies', ['anomaly_category', 'severity'])
    op.create_index('idx_anomaly_dedup', 'cost_anomalies', ['provider', 'account_id', 'service_name', 'resource_id', 'anomaly_date', 'anomaly_category'])
    op.create_index('idx_anomaly_detector_id', 'cost_anomalies', ['detector_id'])
    op.create_index('idx_anomaly_method', 'cost_anomalies', ['detection_method'])

    # 2. Create cost_baselines table
    op.create_table(
        'cost_baselines',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dimension_type', sa.String(32), nullable=False),
        sa.Column('dimension_key', sa.String(512), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('account_id', sa.String(64), nullable=True),
        sa.Column('service_name', sa.String(128), nullable=True),
        sa.Column('region', sa.String(64), nullable=True),
        sa.Column('resource_id', sa.String(512), nullable=True),
        sa.Column('window_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('mean', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('stddev', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('median', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('mad', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('q1', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('q3', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('iqr', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('min_value', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('max_value', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('zero_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('version', sa.String(16), nullable=False, server_default='1.0'),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_baseline_dim_key_window', 'cost_baselines', ['dimension_key', 'window_days'])
    op.create_index('idx_baseline_prov_svc', 'cost_baselines', ['provider', 'service_name'])

    # 3. Create anomaly_detection_runs table
    op.create_table(
        'anomaly_detection_runs',
        sa.Column('run_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider', sa.String(16), nullable=False, server_default='ALL'),
        sa.Column('scope', sa.String(64), nullable=False, server_default='FULL'),
        sa.Column('status', sa.String(32), nullable=False, server_default='PENDING'),
        sa.Column('total_series_evaluated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('baselines_generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('anomalies_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('anomalies_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('anomalies_unchanged', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('anomalies_resolved', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_excess_cost', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('detector_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_anomaly_run_prov_status', 'anomaly_detection_runs', ['provider', 'status'])
    op.create_index('idx_anomaly_run_started', 'anomaly_detection_runs', ['started_at'])


def downgrade() -> None:
    op.drop_table('anomaly_detection_runs')
    op.drop_table('cost_baselines')
    op.drop_index('idx_anomaly_method', table_name='cost_anomalies')
    op.drop_index('idx_anomaly_detector_id', table_name='cost_anomalies')
    op.drop_index('idx_anomaly_dedup', table_name='cost_anomalies')
    op.drop_index('idx_anomaly_cat_severity', table_name='cost_anomalies')
    op.drop_column('cost_anomalies', 'reopened_at')
    op.drop_column('cost_anomalies', 'last_detected_at')
    op.drop_column('cost_anomalies', 'first_detected_at')
    op.drop_column('cost_anomalies', 'investigation_notes')
    op.drop_column('cost_anomalies', 'resolved_by')
    op.drop_column('cost_anomalies', 'resolution_reason')
    op.drop_column('cost_anomalies', 'dismissed_by')
    op.drop_column('cost_anomalies', 'dismissal_reason')
    op.drop_column('cost_anomalies', 'source_billing_references')
    op.drop_column('cost_anomalies', 'contributing_resources')
    op.drop_column('cost_anomalies', 'baseline_metrics')
    op.drop_column('cost_anomalies', 'confidence_score')
    op.drop_column('cost_anomalies', 'observation_window_days')
    op.drop_column('cost_anomalies', 'baseline_window_days')
    op.drop_column('cost_anomalies', 'currency')
    op.drop_column('cost_anomalies', 'projected_monthly_impact')
    op.drop_column('cost_anomalies', 'estimated_excess_cost')
    op.drop_column('cost_anomalies', 'absolute_deviation')
    op.drop_column('cost_anomalies', 'detection_method')
    op.drop_column('cost_anomalies', 'explanation')
    op.drop_column('cost_anomalies', 'title')
    op.drop_column('cost_anomalies', 'anomaly_category')
    op.drop_column('cost_anomalies', 'sku')
    op.drop_column('cost_anomalies', 'resource_id')
    op.drop_column('cost_anomalies', 'detector_version')
    op.drop_column('cost_anomalies', 'detector_id')
