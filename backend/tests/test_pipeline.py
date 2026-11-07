"""
CloudSage Ingestion Pipeline Integration Tests.
Category E: End-to-end pipeline execution, partial success, duplicate prevention, and run tracking.
"""

from decimal import Decimal
import io
import pytest
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.models.billing import BillingRecord
from backend.app.models.ingestion import IngestionRun
from backend.app.models.resource import CloudResource


def test_pipeline_complete_ingestion(db_session):
    csv_data = """identity/LineItemId,bill/PayerAccountId,lineItem/UsageAccountId,lineItem/LineItemType,lineItem/UsageStartDate,lineItem/UsageEndDate,lineItem/ProductCode,lineItem/UsageAmount,pricing/unit,lineItem/UnblendedCost,lineItem/CurrencyCode,lineItem/ResourceId,product/region,resourceTags/user:Owner,resourceTags/user:Environment
pipe-001,112233445566,112233445566,Usage,2026-11-01T00:00:00Z,2026-11-01T01:00:00Z,AmazonEC2,1.0,HOURS,0.1920,USD,arn:aws:ec2:us-east-1:112233445566:instance/i-pipe-01,us-east-1,data-squad,production
pipe-002,112233445566,112233445566,Usage,2026-11-01T00:00:00Z,2026-11-01T01:00:00Z,AmazonS3,100.0,GB,0.0230,USD,arn:aws:s3:::enterprise-data-lake,us-east-1,data-squad,production
"""
    pipeline = IngestionPipeline(db_session)
    stream = io.StringIO(csv_data)
    result = pipeline.execute(stream_or_path=stream, source_name="test_pipeline.csv", provider=CloudProvider.AWS)

    assert result.total_records == 2
    assert result.ingested_records == 2
    assert result.skipped_duplicates == 0
    assert result.failed_records == 0
    assert result.total_cost_usd == Decimal("0.2150")

    # Verify DB persistence
    records = db_session.query(BillingRecord).all()
    assert len(records) == 2

    # Verify CloudResource creation
    resources = db_session.query(CloudResource).all()
    assert len(resources) == 2

    # Verify IngestionRun tracking
    run = db_session.query(IngestionRun).first()
    assert run is not None
    assert run.status == "COMPLETED"
    assert run.ingested_records == 2
    assert run.total_cost == Decimal("0.2150")


def test_pipeline_duplicate_prevention_on_repeated_ingest(db_session):
    """
    CRITICAL IDEMPOTENCY TEST:
    Ingesting the exact same billing file twice MUST result in 0 new records on the second run,
    skipping all records as duplicates without inflating total expenditure.
    """
    csv_data = """identity/LineItemId,bill/PayerAccountId,lineItem/UsageAccountId,lineItem/LineItemType,lineItem/UsageStartDate,lineItem/UsageEndDate,lineItem/ProductCode,lineItem/UsageAmount,pricing/unit,lineItem/UnblendedCost,lineItem/CurrencyCode,lineItem/ResourceId,product/region
dup-001,112233445566,112233445566,Usage,2026-11-01T00:00:00Z,2026-11-01T01:00:00Z,AmazonEC2,1.0,HOURS,0.5000,USD,arn:aws:ec2:us-east-1:112233445566:instance/i-dup,us-east-1
"""
    pipeline = IngestionPipeline(db_session)

    # First run
    stream1 = io.StringIO(csv_data)
    res1 = pipeline.execute(stream_or_path=stream1, source_name="dup_test.csv", provider=CloudProvider.AWS)
    assert res1.ingested_records == 1
    assert res1.skipped_duplicates == 0

    # Second run (exact duplicate)
    stream2 = io.StringIO(csv_data)
    res2 = pipeline.execute(stream_or_path=stream2, source_name="dup_test.csv", provider=CloudProvider.AWS)
    assert res2.ingested_records == 0
    assert res2.skipped_duplicates == 1

    # Total in DB must remain 1
    total_in_db = db_session.query(BillingRecord).count()
    assert total_in_db == 1


def test_pipeline_partial_success_with_malformed_record(db_session):
    """
    Verifies that an invalid record does not abort valid records.
    Valid records are committed, invalid records are reported with line details.
    """
    csv_data = """identity/LineItemId,bill/PayerAccountId,lineItem/UsageAccountId,lineItem/LineItemType,lineItem/UsageStartDate,lineItem/UsageEndDate,lineItem/ProductCode,lineItem/UsageAmount,pricing/unit,lineItem/UnblendedCost,lineItem/CurrencyCode,lineItem/ResourceId,product/region
good-001,112233445566,112233445566,Usage,2026-11-01T00:00:00Z,2026-11-01T01:00:00Z,AmazonEC2,1.0,HOURS,0.2500,USD,arn:aws:ec2:us-east-1:112233445566:instance/i-good,us-east-1
bad-002,112233445566,112233445566,Usage,2026-11-01T05:00:00Z,2026-11-01T01:00:00Z,AmazonEC2,1.0,HOURS,0.2500,USD,arn:aws:ec2:us-east-1:112233445566:instance/i-bad,us-east-1
good-003,112233445566,112233445566,Usage,2026-11-01T01:00:00Z,2026-11-01T02:00:00Z,AmazonEC2,1.0,HOURS,0.2500,USD,arn:aws:ec2:us-east-1:112233445566:instance/i-good-2,us-east-1
"""
    # Notice bad-002 has usage_end_time (01:00) before usage_start_time (05:00), which violates chronological order!
    pipeline = IngestionPipeline(db_session)
    stream = io.StringIO(csv_data)
    result = pipeline.execute(stream_or_path=stream, source_name="partial_test.csv", provider=CloudProvider.AWS)

    assert result.total_records == 3
    assert result.ingested_records == 2
    assert result.failed_records == 1
    assert len(result.errors) == 1
    assert "Line 2" in result.errors[0]

    # Verify run status is PARTIAL_SUCCESS
    run = db_session.query(IngestionRun).filter(IngestionRun.source_filename == "partial_test.csv").first()
    assert run.status == "PARTIAL_SUCCESS"
    assert run.ingested_records == 2
    assert run.failed_records == 1
