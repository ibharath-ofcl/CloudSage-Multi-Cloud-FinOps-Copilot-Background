"""
CloudSage Database Metadata & Schema Verification Unit Tests.
Asserts that all 10 canonical tables, foreign keys, indexes, and precision constraints exist in metadata.
"""

from decimal import Decimal
import pytest
from sqlalchemy import Numeric, Float
from backend.app.core.database import Base
from backend.app.models import (
    BillingRecord,
    CloudResource,
    ResourceMetric,
    WasteDetection,
    Recommendation,
    CostAnomaly,
    User,
    AuditLog,
    AlertRule,
    NotificationLog,
)


EXPECTED_TABLES = {
    "billing_records",
    "cloud_resources",
    "resource_metrics",
    "waste_detections",
    "recommendations",
    "cost_anomalies",
    "users",
    "audit_logs",
    "alert_rules",
    "notification_logs",
}

FINANCIAL_MONETARY_COLUMNS = {
    "unblended_cost",
    "blended_cost",
    "list_cost",
    "monthly_cost",
    "actual_cost",
    "expected_cost",
    "baseline_mean",
    "baseline_stddev",
    "estimated_monthly_waste",
    "estimated_monthly_savings",
    "estimated_annual_savings",
    "threshold_value",
}


def test_all_tables_registered_in_metadata():
    """Verify that all 10 required database tables are declared in Base.metadata."""
    registered_tables = set(Base.metadata.tables.keys())
    assert EXPECTED_TABLES.issubset(registered_tables), (
        f"Missing tables: {EXPECTED_TABLES - registered_tables}"
    )


def test_no_float_types_in_financial_columns():
    """
    CRITICAL FINOPS RULE: Verify that zero financial or quantity columns use Float.
    All monetary and usage metrics must strictly use Numeric (arbitrary precision Decimal).
    """
    for table_name, table in Base.metadata.tables.items():
        for column in table.columns:
            # Check for forbidden Float types across all columns in all tables
            assert not isinstance(column.type, Float), (
                f"Forbidden Float column found: {table_name}.{column.name}! Must be Numeric."
            )
            # Specifically verify financial columns enforce Numeric precision
            if column.name in FINANCIAL_MONETARY_COLUMNS:
                assert isinstance(column.type, Numeric), (
                    f"Financial column {table_name}.{column.name} is not Numeric!"
                )
                assert column.type.precision == 18, (
                    f"Financial column {table_name}.{column.name} does not have precision 18!"
                )
                assert column.type.scale == 4, (
                    f"Financial column {table_name}.{column.name} does not have scale 4!"
                )


def test_foreign_key_integrity():
    """Verify foreign key relations across child entities."""
    metrics_table = Base.metadata.tables["resource_metrics"]
    fk_targets = [fk.target_fullname for fk in metrics_table.foreign_keys]
    assert "cloud_resources.resource_id" in fk_targets

    waste_table = Base.metadata.tables["waste_detections"]
    fk_targets = [fk.target_fullname for fk in waste_table.foreign_keys]
    assert "cloud_resources.resource_id" in fk_targets

    rec_table = Base.metadata.tables["recommendations"]
    fk_targets = [fk.target_fullname for fk in rec_table.foreign_keys]
    assert "cloud_resources.resource_id" in fk_targets
    assert "waste_detections.id" in fk_targets


def test_indexing_registration():
    """Verify critical indexes are registered in metadata."""
    billing_table = Base.metadata.tables["billing_records"]
    index_names = {idx.name for idx in billing_table.indexes}
    assert "idx_billing_prov_srv_time" in index_names
    assert "idx_billing_res_time" in index_names

    rec_table = Base.metadata.tables["recommendations"]
    index_names = {idx.name for idx in rec_table.indexes}
    assert "idx_rec_status_priority" in index_names
    assert "idx_rec_prov_savings" in index_names
