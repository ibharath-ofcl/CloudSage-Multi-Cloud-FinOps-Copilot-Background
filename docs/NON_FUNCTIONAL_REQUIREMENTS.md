# CloudSage: Non-Functional Requirements Document (NFR)

## 1. Overview and Quality Attributes

This document articulates the non-functional requirements (NFRs), architectural quality attributes, security standards, and operational service level objectives (SLOs) governing the CloudSage Multi-Cloud FinOps platform.

---

## 2. Security and Access Control

### 2.1 Identity and Authentication
- **Authentication Standard**: JSON Web Tokens (JWT) signed using RS256 (asymmetric RSA 2048-bit keypair) with strict token expiration (Access tokens: 15 minutes; Refresh tokens: 7 days with rotation).
- **Multi-Factor Authentication (MFA)**: Support for Time-based One-Time Password (TOTP) compliant with RFC 6238 for privileged administrative accounts.
- **Enterprise Single Sign-On (SSO)**: SAML 2.0 and OIDC federation integration readiness for corporate identity providers (Okta, Azure AD / Microsoft Entra ID, Google Workspace).

### 2.2 Role-Based Access Control (RBAC)
- Fine-grained permission model mapping users to roles (`SuperAdmin`, `FinOpsEngineer`, `FinanceAnalyst`, `EngineeringManager`, `Executive`).
- Granular permission checks enforced at both the API gateway and individual service methods.

### 2.3 Data Encryption
- **Data in Transit**: Enforced TLS 1.3 across all incoming client connections, internal microservice communication, and external cloud API calls. Insecure cipher suites are rejected.
- **Data at Rest**: AES-256 encryption across all persistent volumes, PostgreSQL table storage, Redis caching layers, and backup archives.

---

## 3. Cloud Credential Security & Least Privilege

> [!CAUTION]
> CloudSage strictly prohibits storing static, long-lived cloud credentials (e.g., AWS Access Key / Secret Key pairs, Azure client secrets, or GCP service account JSON keyfiles) on disk or in the database.

### 3.1 Cloud Integration Authentication Standards
- **Amazon Web Services (AWS)**: STS `AssumeRole` using AWS IAM Cross-Account Roles with unique External ID and read-only policies:
  - `arn:aws:iam::aws:policy/AWSOrganizationsReadOnlyAccess`
  - `arn:aws:iam::aws:policy/CostAndUsageReportAutomationPolicy`
  - CloudWatch Read-Only access (`cloudwatch:GetMetricData`).
- **Microsoft Azure**: Azure Active Directory / Entra ID Workload Identity Federation using managed federated credentials. Assigned read-only roles:
  - `Cost Management Reader`
  - `Monitoring Reader`
- **Google Cloud Platform (GCP)**: Workload Identity Federation with short-lived OAuth 2.0 access tokens. Assigned read-only IAM roles:
  - `roles/billing.viewer`
  - `roles/monitoring.viewer`
  - `roles/bigquery.dataViewer` (for BigQuery billing export dataset).

### 3.2 Secrets Management
- Application runtime secrets (JWT signing keys, database passwords, API tokens) must be injected via environment variables managed by an enterprise secret manager (e.g., HashiCorp Vault, AWS Secrets Manager, or Google Secret Manager).
- Zero plaintext secrets in repository or container images.

---

## 4. API Security and Hardening

- **Rate Limiting**: IP-based and user-based token bucket rate limiting:
  - Public/Auth endpoints: 10 requests / minute.
  - Standard REST API endpoints: 120 requests / minute per user.
  - AI Copilot query endpoint: 20 requests / minute per user.
- **CORS Policies**: Explicit origin whitelisting; wildcards (`*`) disallowed in production.
- **Input Validation & Sanitization**: Strict Pydantic v2 validation models for all request payloads. Disallow raw or unescaped strings to prevent SQL Injection and Cross-Site Scripting (XSS).
- **Security Headers**: Enforce `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security` (HSTS with 2-year max-age).

---

## 5. Performance and Latency SLOs

```
+------------------------------------------------------------------------------------+
|                         SERVICE LEVEL OBJECTIVES (SLOs)                            |
+-----------------------------------------+------------------------------------------+
| Performance Metric                      | Target Objective (95th / 99th Percentile)|
+-----------------------------------------+------------------------------------------+
| Dashboard Metric API Response           | p95 < 200 ms, p99 < 500 ms               |
| Historical Time-Series Aggregation Query| p95 < 800 ms, p99 < 1,500 ms             |
| Waste Detection Batch Scan              | Complete scan < 30 seconds for 100k rows |
| Anomaly Detection Pipeline              | Complete scan < 15 seconds per ingest run|
| AI Copilot Response Latency             | p95 < 3.5 seconds (incl. LLM generation) |
| Ingestion Processing Throughput         | >= 50,000 billing records / minute       |
| Frontend Initial Page Load (LCP)        | < 1.8 seconds on 4G / broadband          |
+-----------------------------------------+------------------------------------------+
```

---

## 6. Scalability and Elasticity

- **Horizontal Scalability**: Stateless FastAPI application containers scaled horizontally behind an Application Load Balancer or Kubernetes Ingress.
- **Database Partitioning**: PostgreSQL billing tables partitioned by `provider` and `billing_period` (monthly ranges) to maintain index performance as records grow to tens of millions.
- **Decoupled Background Tasks**: Ingestion, waste heuristic evaluation, and anomaly detection delegated to distributed Celery worker nodes backed by Redis queues.
- **Read-Replica Architecture**: Analytical dashboard reads and AI Copilot queries route to read replicas, preventing contention with live ingestion write pipelines.

---

## 7. Reliability, Availability, and Fault Tolerance

- **High Availability**: Architecture engineered for 99.9% uptime (excluding scheduled maintenance).
- **Graceful Degradation**: If an external cloud provider API or LLM endpoint experiences an outage, core dashboard visualization from previously cached and normalized records remains fully available.
- **Idempotent Ingestion**: Ingestion worker tasks can be retried indefinitely upon failure without generating duplicate records or corrupted ledger calculations.
- **Circuit Breaker Pattern**: Upstream API calls (cloud billing endpoints, notification webhooks, LLM APIs) implement circuit breakers with exponential backoff and jitter.
- **Dead-Letter Queues (DLQ)**: Malformed ingestion payloads are moved to an unrecoverable DLQ table for inspection without blocking pipeline execution.

---

## 8. Data Accuracy and Financial Integrity

- **Penny-Accurate Floating Point Prevention**: All financial cost values, usage quantities, and savings estimations must use exact arbitrary-precision decimal representations (`NUMERIC(18, 4)` in PostgreSQL and `Decimal` in Python). Floating point arithmetic (`float` / `double`) is strictly forbidden for currency.
- **Reconciliation Check**: Automated post-ingestion validation comparing the sum of normalized line-item costs against the raw invoice header total; variance must be $\le \$0.01$.

---

## 9. Auditability and Compliance

- **Immutable Audit Ledger**: Comprehensive logging of critical system events:
  - User logins, logout events, and failed authentication attempts.
  - Recommendation state transitions (`PROPOSED` -> `APPROVED` -> `IMPLEMENTED`).
  - Copilot queries, generated SQL statements, and execution latency.
  - Manual override or dismissal of waste detections.
- **Audit Record Schema**: Every audit record captures `timestamp`, `user_id`, `client_ip`, `action_type`, `target_resource_id`, `before_state`, and `after_state`.
- **Compliance Alignment**: System designed to support SOC 2 Type II, ISO 27001, and GDPR Article 32 data processing security standards.

---

## 10. Observability and Monitoring

- **Metrics Telemetry**: Prometheus metrics exporter exposing application telemetry:
  - HTTP request rate, error rate (4xx/5xx), and duration histograms.
  - Celery queue depth, task processing duration, and failure counts.
  - Ingestion pipeline record throughput and normalization error counts.
  - Active waste detection count and potential savings total.
- **Structured JSON Logging**: All application logs formatted as structured JSON with correlation IDs (`trace_id`, `request_id`, `user_id`) to enable distributed tracing.
- **Health Check Probes**:
  - `/health/liveness`: Verifies web service process availability.
  - `/health/readiness`: Verifies active connectivity to PostgreSQL and Redis.

---

## 11. Maintainability and Code Quality

- **Modular Architecture**: Layered, clean architecture separating domain entities, repository data access, service business logic, and API transport controllers.
- **Strict Typing**: 100% type annotations enforced in Python via `mypy` (strict mode) and TypeScript in the React frontend.
- **Automated Testing Suite**: Minimum 85% test coverage requirement across unit, integration, and end-to-end synthetic suites.
