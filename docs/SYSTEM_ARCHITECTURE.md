# CloudSage: System Architecture and Data Flow

## 1. Architectural Overview

CloudSage is designed as a distributed, decoupled, service-oriented architecture engineered for high concurrency, deterministic financial accuracy, and multi-cloud scalability.

The system partitions responsibilities cleanly across:
1. **Presentation Layer**: Responsive React/TypeScript client with interactive Recharts visualizations.
2. **API & Gateway Layer**: High-throughput FastAPI application exposing secure REST endpoints, enforcing JWT auth and RBAC/ABAC policies.
3. **Ingestion & Normalization Layer**: Cloud-specific adapters consuming AWS, Azure, and GCP billing feeds, converting them into a canonical FOCUS 1.0 schema.
4. **Analytical Storage Layer**: Partitioned PostgreSQL 16 database storing normalized billing ledgers, telemetry, detection outputs, and audit logs.
5. **Analytical Detection Engines**: Asynchronous Celery workers evaluating deterministic waste heuristics and statistical cost anomaly baselines.
6. **Advisory Recommendation Engine**: Generates prioritized, risk-scored optimization plans with human-in-the-loop governance.
7. **AI FinOps Copilot**: Natural Language to SQL (NL2SQL) engine equipped with schema validation, AST safety parsing, read-only database sandboxing, and deterministic answer grounding.
8. **Notification & Dispatch Service**: Multi-channel notification pipeline publishing alerts to Slack, Teams, Email, and Webhooks.
9. **Observability & Telemetry Infrastructure**: Prometheus metrics harvesting, structured JSON logging, and Grafana dashboard visualization.

---

## 2. High-Level Architecture Diagram

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

    subgraph Observability["Monitoring & Telemetry"]
        Prom["Prometheus Metrics Exporter"]
        Grafana["Grafana Dashboards"]
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

    %% Observability
    API --> Prom
    Workers --> Prom
    Prom --> Grafana
```

---

## 3. End-to-End Data Flow

The platform executes five primary operational data flows:

### 3.1 Data Flow 1: Ingestion and Normalization Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Cloud as Cloud Providers (AWS / Azure / GCP)
    participant Celery as Ingestion Worker (Celery)
    participant Normalizer as FOCUS Normalization Engine
    participant DB as PostgreSQL Database
    participant Redis as Redis Cache

    Cloud->>Celery: Deliver Billing Export / Poll Trigger
    Celery->>Normalizer: Stream Raw Line Items (Chunked)
    Normalizer->>Normalizer: Map SKUs to Standard Taxonomy
    Normalizer->>Normalizer: Convert Currency to USD & Sanitize Tags
    Normalizer->>DB: Batch Insert into Partitioned Billing Table
    DB-->>Celery: Confirm Ingestion Watermark & Line Count
    Celery->>Redis: Invalidate Stale Spend Caches
    Celery->>Redis: Enqueue Waste & Anomaly Detection Tasks
```

1. **Scheduled Trigger**: Celery Beat or cloud webhooks trigger an ingestion job for an active provider account.
2. **Chunked Stream**: Raw billing files (AWS CUR, Azure Cost Export, GCP BigQuery rows) are streamed in 50,000-row chunks.
3. **Standardization**: Provider-specific fields are mapped into the FOCUS 1.0 canonical format (`record_id`, `provider`, `service_category`, `unblended_cost`, `tags`).
4. **Currency & Tag Normalization**: Costs are converted to USD; tags are lowercased and stripped of whitespace; canonical tags (`owner`, `environment`, `project`) are extracted.
5. **Idempotent Upsert**: Batches are written to PostgreSQL using composite uniqueness checks (`provider`, `account_id`, `usage_start_time`, `line_item_id`).
6. **Task Trigger**: Ingestion completion automatically signals the Waste and Anomaly Detection engines.

---

### 3.2 Data Flow 2: Waste and Anomaly Detection Pipeline

```mermaid
sequenceDiagram
    autonumber
    participant Queue as Redis Task Queue
    participant Waste as Waste Detection Engine
    participant Anomaly as Cost Anomaly Engine
    participant Rec as Recommendation Engine
    participant DB as PostgreSQL Database
    participant Notif as Notification Dispatcher

    Queue->>Waste: Trigger Waste Scan
    Queue->>Anomaly: Trigger Anomaly Scan
    Waste->>DB: Query Inactive / Oversized / Orphaned Assets
    DB-->>Waste: Return Idle Assets & Metrics
    Waste->>Rec: Generate Advisory Recommendation Records
    Rec->>DB: Persist Recommendations with 'PROPOSED' State
    
    Anomaly->>DB: Query 30-Day Rolling Cost Baselines
    DB-->>Anomaly: Historical Mean, StdDev, IQR
    Anomaly->>Anomaly: Compute Z-Scores and Outlier Fences
    Anomaly->>DB: Persist Detected Anomalies & Root Causes
    
    Anomaly->>Notif: Dispatch Alert if Severity >= High
    Notif->>Notif: Format Slack / Teams / Email Message
```

1. **Waste Engine Execution**: Runs deterministic heuristics against unified data:
   - Queries instances where average CPU utilization was $< 5\%$ and network I/O $< 5\text{MB/day}$ over 7 days.
   - Queries block storage volumes in `available` (unattached) status for $> 3\text{ days}$.
   - Queries snapshots with age $> 90\text{ days}$ or deleted source volumes.
2. **Recommendation Generation**: Converts detected waste into structured advisory recommendations with projected dollar savings and risk scoring.
3. **Anomaly Engine Execution**: Calculates 30-day rolling baseline metrics ($\mu$, $\sigma$, IQR) per service and account. Detects spending spikes where Z-score $\ge 3.0$ and absolute daily delta $> \$50$.
4. **Root-Cause Attribution**: Identifies the primary cost-driving resource, region, and team tag.
5. **Notification Dispatch**: Dispatches urgent alerts to configured Slack webhooks and email distribution lists.

---

### 3.3 Data Flow 3: AI FinOps Copilot Conversational Query Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as User (Finance / Eng / Exec)
    participant UI as React Copilot Interface
    participant API as FastAPI Backend
    participant LLM as LLM Orchestration Service
    participant Guard as AST Safety Validator
    participant DB as PostgreSQL (Read-Only)

    User->>UI: "Why did AWS spend increase this week?"
    UI->>API: POST /api/v1/copilot/query
    API->>LLM: Formulate Prompt with Injected DDL Schema
    LLM->>LLM: Generate Analytical SQL Query
    LLM->>Guard: Submit Generated SQL for Verification
    Guard->>Guard: AST Parse (Enforce SELECT only, Block Mutating Keywords)
    Guard->>DB: Execute Query with 5s Timeout (Read-Only User)
    DB-->>Guard: Return Raw Aggregated Rows
    Guard-->>LLM: Forward Ground-Truth Numerical Proof
    LLM->>LLM: Synthesize Grounded Natural Language Explanation
    LLM-->>API: Response Payload (Text, Tabular Proof, SQL Query)
    API-->>UI: Render Answer, Proof Table, and Drilldown Visualizer
```

1. **User Prompt**: The user enters a question in natural language.
2. **Context Assembly**: Backend injects canonical schema definitions and user role-scoping filters.
3. **SQL Generation**: The LLM acts as an expert SQL query generator, producing a precise aggregation query.
4. **AST Safety Guard**: The query is validated using an Abstract Syntax Tree (AST) parser to ensure:
   - Query starts strictly with `SELECT`.
   - Contains no data-modifying statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`).
   - Restricts row limits (`LIMIT 100`).
5. **Deterministic Execution**: The query is executed on a dedicated read-only database connection.
6. **Grounded Synthesis**: The LLM synthesizes the natural language response using **only** the returned rows, citing exact numbers and displaying the underlying proof table.

---

### 3.4 Data Flow 4: Human-in-the-Loop Recommendation Lifecycle

```mermaid
stateDiagram-v2
    [*] --> PROPOSED: Waste Engine Detects Inefficiency
    
    PROPOSED --> UNDER_REVIEW: Engineer or Analyst Opens Details
    
    UNDER_REVIEW --> ENDORSED: Finance Analyst Validates ROI
    UNDER_REVIEW --> SNOOZED: Engineer Snoozes for 30 Days
    UNDER_REVIEW --> DISMISSED: Engineer Flags as Legitimate Workload
    
    ENDORSED --> APPROVED: FinOps Lead / Squad Lead Grants Approval
    UNDER_REVIEW --> APPROVED: FinOps Lead Grants Approval Directly
    
    APPROVED --> IMPLEMENTED: Engineer Executes Manual Change (Terraform/Console)
    
    DISMISSED --> [*]
    IMPLEMENTED --> [*]
    SNOOZED --> PROPOSED: 30-Day Snooze Window Expires
```

---

## 4. Security Boundaries and Isolation

- **Zero Ingress to Production Clouds**: CloudSage does not require ingress ports to enterprise virtual private clouds (VPCs). Cloud billing data is pulled securely via HTTPS from cloud storage buckets or BigQuery datasets.
- **Read-Only Credentials**: Cloud integrations operate strictly under read-only IAM policies. The backend cannot create, modify, downscale, or delete any cloud asset.
- **Database Connection Isolation**:
  - `app_writer`: Used by ingestion workers for inserting normalized records.
  - `app_reader`: Used by standard dashboard endpoints.
  - `copilot_sandbox`: Restricted read-only user with explicit execution timeouts and row caps, preventing resource starvation or data exfiltration.
