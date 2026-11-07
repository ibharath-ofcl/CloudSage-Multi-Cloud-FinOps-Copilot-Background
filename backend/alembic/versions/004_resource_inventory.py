"""Add Resource Relationships, Inventory Sync Runs, and Inventory Quality Tables

Revision ID: 004_resource_inventory
Revises: 003_normalization_and_quality
Create Date: 2026-11-07 13:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '004_resource_inventory'
down_revision: Union[str, None] = '003_normalization_and_quality'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns to cloud_resources
    op.add_column('cloud_resources', sa.Column('zone', sa.String(64), nullable=True))
    op.add_column('cloud_resources', sa.Column('department', sa.String(128), nullable=True))
    op.add_column('cloud_resources', sa.Column('project', sa.String(128), nullable=True))
    op.add_column('cloud_resources', sa.Column('raw_tags', postgresql.JSONB(), nullable=True, server_default='{}'))
    op.add_column('cloud_resources', sa.Column('tag_quality_score', sa.Numeric(5, 2), nullable=False, server_default='0.00'))
    op.add_column('cloud_resources', sa.Column('resource_created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('cloud_resources', sa.Column('last_inventory_sync_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('cloud_resources', sa.Column('discovery_source', sa.String(32), nullable=False, server_default='BILLING_INFERRED'))
    op.add_column('cloud_resources', sa.Column('discovery_status', sa.String(32), nullable=False, server_default='CONFIRMED'))
    op.add_column('cloud_resources', sa.Column('resource_metadata', postgresql.JSONB(), nullable=True, server_default='{}'))
    op.add_column('cloud_resources', sa.Column('metadata_version', sa.String(16), nullable=False, server_default='1.0'))

    op.create_index('idx_res_prov_status', 'cloud_resources', ['provider', 'status'])
    op.create_index('idx_res_account_res', 'cloud_resources', ['account_id', 'resource_id'])
    op.create_index('idx_res_project', 'cloud_resources', ['project'])

    # 2. Create resource_relationships table
    op.create_table(
        'resource_relationships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_resource_id', sa.String(512), sa.ForeignKey('cloud_resources.resource_id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_resource_id', sa.String(512), nullable=False),
        sa.Column('relationship_type', sa.String(64), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('discovery_source', sa.String(32), nullable=False, server_default='INVENTORY_DISCOVERY'),
        sa.Column('confidence', sa.Numeric(5, 4), nullable=False, server_default='1.0000'),
        sa.Column('first_observed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_observed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('relationship_metadata', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.UniqueConstraint('source_resource_id', 'target_resource_id', 'relationship_type', name='uq_resource_relationships'),
    )
    op.create_index('idx_rel_src_tgt', 'resource_relationships', ['source_resource_id', 'target_resource_id'])
    op.create_index('idx_rel_provider_type', 'resource_relationships', ['provider', 'relationship_type'])

    # 3. Create inventory_sync_runs table
    op.create_table(
        'inventory_sync_runs',
        sa.Column('run_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('discovery_mode', sa.String(32), nullable=False, server_default='EXPORT_BASED'),
        sa.Column('status', sa.String(32), nullable=False, server_default='PENDING'),
        sa.Column('source_identifier', sa.String(256), nullable=True),
        sa.Column('total_discovered', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('new_resources', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('updated_resources', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('stale_resources', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('relationships_discovered', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=False, server_default='[]'),
    )
    op.create_index('idx_sync_prov_status', 'inventory_sync_runs', ['provider', 'status'])

    # 4. Create inventory_quality_reports table
    op.create_table(
        'inventory_quality_reports',
        sa.Column('report_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('sync_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('provider', sa.String(16), nullable=True),
        sa.Column('total_resources', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completeness_score', sa.Numeric(5, 2), nullable=False, server_default='100.00'),
        sa.Column('tag_completeness_score', sa.Numeric(5, 2), nullable=False, server_default='100.00'),
        sa.Column('inventory_confidence', sa.Numeric(5, 4), nullable=False, server_default='1.0000'),
        sa.Column('findings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('critical_findings', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('high_findings', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('medium_findings', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('low_findings', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('findings_summary', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_inv_qual_prov', 'inventory_quality_reports', ['provider'])


def downgrade() -> None:
    op.drop_table('inventory_quality_reports')
    op.drop_table('inventory_sync_runs')
    op.drop_table('resource_relationships')
    op.drop_column('cloud_resources', 'metadata_version')
    op.drop_column('cloud_resources', 'resource_metadata')
    op.drop_column('cloud_resources', 'discovery_status')
    op.drop_column('cloud_resources', 'discovery_source')
    op.drop_column('cloud_resources', 'last_inventory_sync_at')
    op.drop_column('cloud_resources', 'resource_created_at')
    op.drop_column('cloud_resources', 'tag_quality_score')
    op.drop_column('cloud_resources', 'raw_tags')
    op.drop_column('cloud_resources', 'project')
    op.drop_column('cloud_resources', 'department')
    op.drop_column('cloud_resources', 'zone')
