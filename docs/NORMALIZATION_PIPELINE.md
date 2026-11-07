# Unified Normalization & FOCUS Pipeline Architecture

## 1. Executive Summary

The CloudSage **Unified Normalization Pipeline** coordinates service catalog lookups, historical foreign exchange conversions, tag governance, FOCUS 1.0 validation, and data quality scoring into a repeatable 15-step workflow.

- **Module**: `backend/app/normalization/pipeline.py`
- **Orchestrator**: `NormalizationPipeline`
- **Audit Table**: `normalization_runs`
- **Normalization Version**: `1.0.0`
- **Taxonomy Mapping Version**: `2026.11`

---

## 2. The 15-Step Normalization Workflow

The pipeline operates across 15 disciplined stages:

```
[Step 01] Receive validated raw records from Ingestion Engine or DB
   │
[Step 02] Identify cloud provider (AWS, Azure, GCP) & original currency
   │
[Step 03] Validate structural attributes and timestamp boundaries
   │
[Step 04] Retrieve SKU and service catalog definitions (Cache -> DB -> System)
   │
[Step 05] Normalize service category, family, and standard usage units
   │
[Step 06] Standardize timestamps and charge periods to ISO-8601 UTC
   │
[Step 07] Sanitize tags, strip prefixes, extract FinOps ownership metadata
   │
[Step 08] Compute tag quality and hygiene compliance score (0 - 100%)
   │
[Step 09] Apply date-aware historical foreign exchange conversion into USD
   │
[Step 10] Map record to canonical FOCUS 1.0 Pydantic schema
   │
[Step 11] Run automated FOCUS 1.0 specification validation suite
   │
[Step 12] Run Data Quality Engine (Rules DQ-001 through DQ-014)
   │
[Step 13] Persist / update record in partitioned PostgreSQL billing_records
   │
[Step 14] Synchronize associated CloudResource metadata and tags
   │
[Step 15] Finalize NormalizationRun audit log and data quality summary
```

---

## 3. Reprocessing & Backfill Architecture

When new exchange rates are published or service catalog mapping rules are added, historical billing data must be reprocessed to reflect the latest taxonomy without inflating expenditure.

### Idempotency Guarantee: In-Place Updates
- Reprocessing queries existing records in batches (default: 500 records).
- Records are updated **in-place** within the database partition (`billing_records`).
- No new primary keys (`record_id`) or duplicate rows are generated.
- The record's `raw_metadata` captures `_reprocessed_at` and `_normalization_version`.

```python
from backend.app.normalization.pipeline import NormalizationPipeline

pipeline = NormalizationPipeline(db=db_session)

# Reprocess all AWS records for November 2026
run = pipeline.reprocess_existing_records(
    provider="AWS",
    start_date=date(2026, 11, 1),
    end_date=date(2026, 11, 30),
    batch_size=500
)
print(f"Run {run.run_id} completed: {run.successful_records} updated, 0 duplicates.")
```

---

## 4. Background Celery Task Integration

Large multi-million row historical re-normalizations run asynchronously in the background via Celery:

```python
from backend.app.ingestion.tasks import reprocess_normalization_task

# Enqueue background task
task = reprocess_normalization_task.delay(provider_str="AWS", batch_size=1000)
```

---

## 5. Performance and Memory Safety

1. **Bounded Memory**: Iterates using cursor-based batch chunking ($O(\text{batch\_size})$).
2. **Caching**: Exchange rates and catalog lookups are cached in memory to eliminate redundant database queries.
3. **Bulk Commits**: Database transactions commit per micro-batch (500 records) to maintain small transaction logs.
