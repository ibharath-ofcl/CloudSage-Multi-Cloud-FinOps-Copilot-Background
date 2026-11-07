# CloudSage: 15-Stage Enterprise Development Roadmap

## 1. Roadmap Architecture and Phasing Strategy

CloudSage is developed across 15 structured, modular stages to ensure enterprise-grade software quality, strict security controls, financial accuracy, and seamless pair-programming progression.

```
PHASE 1: FOUNDATION & DATA ARCHITECTURE (Stages 1 - 4)
  Stage 1: Requirement Analysis & Project Foundation [COMPLETED]
  Stage 2: Core Data Models & Database Schema Architecture [COMPLETED]
  Stage 3: Multi-Cloud Ingestion Engine [COMPLETED]
  Stage 4: Unified Data Normalization & FOCUS Pipeline [NEXT]

PHASE 2: ANALYTICAL & COGNITIVE ENGINES (Stages 5 - 7)
  Stage 5: Cloud Waste Detection Engine
  Stage 6: Cost Anomaly Detection Engine
  Stage 7: Advisory Recommendation Engine & Savings Optimization

PHASE 3: BACKEND SERVICES & AI COPILOT (Stages 8 - 9)
  Stage 8: Core REST API & Backend Service Layer
  Stage 9: AI FinOps Copilot & Grounded Query Engine

PHASE 4: USER INTERFACE & NOTIFICATIONS (Stages 10 - 12)
  Stage 10: Enterprise Frontend Dashboard & Visualization UI
  Stage 11: Waste & Recommendation Management UI
  Stage 12: Anomaly Detection & Alerts Notification Hub

PHASE 5: SECURITY, VERIFICATION & PRODUCTION READINESS (Stages 13 - 15)
  Stage 13: Role-Based Access Control (RBAC), Audit Logging & Security Hardening
  Stage 14: System Integration, End-to-End Testing & Benchmark Test Suite
  Stage 15: Production Containerization, CI/CD, Deployment & Operational Readiness
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

### Stage 4: Unified Data Normalization & FOCUS Pipeline
- **Focus**: Transforming disparate multi-cloud records into the canonical FinOps schema.
- **Key Deliverables**:
  - Currency conversion service standardizing all expenditures to USD.
  - Service classification lookup engine categorizing compute, storage, database, networking, and AI/ML.
  - Tag normalization engine sanitizing casing, trimming whitespace, and extracting core FinOps tags.
  - Timestamp standardization to UTC ISO-8601 hourly and daily intervals.
- **Acceptance Criteria**: 100% field mapping parity across AWS, Azure, and GCP records into the canonical FOCUS schema.

---

### Stage 5: Cloud Waste Detection Engine
- **Focus**: Algorithmic heuristics identifying idle, oversized, and orphaned infrastructure.
- **Key Deliverables**:
  - Idle Virtual Machine detector (CPU < 5%, network < 5MB/day over 7 days).
  - Oversized Compute detector (CPU < 15%, memory < 20% over 14 days).
  - Unattached Block Storage detector (unattached AWS EBS, Azure Disks, GCP Persistent Disks > 3 days).
  - Orphaned Snapshot detector (snapshots older than retention policy or deleted parent volumes).
  - Idle IP and Zero-Target Load Balancer detector.
  - Off-hours continuous non-production environment detector.
- **Acceptance Criteria**: Flagging idle and oversized assets with calculated historical monthly costs and utilization proof.

---

### Stage 6: Cost Anomaly Detection Engine
- **Focus**: Statistical time-series anomaly detection and root-cause attribution.
- **Key Deliverables**:
  - Rolling 30-day baseline calculator ($\mu$, $\sigma$, Median, IQR) partitioned by provider, service, and account.
  - Z-score and IQR outlier detection algorithms.
  - Change-point detection identifying structural expenditure step-functions.
  - Automated root-cause attribution engine identifying offending resources, regions, and tags.
- **Acceptance Criteria**: Detection of cost spikes within minutes of ingestion; attribution accuracy pinpointing specific service drivers.

---

### Stage 7: Advisory Recommendation Engine & Savings Optimization
- **Focus**: Prioritizing, risk-rating, and cataloging actionable savings proposals.
- **Key Deliverables**:
  - Advisory recommendation generator translating detected waste into structured action items.
  - Savings calculation formulas (projected monthly and annualized cost reductions).
  - Risk classification model (`NONE`, `LOW`, `MEDIUM`, `HIGH`) with blast-radius explanations.
  - Priority scoring matrix ($P1$ to $P4$) balancing financial impact against effort.
  - Audited recommendation lifecycle state machine (`PROPOSED`, `UNDER_REVIEW`, `APPROVED`, `DISMISSED`, `IMPLEMENTED`).
- **Acceptance Criteria**: Zero automated destructive commands; clear step-by-step manual remediation guides.

---

### Stage 8: Core REST API & Backend Service Layer
- **Focus**: High-throughput FastAPI application exposing secure REST endpoints.
- **Key Deliverables**:
  - REST endpoints for Dashboard KPIs, Spend Trends, Waste Items, Anomalies, and Recommendations.
  - Filterable, paginated query APIs with cursor-based pagination.
  - Export endpoints generating standardized CSV and JSON financial reports.
  - CORS, rate-limiting, and Pydantic request/response validation middleware.
- **Acceptance Criteria**: p95 API response latency < 200ms; complete OpenAPI / Swagger documentation.

---

### Stage 9: AI FinOps Copilot & Grounded Query Engine
- **Focus**: Natural language query interface with deterministic database grounding.
- **Key Deliverables**:
  - NL2SQL translator mapping user prompts to canonical schema queries.
  - Abstract Syntax Tree (AST) safety parser disallowing mutating SQL operations (`INSERT`, `UPDATE`, `DELETE`, `DROP`).
  - Sandboxed read-only database execution client with 5-second timeout and row caps.
  - Grounded answer synthesizer citing exact returned database rows.
  - Automated verification test comparing generated answer numbers against database outputs.
- **Acceptance Criteria**: Zero fabricated numbers; exact mathematical match with database truth.

---

### Stage 10: Enterprise Frontend Dashboard & Visualization UI
- **Focus**: Responsive React/TypeScript web application delivering executive financial insights.
- **Key Deliverables**:
  - Executive KPI summary cards (Total Spend MTD, Run-Rate, Potential Savings, Realized Savings).
  - Interactive multi-cloud spending distribution charts (Recharts donut & bar charts).
  - Historical spending trends (Daily/Monthly stacked area charts).
  - Filter controls for Date Range, Cloud Provider, Service Category, and Environment.
- **Acceptance Criteria**: Sub-2-second page load time; responsive design across desktop and tablet viewports.

---

### Stage 11: Waste & Recommendation Management UI
- **Focus**: Interactive workbench for triaging waste and reviewing recommendations.
- **Key Deliverables**:
  - Filterable waste items table with utilization telemetry and estimated savings.
  - Recommendation review cards with risk badges, priority tags, and remediation commands.
  - Human-in-the-loop review actions (Endorse, Approve, Dismiss, Snooze).
  - Audit history drawer showing state transitions and reviewer comments.
- **Acceptance Criteria**: Intuitive, error-free workflow transitions reflecting real-time database state.

---

### Stage 12: Anomaly Detection & Alerts Notification Hub
- **Focus**: Threat board for cost spikes and multi-channel notification dispatch.
- **Key Deliverables**:
  - Real-time cost anomaly feed with root-cause drilldown modals.
  - Alert rule configuration interface (thresholds, percentages, notification targets).
  - Outbound dispatch adapters for Slack webhooks, Microsoft Teams, and Email.
  - Notification delivery history log.
- **Acceptance Criteria**: Immediate dispatch of alert payloads upon anomaly detection; full delivery audit trail.

---

### Stage 13: Role-Based Access Control (RBAC), Audit Logging & Security Hardening
- **Focus**: Enterprise identity, authorization enforcement, and security hardening.
- **Key Deliverables**:
  - User authentication via JWT with refresh token rotation.
  - Role-based authorization middleware enforcing permissions across the 5 core personas.
  - Attribute-Based Access Control (ABAC) scoping for team-level engineering managers.
  - Immutable audit logging interceptor recording all state changes and privileged actions.
- **Acceptance Criteria**: Unauthorized API calls blocked with 403 Forbidden; audit records captured without exception.

---

### Stage 14: System Integration, End-to-End Testing & Benchmark Test Suite
- **Focus**: Comprehensive validation against synthetic benchmark datasets and success criteria.
- **Key Deliverables**:
  - Synthetic benchmark dataset containing 100 seeded waste scenarios and cost spikes.
  - Automated integration test suite validating $\ge 90\%$ waste detection rate.
  - End-to-end pipeline latency validation (ingestion to anomaly alert $\le 5$ minutes).
  - Automated Copilot mathematical truth assertion test suite.
- **Acceptance Criteria**: All 7 core success criteria verified and passing in automated test harness.

---

### Stage 15: Production Containerization, CI/CD, Deployment & Operational Readiness
- **Focus**: Production packaging, deployment automation, and operational observability.
- **Key Deliverables**:
  - Multi-stage Dockerfiles for Frontend, Backend API, and Celery Workers.
  - Docker Compose configuration for 1-command local and staging bootstrapping.
  - GitHub Actions CI/CD workflows for automated linting, testing, and container publishing.
  - Prometheus metrics instrumentation and pre-configured Grafana monitoring dashboards.
  - Production deployment guide and operational runbook.
- **Acceptance Criteria**: Fully containerized deployment starting cleanly with verified health checks and metrics scraping.
