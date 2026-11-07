# CloudSage – Multi-Cloud FinOps Copilot

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/Architecture-FOCUS%201.0%20Compliant-green.svg)](docs/FUNCTIONAL_REQUIREMENTS.md)
[![Safety](https://img.shields.io/badge/Safety-Advisory%20Only-orange.svg)](docs/BUSINESS_REQUIREMENTS.md)
[![Status](https://img.shields.io/badge/Status-Stage%204%20Complete-brightgreen.svg)](docs/DEVELOPMENT_ROADMAP.md)

> **CloudSage** is an enterprise-grade, AI-powered Multi-Cloud Financial Operations (FinOps) platform engineered to unify fragmented cloud billing data, detect unnecessary expenditure, identify cost anomalies, and generate prioritized, evidence-backed savings recommendations across **Amazon Web Services (AWS)**, **Microsoft Azure**, and **Google Cloud Platform (GCP)**.

---

## 1. Problem Statement

As modern enterprises scale digital infrastructure across heterogeneous cloud ecosystems, cloud expenditures have rapidly grown into one of the largest operating expenses. However, decentralized engineering practices cause severe financial leakages:

1. **Fragmented Billing Data**: Incompatible billing formats (AWS CUR, Azure Cost Export, GCP BigQuery Export) prevent unified financial reporting and cost visibility.
2. **Unnecessary Spending**: Idle virtual machines and oversized compute instances silently inflate monthly invoices.
3. **Forgotten & Abandoned Infrastructure**: Unattached storage disks (EBS, Managed Disks, Persistent Disks), orphaned backup snapshots, and unused static IPs drain budgets without delivering business value.
4. **Delayed Anomaly Detection**: Unanticipated spending surges are often discovered weeks later during monthly invoice reconciliation.
5. **Deficient Tagging & Ownership**: Missing or inconsistent tags obscure departmental accountability, preventing accurate chargeback and showback.
6. **Information Asymmetry**: Non-technical financial and executive stakeholders struggle to extract actionable insights from complex cloud billing consoles.

---

## 2. Project Objectives

CloudSage bridges the gap between infrastructure engineering, financial operations, and executive leadership by delivering:

- **Single Source of Truth**: Automated ingestion and canonical normalization of multi-cloud billing feeds into the open **FOCUS™ 1.0** standard.
- **Continuous Waste Detection**: Algorithmic heuristics detecting idle, oversized, unattached, and orphaned cloud resources.
- **Near Real-Time Anomaly Detection**: Statistical baselining flagging cost spikes within minutes of ingestion with root-cause attribution.
- **Strictly Advisory Recommendations**: Prioritized savings proposals with transparent mathematical proof and risk classifications. **CloudSage enforces a strict non-destructive policy with zero autonomous deletion or downsizing.**
- **Conversational AI FinOps Copilot**: Natural language query interface grounded strictly in deterministic database calculations—ensuring zero fabricated figures.

---

## 3. Core Features

| Feature Domain | Capabilities |
| :--- | :--- |
| **Multi-Cloud Ingestion** | Scheduled, idempotent ingestion of AWS Cost & Usage Reports (CUR), Azure Cost Management exports, GCP Cloud Billing exports, and local synthetic seed datasets. |
| **Unified Normalization** | Full compliance with FinOps Open Cost & Usage Specification (FOCUS™ 1.0), currency conversion to USD, service taxonomy classification, and tag sanitization. |
| **Cloud Waste Engine** | Automated scanning for idle VMs (CPU < 5%), oversized instances (CPU < 15%), unattached storage disks, orphaned snapshots, idle static IPs, and 24x7 non-production environments. |
| **Cost Anomaly Engine** | 30-day rolling statistical baselines, Z-score ($\ge 3.0$) and IQR outlier detection, structural change-point detection, and instant multi-channel alert dispatch. |
| **Advisory Recommendation Engine** | Actionable remediation proposals with estimated monthly/annualized savings, risk ratings (`NONE`, `LOW`, `MEDIUM`, `HIGH`), priority scoring ($P1$ to $P4$), and human approval lifecycles. |
| **AI FinOps Copilot** | Natural language queries translated into schema-safe, read-only SQL queries with AST validation, returning deterministic figures and tabular proofs. |
| **Executive Dashboard** | High-performance React dashboard showing MTD spend, run-rate projections, provider breakdowns, daily/monthly spend trends, and tagging compliance gauges. |
| **Alerts & Notification Hub** | Configurable budget thresholds and anomaly alerts dispatched via Slack webhooks, Microsoft Teams, and Email. |
| **Enterprise RBAC & Audit** | 5 core persona roles (Super Admin, FinOps Engineer, Finance Analyst, Engineering Manager, Executive) with ABAC team scoping and an immutable audit ledger. |

---

## 4. High-Level System Architecture

```mermaid
flowchart TD
    subgraph Clients["Presentation & Client Layer"]
        UI["React 18 TypeScript Dashboard"]
        CopilotUI["Conversational Copilot Interface"]
    end

    subgraph Gateway["API & Security Layer"]
        API["FastAPI Application Gateway"]
        Auth["JWT & RBAC / ABAC Security Module"]
        Audit["Immutable Audit Logger"]
    end

    subgraph Ingestion["Multi-Cloud Ingestion Adapters"]
        AWSIngest["AWS Ingestion Adapter (CUR / S3 / CloudWatch)"]
        AzureIngest["Azure Ingestion Adapter (Cost Export / Blob / Monitor)"]
        GCPIngest["GCP Ingestion Adapter (Billing / BigQuery / Cloud Monitoring)"]
        SeedIngest["Synthetic & File Seed Ingestion Adapter (CSV / JSON)"]
    end

    subgraph Normalization["ETL & Normalization Engine"]
        Normalizer["FOCUS 1.0 Schema Normalizer & Tag Sanitizer"]
        Idempotency["Deduplication & Idempotency Validator"]
    end

    subgraph Storage["Analytical Data Storage Layer"]
        PG[("PostgreSQL 16 Database (Partitioned Billing & Metrics)")]
        RedisCache[("Redis 7 (In-Memory Cache & Message Broker)")]
    end

    subgraph Workers["Distributed Processing Workers (Celery)"]
        WasteEngine["Cloud Waste Detection Engine"]
        AnomalyEngine["Statistical Cost Anomaly Engine"]
        RecEngine["Advisory Recommendation Engine"]
        NotifService["Notification & Dispatch Service"]
    end

    subgraph Copilot["Cognitive AI FinOps Engine"]
        LLM["AI FinOps Copilot (LLM Orchestrator)"]
        ASTGuard["SQL AST Validator & Safety Sandbox"]
        ReadReplica[("Read-Only Database Connection")]
    end

    subgraph Notifications["External Notification Channels"]
        Slack["Slack Webhook"]
        Teams["Microsoft Teams"]
        Email["Email (SMTP / SendGrid)"]
    end

    %% Client to API
    UI -->|"HTTPS / REST"| API
    CopilotUI -->|"WebSocket / HTTPS"| API

    %% API Layer
    API --> Auth
    API --> Audit
    API --> RedisCache
    API --> PG

    %% Ingestion Flow
    AWSIngest --> Normalizer
    AzureIngest --> Normalizer
    GCPIngest --> Normalizer
    SeedIngest --> Normalizer
    Normalizer --> Idempotency
    Idempotency --> PG

    %% Background Queue & Workers
    API -->|"Enqueue Tasks"| RedisCache
    RedisCache --> Workers
    WasteEngine --> PG
    AnomalyEngine --> PG
    RecEngine --> PG
    NotifService --> Notifications

    %% Copilot Flow
    API --> LLM
    LLM --> ASTGuard
    ASTGuard --> ReadReplica
    ReadReplica -.->|"Ground Truth Rows"| LLM
    LLM -.->|"Verified Grounded Response"| API
```

---

## 5. Technology Stack Summary

- **Frontend**: React 18, TypeScript, Tailwind CSS, Recharts, Lucide Icons, TanStack Table.
- **Backend API**: Python 3.11+, FastAPI (async), Pydantic v2, SQLAlchemy 2.0 (asyncpg).
- **Database**: PostgreSQL 16+ with Native Declarative Range Partitioning by billing period and GIN/B-tree indexing.
- **Data Processing**: Python 3.11, Pandas (chunked streaming), DuckDB / Polars evaluation.
- **Background Processing**: Celery 5.3+, Redis 7+ (broker, results backend, and metrics cache).
- **AI & Copilot**: LLM Orchestration with Schema-Constrained Tool Calling (NL2SQL), Abstract Syntax Tree (AST) query safety validation, and read-only connection sandboxing.
- **Cloud Integrations**: AWS SDK (boto3), Azure SDK, Google Cloud Client Libraries (read-only IAM roles).
- **DevOps & Infrastructure**: Docker (multi-stage builds), Docker Compose, GitHub Actions CI/CD workflows.
- **Observability**: Prometheus metrics exporter, Grafana dashboards, structured JSON logging.

---

## 6. 15-Stage Development Roadmap

The development of CloudSage is structured across 15 disciplined stages:

| Stage | Name | Status | Key Deliverable |
| :---: | :--- | :---: | :--- |
| **01** | **Requirement Analysis & Project Foundation** | **Completed** | Requirements, Architecture, Governance & Roadmap Foundation |
| **02** | **Core Data Models & Database Schema Architecture** | **Completed** | FOCUS 1.0 PostgreSQL schemas, partitioning, and Alembic migrations |
| **03** | **Multi-Cloud Ingestion Engine** | **Completed** | AWS CUR, Azure Cost, GCP BigQuery adapters, deduplication & REST API |
| **04** | **Unified Data Normalization & FOCUS Pipeline** | **Completed** | FOCUS 1.0 validation, historical FX, SKU catalog, tag governance & quality engine |
| **05** | Cloud Waste Detection Engine | *Planned* | Heuristics for idle VMs, oversized compute, unattached disks & snapshots |
| **06** | Cost Anomaly Detection Engine | *Planned* | 30-day statistical baselining, Z-score detection & root-cause attribution |
| **07** | Advisory Recommendation Engine & Optimization | *Planned* | Priority scoring, risk rating, savings calculation & approval states |
| **08** | Core REST API & Backend Service Layer | *Planned* | FastAPI REST endpoints, filtering, cursor pagination & export APIs |
| **09** | AI FinOps Copilot & Grounded Query Engine | *Planned* | Schema-safe NL2SQL translator, AST sandbox & deterministic verifier |
| **10** | Enterprise Frontend Dashboard & Visualization UI | *Planned* | React/TypeScript UI, KPI cards, Recharts trends & provider breakdowns |
| **11** | Waste & Recommendation Management UI | *Planned* | Interactive review tables, approval actions & remediation guides |
| **12** | Anomaly Detection & Alerts Notification Hub | *Planned* | Threat feed, alert threshold rules & Slack/Teams/Email dispatchers |
| **13** | Role-Based Access Control (RBAC) & Audit Logging | *Planned* | JWT auth, role middleware, ABAC scoping & immutable audit logging |
| **14** | System Integration & Benchmark Test Suite | *Planned* | 100-case synthetic benchmark suite validating $\ge 90\%$ waste detection |
| **15** | Production Containerization, CI/CD & Readiness | *Planned* | Multi-stage Docker, Compose, GitHub Actions & Prometheus/Grafana |

---

## 7. Current Development Status

- **Completed Stages**: 
  - Stage 1: Requirement Analysis & Project Foundation (`stage-1/project-foundation`).
  - Stage 2: Core Data Models & Database Schema Architecture (`stage-2/data-models-schema`).
  - Stage 3: Multi-Cloud Ingestion Engine (`stage-3/multicloud-ingestion`).
  - Stage 4: Unified Data Normalization & FOCUS Pipeline (`stage-4/focus-normalization`).
- **Active Branch**: `stage-4/focus-normalization`.
- **Next Milestone**: Stage 5 (Cloud Waste Detection Engine) awaits formal review and approval.

---

## 8. Multi-Cloud Normalization & Ingestion Engine Quickstart

CloudSage provides an end-to-end multi-cloud billing ingestion, FOCUS 1.0 normalization, and data quality evaluation engine.

### Ingestion & Normalization REST API
```bash
# Start the FastAPI application
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 1. Ingest Multi-Cloud Billing Feeds
curl -X POST "http://localhost:8000/api/v1/ingestion/upload/aws" \
  -F "file=@backend/sample_data/aws/aws_cur_sample.csv"

# 2. Trigger Batch Normalization / In-Place Reprocessing
curl -X POST "http://localhost:8000/api/v1/normalization/run" \
  -H "Content-Type: application/json" \
  -d '{"provider": "AWS", "reprocess_all": true, "batch_size": 500}'

# 3. Retrieve Latest Data Quality Assessment
curl "http://localhost:8000/api/v1/normalization/quality-report"

# 4. Check FOCUS 1.0 Conformance Assessment
curl "http://localhost:8000/api/v1/normalization/focus-validation"

# 5. Query Tag Hygiene Scores
curl "http://localhost:8000/api/v1/normalization/tag-quality?limit=10"
```

### Running Test Suites
```bash
python3 -m pytest backend/tests -v
```

---

## 9. Documentation Index

Detailed architectural and functional specifications are located in the [`docs/`](docs/) directory:

- [Project Overview & Executive Summary](docs/PROJECT_OVERVIEW.md)
- [Business Requirements Document (BRD)](docs/BUSINESS_REQUIREMENTS.md)
- [Functional Requirements Document (FRD)](docs/FUNCTIONAL_REQUIREMENTS.md)
- [Non-Functional Requirements Document (NFR)](docs/NON_FUNCTIONAL_REQUIREMENTS.md)
- [Database Schema & Relational Data Architecture](docs/DATABASE_SCHEMA.md)
- [Multi-Cloud Ingestion Engine Architecture](docs/INGESTION_ARCHITECTURE.md)
- [Cloud Provider Field Mappings & Normalization Taxonomy](docs/CLOUD_PROVIDER_FIELD_MAPPINGS.md)
- [FOCUS 1.0 Specification Conformance & Matrix](docs/FOCUS_1_0_IMPLEMENTATION.md)
- [Advanced Currency Normalization & Historical FX](docs/CURRENCY_NORMALIZATION.md)
- [Multi-Cloud SKU Catalog & Taxonomy](docs/SKU_CATALOG.md)
- [Advanced Resource Tag Normalization & Hygiene](docs/TAG_NORMALIZATION.md)
- [Data Quality & Governance Framework](docs/DATA_QUALITY_FRAMEWORK.md)
- [Unified Normalization Pipeline Architecture](docs/NORMALIZATION_PIPELINE.md)
- [Data Normalization & FOCUS 1.0 Alignment](docs/DATA_NORMALIZATION.md)
- [Synthetic Datasets & Seeded FinOps Scenarios](docs/SYNTHETIC_DATASETS.md)
- [Multi-Cloud Ingestion API Reference](docs/INGESTION_API.md)
- [User Roles, Personas & Permissions Matrix](docs/USER_ROLES_AND_PERMISSIONS.md)
- [Technology Stack Evaluation](docs/TECHNOLOGY_STACK.md)
- [System Architecture & Data Flow](docs/SYSTEM_ARCHITECTURE.md)
- [Acceptance & Success Criteria](docs/SUCCESS_CRITERIA.md)
- [15-Stage Enterprise Development Roadmap](docs/DEVELOPMENT_ROADMAP.md)

---

## 10. Non-Destructive Advisory Policy

> [!IMPORTANT]
> **Advisory-Only Safety Guarantee**: CloudSage does **not** perform autonomous destructive changes to cloud infrastructure. All recommendations generated by the platform are strictly advisory. Infrastructure modifications require human review, engineering approval, and manual or CI/CD execution via external infrastructure-as-code tools (Terraform, CloudFormation, Pulumi, or cloud consoles).
