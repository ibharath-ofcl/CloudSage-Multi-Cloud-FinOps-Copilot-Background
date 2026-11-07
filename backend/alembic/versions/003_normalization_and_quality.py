"""Add Normalization, Exchange Rates, Catalog Mappings, and Quality Tables

Revision ID: 003_normalization_and_quality
Revises: 002_ingestion_runs
Create Date: 2026-11-07 13:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003_normalization_and_quality'
down_revision: Union[str, None] = '002_ingestion_runs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. exchange_rates table
    op.create_table(
        'exchange_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('currency_code', sa.String(3), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('rate_to_usd', sa.Numeric(18, 6), nullable=False),
        sa.Column('source', sa.String(64), nullable=False, server_default='ECB_REFERENCE'),
        sa.Column('is_interpolated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_exchange_rates_curr_date', 'exchange_rates', ['currency_code', 'effective_date'], unique=True)

    # 2. sku_catalog_mappings table
    op.create_table(
        'sku_catalog_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('service_code', sa.String(128), nullable=False),
        sa.Column('sku_id', sa.String(256), nullable=True),
        sa.Column('canonical_category', sa.String(32), nullable=False),
        sa.Column('service_family', sa.String(64), nullable=False),
        sa.Column('resource_type', sa.String(64), nullable=False),
        sa.Column('normalized_unit', sa.String(32), nullable=False),
        sa.Column('pricing_model_default', sa.String(32), nullable=True),
        sa.Column('confidence', sa.Numeric(5, 4), nullable=False, server_default='1.0000'),
        sa.Column('provenance', sa.String(32), nullable=False, server_default='SYSTEM_CATALOG'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_sku_catalog_lookup', 'sku_catalog_mappings', ['provider', 'service_code', 'sku_id'])

    # 3. normalization_runs table
    op.create_table(
        'normalization_runs',
        sa.Column('run_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='PENDING'),
        sa.Column('normalization_version', sa.String(16), nullable=False, server_default='1.0.0'),
        sa.Column('mapping_version', sa.String(16), nullable=False, server_default='2026.11'),
        sa.Column('total_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('warnings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_quality_score', sa.Numeric(5, 2), nullable=False, server_default='100.00'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=False, server_default='[]'),
    )
    op.create_index('idx_norm_status', 'normalization_runs', ['status'])

    # 4. data_quality_reports table
    op.create_table(
        'data_quality_reports',
        sa.Column('report_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('provider', sa.String(16), nullable=True),
        sa.Column('overall_score', sa.Numeric(5, 2), nullable=False, server_default='100.00'),
        sa.Column('total_records_evaluated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('critical_findings', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('high_findings', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('medium_findings', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('low_findings', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('informational_findings', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('findings_summary', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_dq_provider', 'data_quality_reports', ['provider'])


def downgrade() -> None:
    op.drop_table('data_quality_reports')
    op.drop_table('normalization_runs')
    op.drop_table('sku_catalog_mappings')
    op.drop_table('exchange_rates')
