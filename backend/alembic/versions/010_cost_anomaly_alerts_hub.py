"""Add Cost Anomaly Alerts and Notification Hub Models

Revision ID: 010_cost_anomaly_alerts_hub
Revises: 009_recommendation_waste_workspace
Create Date: 2026-11-08 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '010_cost_anomaly_alerts_hub'
down_revision: Union[str, None] = '009_recommendation_waste_workspace'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend alert_rules with multi-cloud scoping and threshold columns
    op.add_column('alert_rules', sa.Column('description', sa.String(512), nullable=True))
    op.add_column('alert_rules', sa.Column('provider', sa.String(16), server_default='ALL', nullable=False))
    op.add_column('alert_rules', sa.Column('account_id', sa.String(64), nullable=True))
    op.add_column('alert_rules', sa.Column('region', sa.String(64), nullable=True))
    op.add_column('alert_rules', sa.Column('service_name', sa.String(128), nullable=True))
    op.add_column('alert_rules', sa.Column('environment', sa.String(64), nullable=True))
    op.add_column('alert_rules', sa.Column('owner', sa.String(128), nullable=True))
    op.add_column('alert_rules', sa.Column('cost_center', sa.String(64), nullable=True))
    op.add_column('alert_rules', sa.Column('min_severity', sa.String(16), server_default='MEDIUM', nullable=False))
    op.add_column('alert_rules', sa.Column('min_excess_cost', sa.Numeric(18, 4), server_default='0.0000', nullable=False))
    op.add_column('alert_rules', sa.Column('percentage_deviation_threshold', sa.Numeric(8, 2), server_default='0.00', nullable=False))
    op.add_column('alert_rules', sa.Column('absolute_deviation_threshold', sa.Numeric(18, 4), server_default='0.0000', nullable=False))
    op.add_column('alert_rules', sa.Column('anomaly_category', sa.String(64), nullable=True))
    op.add_column('alert_rules', sa.Column('recipients', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))
    op.add_column('alert_rules', sa.Column('cooldown_minutes', sa.Integer(), server_default='1440', nullable=False))
    op.add_column('alert_rules', sa.Column('escalation_policy', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False))
    op.add_column('alert_rules', sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('alert_rules', sa.Column('created_by', sa.String(128), server_default='system', nullable=False))
    op.add_column('alert_rules', sa.Column('updated_by', sa.String(128), nullable=True))
    op.add_column('alert_rules', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False))

    op.create_index('idx_alert_rule_provider', 'alert_rules', ['provider'])
    op.create_index('idx_alert_rule_account', 'alert_rules', ['account_id'])
    op.create_index('idx_alert_rule_severity', 'alert_rules', ['min_severity'])
    op.create_index('idx_alert_rule_archived', 'alert_rules', ['is_archived'])

    # 2. Create alert_instances table
    op.create_table(
        'alert_instances',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('alert_rule_id', sa.Uuid(), nullable=True),
        sa.Column('anomaly_id', sa.Uuid(), nullable=False),
        sa.Column('dedup_key', sa.String(256), nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('severity', sa.String(16), server_default='MEDIUM', nullable=False),
        sa.Column('current_cost', sa.Numeric(18, 4), server_default='0.0000', nullable=False),
        sa.Column('expected_cost', sa.Numeric(18, 4), server_default='0.0000', nullable=False),
        sa.Column('excess_cost', sa.Numeric(18, 4), server_default='0.0000', nullable=False),
        sa.Column('percentage_deviation', sa.Numeric(8, 2), server_default='0.00', nullable=False),
        sa.Column('status', sa.String(32), server_default='OPEN', nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('account_id', sa.String(64), nullable=False),
        sa.Column('service_name', sa.String(128), nullable=False),
        sa.Column('region', sa.String(64), nullable=False),
        sa.Column('resource_id', sa.String(512), nullable=True),
        sa.Column('acknowledged_by', sa.String(128), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('investigated_by', sa.String(128), nullable=True),
        sa.Column('investigation_notes', sa.Text(), nullable=True),
        sa.Column('ticket_ref', sa.String(128), nullable=True),
        sa.Column('resolved_by', sa.String(128), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('suppressed_by', sa.String(128), nullable=True),
        sa.Column('suppress_reason', sa.Text(), nullable=True),
        sa.Column('suppress_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trigger_count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('first_triggered_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('escalation_level', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_escalated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['alert_rule_id'], ['alert_rules.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['anomaly_id'], ['cost_anomalies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_alert_inst_dedup', 'alert_instances', ['dedup_key'])
    op.create_index('idx_alert_inst_status', 'alert_instances', ['status'])
    op.create_index('idx_alert_inst_severity', 'alert_instances', ['severity'])
    op.create_index('idx_alert_inst_provider', 'alert_instances', ['provider'])
    op.create_index('idx_alert_inst_account', 'alert_instances', ['account_id'])
    op.create_index('idx_alert_inst_anomaly', 'alert_instances', ['anomaly_id'])

    # 3. Create notification_outbox table
    op.create_table(
        'notification_outbox',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('alert_instance_id', sa.Uuid(), nullable=True),
        sa.Column('channel', sa.String(32), nullable=False),
        sa.Column('recipient', sa.String(256), nullable=False),
        sa.Column('subject', sa.String(256), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(32), server_default='PENDING', nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default='5', nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['alert_instance_id'], ['alert_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_outbox_status', 'notification_outbox', ['status'])
    op.create_index('idx_outbox_next_attempt', 'notification_outbox', ['next_attempt_at'])
    op.create_index('idx_outbox_channel', 'notification_outbox', ['channel'])

    # 4. Create notification_delivery_attempts table
    op.create_table(
        'notification_delivery_attempts',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('outbox_id', sa.Uuid(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(32), nullable=False),
        sa.Column('recipient', sa.String(256), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('response_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['outbox_id'], ['notification_outbox.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_attempt_outbox', 'notification_delivery_attempts', ['outbox_id'])

    # 5. Create in_app_notifications table
    op.create_table(
        'in_app_notifications',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('alert_instance_id', sa.Uuid(), nullable=True),
        sa.Column('recipient_user_id', sa.String(128), server_default='ALL', nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(16), server_default='MEDIUM', nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('account_id', sa.String(64), nullable=False),
        sa.Column('service_name', sa.String(128), nullable=False),
        sa.Column('excess_cost', sa.Numeric(18, 4), server_default='0.0000', nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('action_url', sa.String(256), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['alert_instance_id'], ['alert_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_inapp_recipient_read', 'in_app_notifications', ['recipient_user_id', 'is_read'])
    op.create_index('idx_inapp_created', 'in_app_notifications', ['created_at'])

    # 6. Create notification_preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.String(128), nullable=True),
        sa.Column('user_email', sa.String(256), nullable=False),
        sa.Column('enabled_channels', postgresql.JSONB(astext_type=sa.Text()), server_default='["IN_APP", "EMAIL"]', nullable=False),
        sa.Column('min_severity', sa.String(16), server_default='LOW', nullable=False),
        sa.Column('receive_digests', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('digest_frequency', sa.String(16), server_default='DAILY', nullable=False),
        sa.Column('quiet_hours_enabled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('quiet_hours_start_utc', sa.String(8), server_default='22:00', nullable=True),
        sa.Column('quiet_hours_end_utc', sa.String(8), server_default='08:00', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pref_user_email', 'notification_preferences', ['user_email'], unique=True)

    # 7. Create alert_history table
    op.create_table(
        'alert_history',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('alert_instance_id', sa.Uuid(), nullable=False),
        sa.Column('from_status', sa.String(32), nullable=True),
        sa.Column('to_status', sa.String(32), nullable=False),
        sa.Column('actor', sa.String(128), nullable=False),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['alert_instance_id'], ['alert_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_alert_hist_instance', 'alert_history', ['alert_instance_id'])


def downgrade() -> None:
    op.drop_table('alert_history')
    op.drop_table('notification_preferences')
    op.drop_table('in_app_notifications')
    op.drop_table('notification_delivery_attempts')
    op.drop_table('notification_outbox')
    op.drop_table('alert_instances')

    op.drop_index('idx_alert_rule_archived', 'alert_rules')
    op.drop_index('idx_alert_rule_severity', 'alert_rules')
    op.drop_index('idx_alert_rule_account', 'alert_rules')
    op.drop_index('idx_alert_rule_provider', 'alert_rules')

    op.drop_column('alert_rules', 'updated_at')
    op.drop_column('alert_rules', 'updated_by')
    op.drop_column('alert_rules', 'created_by')
    op.drop_column('alert_rules', 'is_archived')
    op.drop_column('alert_rules', 'escalation_policy')
    op.drop_column('alert_rules', 'cooldown_minutes')
    op.drop_column('alert_rules', 'recipients')
    op.drop_column('alert_rules', 'anomaly_category')
    op.drop_column('alert_rules', 'absolute_deviation_threshold')
    op.drop_column('alert_rules', 'percentage_deviation_threshold')
    op.drop_column('alert_rules', 'min_excess_cost')
    op.drop_column('alert_rules', 'min_severity')
    op.drop_column('alert_rules', 'cost_center')
    op.drop_column('alert_rules', 'owner')
    op.drop_column('alert_rules', 'environment')
    op.drop_column('alert_rules', 'service_name')
    op.drop_column('alert_rules', 'region')
    op.drop_column('alert_rules', 'account_id')
    op.drop_column('alert_rules', 'provider')
    op.drop_column('alert_rules', 'description')
