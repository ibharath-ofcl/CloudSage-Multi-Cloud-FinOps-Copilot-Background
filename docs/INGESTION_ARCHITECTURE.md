# Multi-Cloud Billing Ingestion Engine Architecture

## 1. Executive Summary

The CloudSage Multi-Cloud Ingestion Engine provides enterprise-grade, idempotent, multi-cloud billing and usage data ingestion from Amazon Web Services (AWS), Microsoft Azure, and Google Cloud Platform (GCP).

The ingestion engine transforms heterogeneous, provider-specific billing formats (AWS Cost and Usage Reports, Azure Cost Management Exports, and GCP BigQuery Billing Exports) into CloudSage's canonical, FinOps Open Cost and Usage Specification (FOCUS 1.0) compatible `BillingRecord` data model.

```
                              ┌──────────────────────────────────────────────┐
                              │           Cloud Billing Sources              │
                              │  - AWS Cost & Usage Reports (CUR CSV)        │
                              │  - Azure Cost Management Exports (CSV)       │
                              │  - GCP BigQuery Billing Exports (JSON/CSV)   │
                              └──────────────────────┬───────────────────────┘
                                                     │
                                                     ▼
                              ┌──────────────────────────────────────────────┐
                              │            API / Batch Worker Entry          │
                              │  - POST /api/v1/ingestion/upload/{provider}  │
                              │  - Celery Worker / Scheduled Poller          │
                              └──────────────────────┬───────────────────────┘
                                                     │
                                                     ▼
                              ┌──────────────────────────────────────────────┐
                              │            Provider Registry                 │
                              │  - Format auto-detection                     │
                              │  - Adapter resolution (AWS, Azure, GCP)      │
                              └──────────────────────┬───────────────────────┘
                                                     │
                                                     ▼
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   Ingestion Pipeline Engine                                       │
 │                                                                                                   │
 │  1. IngestionTracker: Initialize IngestionRun (status=PROCESSING, batch UUID)                     │
 │  2. Provider Parser: Streaming generator yielding RawBillingRecord objects                        │
 │  3. Provider Validator: Structural validation & anomaly quarantine                                │
 │  4. Data Normalizer: FOCUS 1.0 taxonomy, UTC timestamps, Currency (USD), Tag normalization       │
 │  5. DeduplicationService: SHA-256 composite idempotency fingerprint check against database        │
 │  6. Bulk Database Insertion: SQLAlchemy Core bulk insert into PostgreSQL billing_records          │
 │  7. CloudResource Sync: Upsert cloud_resources metadata and link to billing partitions           │
 │  8. Run Finalization: Update IngestionRun metrics (records, costs, durations, status)             │
 └───────────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                                     │
                                                     ▼
                              ┌──────────────────────────────────────────────┐
                              │         PostgreSQL Partitioned Store         │
                              │  - billing_records (RANGE(usage_start_time)) │
                              │  - cloud_resources                           │
                              │  - ingestion_runs                            │
                              └──────────────────────────────────────────────┘
```

---

## 2. Core Architectural Principles

1. **Strict Advisory Boundary**: The ingestion engine is read-only with respect to cloud infrastructure. It ingests cost and telemetry records without performing or triggering destructive infrastructure actions.
2. **Decimal Financial Arithmetic**: All financial calculations use arbitrary-precision Python `Decimal` objects and database `NUMERIC(18, 4)`. Floating-point arithmetic is strictly prohibited in financial paths to prevent fractional cent drift.
3. **Canonical FOCUS 1.0 Schema Target**: Every cloud record is mapped to a standardized, unified schema compatible with FinOps Foundation standards.
4. **Idempotence & Re-run Safety**: Re-ingesting identical files or overlapping time windows produces zero duplicate billing rows.
5. **Partial Success Resilience**: Malformed individual lines are quarantined in run error logs; valid rows in the batch are committed without aborting the entire dataset.
6. **Streaming & Memory Efficiency**: Large datasets are read line-by-line using Python generator iterators to maintain bounded memory consumption.

---

## 3. Adapter Pattern Implementation

The ingestion engine utilizes an object-oriented **Adapter Pattern** with a central **Provider Registry**.

### 3.1 Base Classes (`backend/app/ingestion/base.py`)

- **`BaseBillingAdapter`**: Abstract base class defining:
  - `parse_stream(stream)`: Reads byte or text streams and yields raw provider records.
  - `validate_record(raw)`: Checks required fields and data integrity.
  - `normalize_record(raw)`: Transforms provider data into `CanonicalBillingRecord`.
  - `process_file(file_path)`: High-level orchestration for file inputs.
- **`RawBillingRecord`**: Pydantic model encapsulating raw dictionary payloads and source file metadata.
- **`CanonicalBillingRecord`**: Pydantic representation matching the PostgreSQL `BillingRecord` schema.

### 3.2 Provider Registry (`backend/app/ingestion/registry.py`)

The `IngestionRegistry` maintains a thread-safe registry of provider adapters. It supports:
- Adapter registration (`register_adapter(provider, adapter_class)`).
- Adapter retrieval (`get_adapter(provider)`).
- Automatic file format and provider auto-detection (`detect_provider_and_adapter(file_path)`).

---

## 4. Idempotency & Deduplication Strategy

Cloud billing systems frequently emit overlapping or revised reports. Without deduplication, re-running ingestion inflates reported expenditure.

### 4.1 SHA-256 Composite Fingerprint

Every canonical record generates a deterministic 64-character SHA-256 fingerprint from immutable business keys:

$$\text{Fingerprint} = \text{SHA256}( \text{provider} \parallel \text{account\_id} \parallel \text{resource\_id} \parallel \text{start\_time} \parallel \text{end\_time} \parallel \text{cost} \parallel \text{currency} )$$

Fields incorporated into the hash:
- `cloud_provider`: e.g., `"AWS"`, `"AZURE"`, `"GCP"`
- `account_id` / `subscription_id` / `project_id`: Cloud billing boundary
- `resource_id`: Cloud resource ARN, resource ID, or synthetic identifier
- `usage_start_time`: ISO 8601 formatted UTC timestamp
- `usage_end_time`: ISO 8601 formatted UTC timestamp
- `cost_amount`: Normalized numeric cost as string
- `currency`: Normalized currency code (e.g., `"USD"`)

### 4.2 In-Flight and Database-Level Deduplication

1. **In-Flight Batch Cache**: Within an ongoing ingestion execution, an in-memory hash set tracks fingerprints to eliminate internal duplicates.
2. **Database Lookup**: The `DeduplicationService` inspects the target partition table using an indexed fingerprint search (`idx_billing_records_fingerprint`).
3. **Database Unique Constraint**: A table-level uniqueness constraint (`uq_billing_records_fingerprint`) ensures absolute isolation even under concurrent ingestion workers.

---

## 5. Error Handling, Validation, and Dead-Letter Quarantine

Ingestion pipelines handle imperfect data gracefully without failing the entire batch:

1. **Syntax and File Corruptions**: Handled during stream parsing. If a line cannot be parsed as valid CSV or JSON, a `ValidationErrorDetail` is appended to the `IngestionRun` errors log, and the stream advances to the next record.
2. **Validation Rules**:
   - `cost_amount >= 0`: Negative costs (unless classified as official credits) raise validation errors.
   - `usage_end_time >= usage_start_time`: Inverted time intervals are rejected.
   - Non-empty `cloud_provider`, `account_id`, and `service_name`.
3. **Quarantine Logging**: All rejected records are recorded with line index, raw snippet, error message, and error category inside the `IngestionRun.error_details` JSON column.
4. **Run Status Transitions**:
   - `COMPLETED`: 100% of records successfully validated and ingested.
   - `PARTIAL_SUCCESS`: At least one record succeeded and at least one record failed.
   - `FAILED`: Critical failure prevented parsing or database persistence (zero records committed).

---

## 6. Streaming vs. Batch Processing Tradeoffs

| Architecture Dimension | CloudSage Approach (Hybrid Streaming-Batch) | Pure In-Memory Batching | Pure Real-Time Streaming (Kafka) |
| :--- | :--- | :--- | :--- |
| **Memory Footprint** | Bounded: $O(\text{chunk\_size})$ (default 1,000 records) | High: $O(N)$ for entire CSV (GBs) | Minimal: $O(1)$ per message |
| **Ingestion Latency** | Low: Near real-time file upload processing | Medium: Delayed until full file read | Sub-second real-time |
| **Database Throughput** | High: Bulk insert via SQLAlchemy Core `bulk_insert_mappings` | High: Single massive batch insert | Lower: High per-row insert overhead |
| **Operational Overhead** | Low: Stateless REST / Celery worker | Low: Simple monolithic scripts | High: Requires Kafka/Pulsar cluster |
| **Suitability for FinOps** | **Optimal**: Cloud billing reports are emitted hourly or daily in files | Inflexible for large multi-GB CURs | Unnecessary complexity for daily billing |

CloudSage balances memory safety with database efficiency by:
- Streaming lines lazily from disk or network byte streams.
- Accumulating micro-batches (chunks of 1,000 records).
- Bulk-inserting chunks into PostgreSQL using parameterized multi-row statements.

---

## 7. CloudResource Entity Synchronization

Whenever a billing line contains a `resource_id`, the ingestion engine automatically synchronizes the `cloud_resources` table:
- Computes canonical resource identifiers and resource names.
- Maps service names to primary resource types (`Compute Instance`, `Storage Volume`, etc.).
- Updates resource status to `ACTIVE`.
- Merges tags and ownership metadata.
- Sets `last_seen_time` to `usage_end_time`.
- Associates the resource foreign key (`resource_uuid`) back to the `billing_records` entry.
