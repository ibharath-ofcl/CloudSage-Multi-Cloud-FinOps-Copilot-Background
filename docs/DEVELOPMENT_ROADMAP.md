# CloudSage: 15-Stage Enterprise Development Roadmap

## 1. Roadmap Architecture and Phasing Strategy

CloudSage is developed across 15 structured, modular stages to ensure enterprise-grade software quality, strict security controls, financial accuracy, and seamless pair-programming progression.

```
PHASE 1: FOUNDATION & DATA ARCHITECTURE (Stages 1 - 4)
  Stage 1: Requirement Analysis & Project Foundation [COMPLETED]
  Stage 2: Core Data Models & Database Schema Architecture [COMPLETED]
  Stage 3: Multi-Cloud Ingestion Engine [COMPLETED]
  Stage 4: Unified Data Normalization & FOCUS Pipeline [COMPLETED]

PHASE 2: RESOURCE INTELLIGENCE & ANALYTICAL ENGINES (Stages 5 - 7)
  Stage 5: Multi-Cloud Resource Discovery & Inventory Intelligence [COMPLETED]
  Stage 6: Cloud Waste Detection Engine [COMPLETED]
  Stage 7: Cost Anomaly Detection Engine [COMPLETED]

PHASE 3: ADVISORY RECOMMENDATIONS & AI INTELLIGENCE (Stages 8 - 9)
  Stage 8: Advisory Recommendation Engine & Savings Optimization [COMPLETED]
  Stage 9: AI-Powered Multi-Cloud FinOps Copilot [COMPLETED]

PHASE 4: FRONTEND INTERFACE & DASHBOARDS (Stages 10 - 12)
  Stage 10: Interactive FinOps Dashboards & Data Visualization
  Stage 11: Enterprise Recommendation & Waste Management UI
  Stage 12: Anomaly Investigation & Root-Cause Analysis UI

PHASE 5: SECURITY, NOTIFICATIONS & PRODUCTION READINESS (Stages 13 - 15)
  Stage 13: Anomaly Detection & Alerts Notification Hub
  Stage 14: Role-Based Access Control (RBAC), Audit Logging & Security Hardening
  Stage 15: Production Containerization, CI/CD, Deployment & Benchmark Test Suite
```

---

## 2. Detailed Breakdown of the 15 Stages

### Stage 1: Requirement Analysis & Project Foundation
- **Focus**: Requirements engineering, architectural modeling, safety policies, and project documentation.
- **Key Deliverables**:
  - Comprehensive documentation repository (`docs/`).
  - System architecture and data flow diagrams.
  - Technology stack evaluation and architectural refinements.
  - Project `README.md` and `.gitignore` setup.
  - Git repository initialization and `stage-1/project-foundation` branch synchronization.
- **Acceptance Criteria**: All 10 documentation deliverables complete, consistent, syntax-validated, and pushed to GitHub.

---

### Stage 2: Core Data Models & Database Schema Architecture
- **Focus**: Canonical relational data modeling, FOCUS 1.0 schema specification, database migrations, and performance indexing.
- **Key Deliverables**:
  - SQLAlchemy 2.0 async ORM models & Pydantic v2 schemas.
  - Declarative PostgreSQL table partitioning by billing period (`usage_start_time`).
  - GIN indexes for JSONB metadata tags; composite B-Tree and BRIN indexes.
  - Alembic migration scaffolding and initial schema revision scripts.
- **Acceptance Criteria**: Zero floating-point types for currency (`NUMERIC(18, 4)` enforced); migration scripts execute cleanly up and down.

---

### Stage 3: Multi-Cloud Ingestion Engine [COMPLETED]
- **Focus**: Adapters for AWS, Azure, GCP billing exports and local seed datasets.
- **Key Deliverables**:
  - AWS CUR CSV parser & adapter (`backend/app/ingestion/adapters/aws/`).
  - Azure Cost Management export adapter (`backend/app/ingestion/adapters/azure/`).
  - GCP BigQuery Billing JSON/CSV export adapter (`backend/app/ingestion/adapters/gcp/`).
  - Deterministic synthetic dataset generator with 6 seeded FinOps scenarios (`backend/app/ingestion/synthetic/`).
  - Pre-generated sample datasets with 1,200 records (`backend/sample_data/`).
  - SHA-256 idempotency fingerprinting and deduplication service (`DeduplicationService`).
  - Ingestion run tracking with partial success support and quarantined error logs (`IngestionRun`).
  - FastAPI Ingestion endpoints (`/api/v1/ingestion/`) and Celery background task (`ingest_billing_file_task`).
  - Full test suite with 46 passing unit/integration tests (`backend/tests/`).
- **Acceptance Criteria**: Ingestion of multi-cloud sample datasets without duplicate line items or unhandled parsing exceptions (100% verified).

---

### Stage 4: Unified Data Normalization & FOCUS Pipeline [COMPLETED]
- **Focus**: Transforming disparate multi-cloud records into the canonical FinOps schema and FOCUS 1.0 specification.
- **Key Deliverables**:
  - FOCUS 1.0 conformance validation suite & exporter (`backend/app/normalization/focus/`).
  - Historical & dynamic currency normalization service with weekend/holiday rollback (`backend/app/normalization/currency/`).
  - Multi-cloud SKU and service catalog taxonomy with confidence scoring and unknown SKU handling (`backend/app/normalization/catalog/`).
  - Advanced regex tag sanitization, FinOps governance attribute extractor, and hygiene scoring (`backend/app/normalization/tags/`).
  - Reusable 14-rule Data Quality framework with severity tiering and report persistence (`backend/app/normalization/quality/`).
  - 15-step unified normalization pipeline supporting in-place reprocessing without duplicate records (`backend/app/normalization/pipeline.py`).
  - Database models (`ExchangeRate`, `SkuCatalogMapping`, `NormalizationRun`, `DataQualityReport`) and Alembic migration `003_normalization_and_quality.py`.
  - REST API routes (`/api/v1/normalization/`) and Celery background task (`reprocess_normalization_task`).
  - Full test suite with 80 passing unit/integration/regression tests (`backend/tests/`).
- **Acceptance Criteria**: 100% field mapping parity across AWS, Azure, and GCP records into canonical FOCUS 1.0 schema with verified data quality reports (100% verified).

---

### Stage 5: Multi-Cloud Resource Discovery & Inventory Intelligence
- **Status**: [COMPLETED]
- **Focus**: Unified asset discovery, inventory graph, directional topology, financial correlation, and quality evaluation across AWS, Azure, and GCP.
- **Key Deliverables**:
  - Hyperscaler discovery adapters for AWS, Azure, and GCP supporting export parsing (Mode A) and safe read-only API discovery (Mode B) (`backend/app/inventory/adapters/`).
  - Canonical state mapping (`active`, `stopped`, `terminated`, `deleted`, `unknown`, `pending`) and name extraction (`backend/app/inventory/mappers/`).
  - Directional topology relationship extraction (`ATTACHED_TO`, `SNAPSHOT_OF`) with composite deduplication (`backend/app/inventory/models.py`).
  - Intelligent non-destructive reconciliation engine with in-place updates, version incrementing, and 14-day stale asset detection (`backend/app/inventory/reconciliation.py`).
  - Billing-to-inventory financial correlation engine computing expenditure and ledger coverage percentages (`backend/app/inventory/correlation.py`).
  - Severity-tiered inventory quality evaluator calculating attribute completeness and composite confidence scores (`backend/app/inventory/quality.py`).
  - Database schema expansion: `ResourceRelationship`, `InventorySyncRun`, `InventoryQualityReport` with Alembic migration `004_resource_inventory.py`.
  - 13 comprehensive REST API endpoints under `/api/v1/inventory/` (`backend/app/api/routes/inventory.py`).
  - Background asynchronous execution via Celery tasks (`import_inventory_file_task`, `sync_inventory_task`).
  - Realistic multi-cloud synthetic inventory datasets for AWS, Azure, and GCP (`backend/sample_data/inventory/`).
  - Complete test suite passing 100% with 108 automated unit/integration tests (`backend/tests/`).
- **Acceptance Criteria**: Comprehensive inventory graph across 3 clouds with directional relationships, 100% passing tests, and zero float precision violations (100% verified).

---

### Stage 6: Cloud Waste Detection Engine
- **Status**: [COMPLETED]
- **Focus**: Evidence-based, advisory-only algorithmic heuristics identifying idle, oversized, unattached, orphaned, and misconfigured infrastructure across AWS, Azure, and GCP.
- **Key Deliverables**:
  - Suite of 7 pluggable multi-cloud detectors inheriting from `BaseWasteDetector` (`backend/app/waste_detection/detectors/`).
  - Core execution engine `WasteDetectionEngine` with batch evaluation, deduplication on `(resource_id, waste_type)`, and automated lifecycle state transitions (`ACTIVE`, `RESOLVED`, `REOPENED`).
  - Human review workflow supporting `ACKNOWLEDGED`, `DISMISSED` (with mandatory reason and user tracking), and `SNOOZED` (with date calculation).
  - Strict Decimal financial calculations (`SavingsCalculator`) ensuring zero binary floating-point drift and conservative 50% single-tier rightsizing reductions.
  - Multidimensional evidence validator (`EvidenceValidator`) with telemetry conflict safeguards (e.g. low CPU + high network proxy exemption).
  - Database schema expansion: `waste_detection_runs` audit table and extended `waste_detections` with Alembic migration `005_waste_detection_engine.py`.
  - 13 comprehensive REST API endpoints under `/api/v1/waste-detection/` (`backend/app/api/routes/waste_detection.py`).
  - Celery asynchronous task integration (`run_waste_detection_task`).
  - 14 deterministic synthetic FinOps demonstration scenarios (`SyntheticWasteScenarioGenerator`).
  - Complete automated test suite with 133 tests passing with 100% success rate across all project stages (`backend/tests/`).
  - Comprehensive documentation deliverables (`docs/WASTE_DETECTION_ARCHITECTURE.md`, `docs/DETECTION_RULES.md`, `docs/IDLE_COMPUTE_DETECTION.md`, `docs/STORAGE_AND_SNAPSHOT_DETECTION.md`, `docs/OVERSIZED_RESOURCE_DETECTION.md`, `docs/SAVINGS_ESTIMATION.md`, `docs/FINDING_LIFECYCLE.md`, `docs/WASTE_DETECTION_API.md`, `docs/DETECTION_TEST_SCENARIOS.md`).
- **Acceptance Criteria**: Strict advisory-only policy, zero float calculations, zero duplicate findings, multi-sample observation windows, and 100% passing tests (100% verified).

---

### Stage 7: Cost Anomaly Detection Engine
- **Status**: [COMPLETED]
- **Focus**: Enterprise-grade statistical and time-series analytics continuously monitoring cloud expenditure across AWS, Azure, and GCP.
- **Key Deliverables**:
  - Contiguous daily time-series aggregation service with dimensional grouping, date zero-filling, and credit isolation (`backend/app/anomaly_detection/aggregation.py`).
  - Rolling statistical baseline engine computing parametric (mean, standard deviation) and robust non-parametric (median, MAD, quartiles, IQR, Tukey fences) distributions across 7, 14, 30, 60, and 90-day windows with zero-variance safeguards (`backend/app/anomaly_detection/baseline.py`, `statistics.py`).
  - Dual-window comparative testing and CUSUM upward shift tracking distinguishing temporary spikes from persistent step increases and gradual escalations (`backend/app/anomaly_detection/change_points.py`).
  - Suite of 7 specialized pluggable anomaly detectors: `StatisticalEnsembleDetector`, `ChangePointDetector`, `ServiceCostSpikeDetector`, `ResourceCostSpikeDetector`, `ProviderAccountSpikeDetector`, `UsagePriceDivergenceDetector`, and `NewSpendPatternDetector` (`backend/app/anomaly_detection/detectors/`).
  - Centralized detector registry with singleton management (`backend/app/anomaly_detection/registry.py`).
  - Root-cause attribution engine ranking top resource, SKU, and regional contributors and enriching them with Stage 5 `CloudResource` inventory ownership, environment, and tags (`backend/app/anomaly_detection/attribution.py`).
  - Strict Decimal financial impact calculator computing absolute/percentage deviations, estimated excess cost, annualized projections, severity tiers, and anti-double-counting guarantees (`backend/app/anomaly_detection/impact.py`).
  - Lifecycle state manager handling deduplication, in-place updates, auto-resolution on return to normal baseline, reopening, and human review workflows (`backend/app/anomaly_detection/lifecycle.py`).
  - Database schema expansion: `cost_baselines`, `anomaly_detection_runs`, and extended `cost_anomalies` with Alembic migration `006_cost_anomaly_detection_engine.py` and DDL script.
  - 14 comprehensive REST API endpoints under `/api/v1/anomaly-detection/` (`backend/app/api/routes/anomaly_detection.py`).
  - Asynchronous background execution via Celery tasks (`execute_anomaly_detection_job`, `run_anomaly_detection_task`).
  - 20 realistic synthetic FinOps anomaly scenarios across AWS, Azure, and GCP (`backend/app/anomaly_detection/synthetic.py`).
  - Complete automated test suite with 162 total tests passing with 100% success rate across all project stages (`backend/tests/`).
  - 10 comprehensive architectural and operational documentation guides (`docs/ANOMALY_DETECTION_ARCHITECTURE.md`, `docs/COST_AGGREGATION.md`, `docs/STATISTICAL_BASELINES.md`, `docs/STATISTICAL_DETECTION_METHODS.md`, `docs/CHANGE_POINT_DETECTION.md`, `docs/ROOT_CAUSE_ATTRIBUTION.md`, `docs/ANOMALY_FINANCIAL_IMPACT.md`, `docs/ANOMALY_LIFECYCLE.md`, `docs/ANOMALY_DETECTION_API.md`, `docs/SYNTHETIC_ANOMALY_SCENARIOS.md`).
- **Acceptance Criteria**: Strict advisory-only policy, zero float representations, multi-metric consensus, anti-double-counting guarantees, and 100% passing tests (100% verified).

---

### Stage 8: Advisory Recommendation Engine & Savings Optimization
- **Status**: [COMPLETED]
- **Branch**: `stage-8/recommendation-engine`
- **Focus**: Prioritizing, risk-rating, and cataloging actionable savings proposals.
- **Key Deliverables**:
  - Pluggable recommendation strategies (Idle Compute, Rightsizing, Storage, Database, Network, Anomalies, Commitments, Scheduling).
  - Pure Decimal financial savings calculator enforcing the Zero Float Rule.
  - Multi-factor prioritization algorithm combining savings, confidence, effort, risk, and urgency.
  - Cross-stage correlation and anti-double-counting engine with action precedence.
  - Recommendation lifecycle state machine with mandatory rejection reasons and verified savings.
  - Full suite of 16 REST API endpoints, Celery tasks, and 20 synthetic multi-cloud benchmark scenarios.
  - 198 automated unit and integration tests passing with 0 failures.
- **Acceptance Criteria**: Strictly advisory-only with zero mutating cloud API calls; copy-pasteable manual remediation guides.

---

### Stage 9: AI-Powered Multi-Cloud FinOps Copilot
- **Status**: [COMPLETED]
- **Branch**: `stage-9/ai-finops-copilot`
- **Focus**: Enterprise conversational intelligence grounded strictly in deterministic database records.
- **Key Deliverables**:
  - Intent classification engine covering 15 canonical FinOps intents with multi-cloud entity extraction.
  - Deterministic analytical query planner enforcing allowlists on datasets, aggregations, and dimensions with zero raw SQL execution.
  - Cross-stage data retrieval and decimal arithmetic across Stages 3–8 models enforcing the Zero Float Rule.
  - Structured evidence citation generator providing verifiable database entity references and confidence scores.
  - Provider-independent LLM abstraction with live OpenAI-compatible provider and deterministic fallback synthesizer.
  - Security guardrails enforcing prompt injection defense, credential sanitization, and strict non-destructive advisory refusal.
  - Persistent multi-turn conversational memory with entity carry-over, user feedback logging, and operational usage telemetry.
  - Full suite of 10 REST API endpoints under `/api/v1/copilot`.
  - 30 standardized deterministic FinOps benchmark queries passing with 100% accuracy.
  - 236 total automated tests passing with 0 regressions.
- **Acceptance Criteria**: Strict advisory-only policy; mandatory advisory disclaimers; 100% benchmark compliance.

---

### Stage 10: Interactive FinOps Dashboards & Data Visualization
- **Status**: [NEXT]
- **Key Deliverables**:
  - NL2SQL translator mapping user prompts to canonical schema queries.
  - Abstract Syntax Tree (AST) safety parser disallowing mutating SQL operations (`INSERT`, `UPDATE`, `DELETE`, `DROP`).
  - Sandboxed read-only database execution client with 5-second timeout and row caps.
  - Grounded answer synthesizer citing exact returned database rows.
  - Automated verification test comparing generated answer numbers against database outputs.
- **Acceptance Criteria**: Zero fabricated numbers; exact mathematical match with database truth.

---

### Stage 11: Enterprise Frontend Dashboard & Visualization UI
- **Focus**: Responsive React/TypeScript web application delivering executive financial insights.
- **Key Deliverables**:
  - Executive KPI summary cards (Total Spend MTD, Run-Rate, Potential Savings, Realized Savings).
  - Interactive multi-cloud spending distribution charts (Recharts donut & bar charts).
  - Historical spending trends (Daily/Monthly stacked area charts).
  - Filter controls for Date Range, Cloud Provider, Service Category, and Environment.
- **Acceptance Criteria**: Sub-2-second page load time; responsive design across desktop and tablet viewports.

---

### Stage 12: Waste & Recommendation Management UI
- **Focus**: Interactive workbench for triaging waste and reviewing recommendations.
- **Key Deliverables**:
  - Filterable waste items table with utilization telemetry and estimated savings.
  - Recommendation review cards with risk badges, priority tags, and remediation commands.
  - Human-in-the-loop review actions (Endorse, Approve, Dismiss, Snooze).
  - Audit history drawer showing state transitions and reviewer comments.
- **Acceptance Criteria**: Intuitive, error-free workflow transitions reflecting real-time database state.

---

### Stage 13: Anomaly Detection & Alerts Notification Hub
- **Focus**: Threat board for cost spikes and multi-channel notification dispatch.
- **Key Deliverables**:
  - Real-time cost anomaly feed with root-cause drilldown modals.
  - Alert rule configuration interface (thresholds, percentages, notification targets).
  - Outbound dispatch adapters for Slack webhooks, Microsoft Teams, and Email.
  - Notification delivery history log.
- **Acceptance Criteria**: Immediate dispatch of alert payloads upon anomaly detection; full delivery audit trail.

---

### Stage 14: Role-Based Access Control (RBAC), Audit Logging & Security Hardening
- **Focus**: Enterprise identity, authorization enforcement, and security hardening.
- **Key Deliverables**:
  - User authentication via JWT with refresh token rotation.
  - Role-based authorization middleware enforcing permissions across the 5 core personas.
  - Attribute-Based Access Control (ABAC) scoping for team-level engineering managers.
  - Immutable audit logging interceptor recording all state changes and privileged actions.
- **Acceptance Criteria**: Unauthorized API calls blocked with 403 Forbidden; audit records captured without exception.

---

### Stage 15: Production Containerization, CI/CD, Deployment & Benchmark Test Suite
- **Focus**: Production packaging, deployment automation, and operational observability.
- **Key Deliverables**:
  - Multi-stage Dockerfiles for Frontend, Backend API, and Celery Workers.
  - Docker Compose configuration for 1-command local and staging bootstrapping.
  - GitHub Actions CI/CD workflows for automated linting, testing, and container publishing.
  - Prometheus metrics instrumentation and pre-configured Grafana monitoring dashboards.
  - Automated integration test suite validating $\ge 90\%$ waste detection rate across 100 benchmark scenarios.
  - Production deployment guide and operational runbook.
- **Acceptance Criteria**: Fully containerized deployment starting cleanly with verified health checks and metrics scraping.
