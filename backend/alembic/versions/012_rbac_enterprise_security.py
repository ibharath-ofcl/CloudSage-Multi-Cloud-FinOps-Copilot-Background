"""Add Enterprise RBAC, Multi-Tenancy, Security Monitoring and Audit Hardening

Revision ID: 012_rbac_enterprise_security
Revises: 011_advanced_anomaly_investigation
Create Date: 2026-11-09 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '012_rbac_enterprise_security'
down_revision: Union[str, None] = '011_advanced_anomaly_investigation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # 1. Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('security_policy', JSON_TYPE, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug'),
    )
    op.create_index('ix_tenants_name', 'tenants', ['name'])
    op.create_index('ix_tenants_slug', 'tenants', ['slug'])

    # 2. Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('resource', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('description', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_permissions_name', 'permissions', ['name'])
    op.create_index('ix_permissions_resource', 'permissions', ['resource'])

    # 3. Create roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('display_name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('is_system_role', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_roles_name', 'roles', ['name'])
    op.create_index('ix_roles_tenant_id', 'roles', ['tenant_id'])

    # 4. Create role_permissions association table
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Uuid(), nullable=False),
        sa.Column('permission_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id'),
    )

    # 5. Alter users table
    op.add_column('users', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('is_locked', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_users_tenant_id', 'users', 'tenants', ['tenant_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])

    # 6. Create user_role_mappings table
    op.create_table(
        'user_role_mappings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role_id', sa.Uuid(), nullable=False),
        sa.Column('assigned_by', sa.String(length=256), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_user_role_unique', 'user_role_mappings', ['user_id', 'role_id'], unique=True)

    # 7. Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('token_jti', sa.String(length=64), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=64), nullable=True),
        sa.Column('client_ip', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=16), server_default='ACTIVE', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_by', sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_jti'),
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_status', 'user_sessions', ['status'])
    op.create_index('ix_user_sessions_refresh_hash', 'user_sessions', ['refresh_token_hash'])

    # 8. Create approval_requests table
    op.create_table(
        'approval_requests',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('requester_id', sa.Uuid(), nullable=False),
        sa.Column('requester_email', sa.String(length=256), nullable=False),
        sa.Column('action_type', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=False),
        sa.Column('resource_id', sa.String(length=512), nullable=False),
        sa.Column('requested_payload', JSON_TYPE, nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
        sa.Column('approver_id', sa.Uuid(), nullable=True),
        sa.Column('approver_email', sa.String(length=256), nullable=True),
        sa.Column('decision_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_approval_requests_status', 'approval_requests', ['status'])
    op.create_index('ix_approval_requests_action_type', 'approval_requests', ['action_type'])
    op.create_index('ix_approval_requests_requester_id', 'approval_requests', ['requester_id'])

    # 9. Create security_events table
    op.create_table(
        'security_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('user_email', sa.String(length=256), nullable=True),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=16), server_default='MEDIUM', nullable=False),
        sa.Column('source_ip', sa.String(length=64), nullable=True),
        sa.Column('endpoint', sa.String(length=256), nullable=True),
        sa.Column('details', JSON_TYPE, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_sec_event_type_time', 'security_events', ['event_type', 'timestamp'])
    op.create_index('idx_sec_event_ip_time', 'security_events', ['source_ip', 'timestamp'])

    # 10. Create audit_integrity_checkpoints table
    op.create_table(
        'audit_integrity_checkpoints',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('last_audit_id', sa.Uuid(), nullable=False),
        sa.Column('cumulative_hash', sa.String(length=64), nullable=False),
        sa.Column('record_count', sa.Integer(), nullable=False),
        sa.Column('verified_by', sa.String(length=256), nullable=False),
        sa.Column('is_valid', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 11. Alter audit_logs table
    op.add_column('audit_logs', sa.Column('tenant_id', sa.Uuid(), nullable=True))
    op.add_column('audit_logs', sa.Column('previous_hash', sa.String(length=64), nullable=True))
    op.add_column('audit_logs', sa.Column('record_hash', sa.String(length=64), nullable=True))
    op.create_foreign_key('fk_audit_logs_tenant_id', 'audit_logs', 'tenants', ['tenant_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])
    op.create_index('ix_audit_logs_record_hash', 'audit_logs', ['record_hash'])


def downgrade() -> None:
    op.drop_constraint('fk_audit_logs_tenant_id', 'audit_logs', type_='foreignkey')
    op.drop_index('ix_audit_logs_record_hash', table_name='audit_logs')
    op.drop_index('ix_audit_logs_tenant_id', table_name='audit_logs')
    op.drop_column('audit_logs', 'record_hash')
    op.drop_column('audit_logs', 'previous_hash')
    op.drop_column('audit_logs', 'tenant_id')

    op.drop_table('audit_integrity_checkpoints')
    op.drop_table('security_events')
    op.drop_table('approval_requests')
    op.drop_table('user_sessions')
    op.drop_table('user_role_mappings')

    op.drop_constraint('fk_users_tenant_id', 'users', type_='foreignkey')
    op.drop_index('ix_users_tenant_id', table_name='users')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'is_locked')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'tenant_id')

    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
    op.drop_table('tenants')

