# CloudSage Stage 12: Repository & Security Architecture Audit

**Date:** 2026-11-08  
**Scope:** Stage 12 Cost Anomaly & Enterprise Alerts Notification Hub  
**Auditors:** Senior Cloud FinOps Architect, Backend Engineer, Security Engineer  

---

## 1. Audit Overview & Objectives

Before implementing Stage 12, an in-depth audit of the existing codebase was conducted across:
1. Stage 7 Anomaly Detection Engine (models, statistical detectors, change-point analyzers, lifecycle state).
2. Existing Alert and Notification Models (`AlertRule`, `NotificationLog`) and Alembic migration history.
3. API Gateway routing, schema definitions, and Celery background task processing.
4. Identity, authentication, and authorization mechanisms across Stages 1–11.
5. Security controls (SSRF, credential exposure, injection defense, Zero Float Rule).
6. Frontend architecture (React 18, Tailwind, global Header, Sidebar navigation, and FilterContext).

---

## 2. Reusable Existing Components

| Existing Component | File Path | Reuse Strategy in Stage 12 |
|---|---|---|
| **`CostAnomaly` Model** | `backend/app/models/anomaly.py` | Acts as the authoritative source of truth for cost anomalies. Stage 12 connects alerts to `CostAnomaly.id` via foreign key without altering Stage 7 statistical baselining. |
| **`AnomalyStatus` & `Severity`** | `backend/app/core/enums.py` | Reuse standard severity tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) and lifecycle states. |
| **`AlertRule` Model** | `backend/app/models/alert.py` | Extend existing table with enterprise dimensions: `provider`, `account_id`, `region`, `service_name`, `environment`, `owner`, `cost_center`, `min_severity`, `min_excess_cost`, `percentage_deviation_threshold`, `cooldown_minutes`, and `escalation_policy`. |
| **`NotificationLog` Model** | `backend/app/models/alert.py` | Retain for historical dispatch logging, supplemented by `NotificationOutbox` for the transactional outbox pattern and `NotificationDeliveryAttempt` for detailed attempt retries. |
| **`User` Model** | `backend/app/models/user.py` | Reused for authenticated principal resolution, role enforcement (`UserRole`), and recipient routing. |
| **`Celery` Task Infrastructure** | `backend/app/core/config.py`, `backend/app/anomaly_detection/tasks.py` | Reused for asynchronous outbox processing, delivery retry queues, and scheduled digest generation. |
| **Frontend Layout & Components** | `frontend/src/components/Header.tsx`, `Sidebar.tsx`, `AuditTimeline.tsx` | Integrate `NotificationBell` into header; add `/alerts` and `/alert-rules` to navigation; reuse timeline styling for alert state history. |

---

## 3. Mandatory Identity & Authorization Audit

### Finding & Analysis:
In Stages 1–11, review endpoints (e.g. `POST /api/v1/recommendations/{id}/action` and `POST /api/v1/waste/findings/{id}/action`) relied on client-supplied `actor` string fields in the JSON payload (e.g., `request.actor`).
Because Stage 14 is the scheduled RBAC/Auth stage in the overall roadmap, global JWT Bearer enforcement is not yet mandated across all legacy endpoints.

### Identified Security Gap:
If client-supplied actors are trusted for alert suppression, rule creation, notification marking, or alert resolution, malicious actors or compromised clients could spoof administrative identities (e.g., claiming to be `admin@company.com`) or suppress critical cost spike alerts undetected.

### Stage 12 Security Resolution:
1. Introduce a server-side authenticated principal resolution dependency: `get_authenticated_principal` in `backend/app/alerts/security.py`.
2. Inspects `Authorization: Bearer <token>` or server-verified headers (`X-User-Email`, `X-User-Role`, `X-Tenant-Id`).
3. Validates against the `users` table where populated; falls back to an authenticated system identity for background Celery worker tasks.
4. Enforces RBAC permissions:
   - `SUPER_ADMIN` / `FINOPS_ENGINEER`: Can create, edit, enable, disable, and archive alert rules; configure escalation policies and suppress alerts.
   - `FINANCE_ANALYST` / `ENGINEERING_MANAGER` / `EXECUTIVE`: Can view alerts, acknowledge, investigate, resolve, and update their own notification preferences.
5. Never trust an unverified client-provided string for security-critical actions.

---

## 4. Webhook Security & SSRF Protection Audit

### Finding & Analysis:
Outbound webhooks allow sending JSON alert payloads to user-configured HTTP/HTTPS endpoints.

### Identified Security Risk:
If an operator or attacker configures an alert rule with a webhook URL pointing to:
- Cloud metadata services: `http://169.254.169.254/latest/meta-data/`
- Localhost / internal services: `http://localhost:8000/`, `http://127.0.0.1/`, `http://0.0.0.0/`
- Private network ranges: `http://10.0.0.1/`, `http://192.168.1.1/`, `http://172.16.0.1/`
The system would be vulnerable to **Server-Side Request Forgery (SSRF)**.

### Stage 12 Safeguards:
1. `validate_webhook_url`: Resolves DNS and blocks loopback addresses (`127.0.0.0/8`), private subnets (RFC 1918), link-local cloud metadata addresses (`169.254.0.0/16`), and non-HTTP schemes (e.g. `file://`, `gopher://`).
2. Configurable whitelist/blacklist and explicit safe local development override mode.
3. Masking of webhook secrets and tokens in all database logs and error messages.

---

## 5. Architectural Gap Analysis & Proposed Additions

| Capability Required | Existing State | Stage 12 Implementation Plan |
|---|---|---|
| **Alert Rules Management** | Basic `AlertRule` table with name, type, and threshold. | Expand `AlertRule` with multi-cloud scoping, severity thresholds, percentage/absolute deviation triggers, cooldown windows, and escalation policies. Add dedicated REST APIs. |
| **Alert Lifecycle & Instances** | No `AlertInstance` model connecting rules to anomalies. | Create `AlertInstance` model tracking `OPEN`, `ACKNOWLEDGED`, `INVESTIGATING`, `RESOLVED`, `SUPPRESSED`, `CLOSED` lifecycle states with full `AlertHistory` audit trail. |
| **Deduplication & Cooldown** | No alert deduplication. | Implement deterministic composite deduplication keys (`hash(account_id, service_name, anomaly_date, rule_id)`) and configurable cooldown suppression. |
| **Transactional Outbox** | No outbox pattern; direct dispatch risks data loss. | Create `NotificationOutbox` and `NotificationDeliveryAttempt` models ensuring atomic outbox writes and asynchronous retry processing with exponential backoff. |
| **Multi-Channel Dispatch** | Enum exists, but no provider classes. | Implement `InAppNotificationProvider`, `EmailNotificationProvider` (SMTP with safe local dev mode), and `WebhookNotificationProvider` (with SSRF protection). |
| **In-App Notification Center** | No in-app notification center. | Build `InAppNotification` table, REST endpoints (`/unread-count`, `/mark-all-read`), `NotificationBell.tsx`, and `NotificationCenter.tsx`. |
| **Notification Preferences** | None. | Create `NotificationPreference` model and user preferences API for quiet hours and digest frequencies. |

---

## 6. Migration Chain Verification

- Current latest migration: `009_recommendation_waste_workspace.py` (down_revision = `008_ai_finops_copilot`).
- Stage 12 migration will be: `010_cost_anomaly_alerts_hub.py` (down_revision = `009_recommendation_waste_workspace`).
