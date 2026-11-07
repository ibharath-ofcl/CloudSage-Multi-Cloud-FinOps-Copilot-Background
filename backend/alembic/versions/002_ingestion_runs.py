"""Add Ingestion Runs Table

Revision ID: 002_ingestion_runs
Revises: 001_initial_schema
Create Date: 2026-11-07 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_ingestion_runs'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ingestion_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('source_filename', sa.String(256), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='RUNNING'),
        sa.Column('total_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ingested_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicate_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_records', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cost', sa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('error_summary', postgresql.JSONB(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('idx_ingest_prov_status', 'ingestion_runs', ['provider', 'status'])
    op.create_index('idx_ingest_started_at', 'ingestion_runs', ['started_at'])


def downgrade() -> None:
    op.drop_table('ingestion_runs')
