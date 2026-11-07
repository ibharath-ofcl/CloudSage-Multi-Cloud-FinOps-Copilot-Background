"""Initial CloudSage Schema Migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-07 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Users Table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(256), nullable=False, unique=True),
        sa.Column('full_name', sa.String(128), nullable=False),
        sa.Column('hashed_password', sa.String(256), nullable=False),
        sa.Column('role', sa.String(32), nullable=False, server_default='FINANCE_ANALYST'),
        sa.Column('department', sa.String(64), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # 2. Cloud Resources Table
    op.create_table(
        'cloud_resources',
        sa.Column('resource_id', sa.String(512), primary_key=True),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('account_id', sa.String(64), nullable=False),
        sa.Column('resource_name', sa.String(256), nullable=True),
        sa.Column('service_category', sa.String(32), nullable=False),
        sa.Column('service_name', sa.String(128), nullable=False),
        sa.Column('resource_type', sa.String(64), nullable=False),
        sa.Column('region', sa.String(64), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='active'),
        sa.Column('tags', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('owner', sa.String(128), nullable=True),
        sa.Column('environment', sa.String(64), nullable=False, server_default='unknown'),
        sa.Column('cost_center', sa.String(64), nullable=True),
        sa.Column('monthly_cost', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('first_discovered_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_res_prov_env', 'cloud_resources', ['provider', 'environment'])
    op.create_index('idx_res_owner', 'cloud_resources', ['owner'])

    # 3. Billing Records Table (FOCUS 1.0)
    op.create_table(
        'billing_records',
        sa.Column('record_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('billing_account_id', sa.String(64), nullable=False),
        sa.Column('subscription_id', sa.String(64), nullable=False),
        sa.Column('resource_id', sa.String(512), nullable=False),
        sa.Column('resource_name', sa.String(256), nullable=True),
        sa.Column('service_category', sa.String(32), nullable=False),
        sa.Column('service_name', sa.String(128), nullable=False),
        sa.Column('region', sa.String(64), nullable=False),
        sa.Column('zone', sa.String(64), nullable=True),
        sa.Column('usage_start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('usage_end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('usage_quantity', sa.Numeric(18, 6), nullable=False, server_default='0.0'),
        sa.Column('usage_unit', sa.String(32), nullable=False),
        sa.Column('unblended_cost', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('blended_cost', sa.Numeric(18, 4), nullable=True),
        sa.Column('list_cost', sa.Numeric(18, 4), nullable=True),
        sa.Column('pricing_model', sa.String(32), nullable=False, server_default='ON_DEMAND'),
        sa.Column('currency', sa.String(8), nullable=False, server_default='USD'),
        sa.Column('tags', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('raw_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_billing_prov_srv_time', 'billing_records', ['provider', 'service_category', 'usage_start_time'])
    op.create_index('idx_billing_res_time', 'billing_records', ['resource_id', 'usage_start_time'])

    # 4. Resource Metrics Table
    op.create_table(
        'resource_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', sa.String(512), sa.ForeignKey('cloud_resources.resource_id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric_name', sa.String(64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('average_value', sa.Numeric(10, 4), nullable=False),
        sa.Column('peak_value', sa.Numeric(10, 4), nullable=False),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='1'),
    )
    op.create_index('idx_metrics_res_name_time', 'resource_metrics', ['resource_id', 'metric_name', 'timestamp'])

    # 5. Waste Detections Table
    op.create_table(
        'waste_detections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('resource_id', sa.String(512), sa.ForeignKey('cloud_resources.resource_id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('waste_type', sa.String(32), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(16), nullable=False, server_default='ACTIVE'),
        sa.Column('estimated_monthly_waste', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('telemetry_proof', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('dismissal_reason', sa.String(512), nullable=True),
        sa.Column('dismissed_by', sa.String(128), nullable=True),
        sa.Column('snooze_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_waste_active_prov', 'waste_detections', ['status', 'provider'])
    op.create_index('idx_waste_type_status', 'waste_detections', ['waste_type', 'status'])

    # 6. Advisory Recommendations Table
    op.create_table(
        'recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('waste_detection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('waste_detections.id', ondelete='SET NULL'), nullable=True),
        sa.Column('resource_id', sa.String(512), sa.ForeignKey('cloud_resources.resource_id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('action_type', sa.String(32), nullable=False),
        sa.Column('priority', sa.String(8), nullable=False, server_default='P2'),
        sa.Column('risk_level', sa.String(16), nullable=False, server_default='LOW'),
        sa.Column('status', sa.String(16), nullable=False, server_default='PROPOSED'),
        sa.Column('estimated_monthly_savings', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('estimated_annual_savings', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('implementation_effort', sa.String(16), nullable=False, server_default='LOW'),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('remediation_guide', sa.Text(), nullable=False),
        sa.Column('endorsed_by', sa.String(128), nullable=True),
        sa.Column('approved_by', sa.String(128), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('implemented_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_rec_status_priority', 'recommendations', ['status', 'priority'])
    op.create_index('idx_rec_prov_savings', 'recommendations', ['provider', 'estimated_monthly_savings'])

    # 7. Cost Anomalies Table
    op.create_table(
        'cost_anomalies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('service_category', sa.String(32), nullable=False),
        sa.Column('service_name', sa.String(128), nullable=False),
        sa.Column('account_id', sa.String(64), nullable=False),
        sa.Column('region', sa.String(64), nullable=False),
        sa.Column('anomaly_date', sa.Date(), nullable=False),
        sa.Column('actual_cost', sa.Numeric(18, 4), nullable=False),
        sa.Column('expected_cost', sa.Numeric(18, 4), nullable=False),
        sa.Column('baseline_mean', sa.Numeric(18, 4), nullable=False),
        sa.Column('baseline_stddev', sa.Numeric(18, 4), nullable=False),
        sa.Column('z_score', sa.Numeric(8, 4), nullable=False),
        sa.Column('spike_percentage', sa.Numeric(8, 2), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False, server_default='MEDIUM'),
        sa.Column('status', sa.String(16), nullable=False, server_default='OPEN'),
        sa.Column('root_cause_analysis', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_anomaly_status_date', 'cost_anomalies', ['status', 'anomaly_date'])

    # 8. Audit Logs Table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_email', sa.String(256), nullable=True),
        sa.Column('action_type', sa.String(64), nullable=False),
        sa.Column('resource_type', sa.String(64), nullable=False),
        sa.Column('resource_id', sa.String(512), nullable=True),
        sa.Column('before_state', postgresql.JSONB(), nullable=True),
        sa.Column('after_state', postgresql.JSONB(), nullable=True),
        sa.Column('client_ip', sa.String(64), nullable=True),
        sa.Column('status', sa.String(16), nullable=False, server_default='SUCCESS'),
    )
    op.create_index('idx_audit_user_time', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('idx_audit_action_time', 'audit_logs', ['action_type', 'timestamp'])

    # 9. Alert Rules & Notification Logs
    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('alert_type', sa.String(32), nullable=False),
        sa.Column('threshold_value', sa.Numeric(18, 4), nullable=False),
        sa.Column('channels', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        'notification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('alert_rule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('alert_rules.id', ondelete='SET NULL'), nullable=True),
        sa.Column('channel', sa.String(32), nullable=False),
        sa.Column('recipient', sa.String(256), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='DELIVERED'),
        sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('notification_logs')
    op.drop_table('alert_rules')
    op.drop_table('audit_logs')
    op.drop_table('cost_anomalies')
    op.drop_table('recommendations')
    op.drop_table('waste_detections')
    op.drop_table('resource_metrics')
    op.drop_table('billing_records')
    op.drop_table('cloud_resources')
    op.drop_table('users')
