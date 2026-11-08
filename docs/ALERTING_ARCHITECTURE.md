# CloudSage Alerting & Enterprise Notification Hub Architecture

## 1. System Overview

Stage 12 transforms CloudSage from an analytical cost anomaly observer (Stage 7) into an active, enterprise-grade alerting and notification platform. The Alerting and Notification Hub continuously evaluates newly detected and materially changed multi-cloud cost anomalies against configurable multi-dimensional alert rules, applies deterministic deduplication and cooldown suppression, dispatches multi-channel notifications via a transactional outbox pattern, and provides an interactive in-app notification center.

```mermaid
flowchart TD
    subgraph Detection [Stage 7 Cost Anomaly Detection]
        CAD[Cost Anomaly Detector] --> |DB Commit| CA[(Cost Anomalies)]
    end

    subgraph Hub [Stage 12 Alerting & Notification Hub]
        Worker[Celery / Async Worker] --> |Poll Unprocessed| CA
        Worker --> AR[AlertRuleEvaluationService]
        
        Rules[(Alert Rules)] --> |Match Dimensions| AR
        
        AR --> Dedup{Deduplication & Cooldown}
        Dedup --> |Within Cooldown & No Escalation| Suppress[Increment Trigger Count & Suppress]
        Dedup --> |New / Cooldown Expired / Escalation| AlertInst[(Alert Instances)]
        
        AlertInst --> History[(Alert History Audit)]
        AlertInst --> |Atomic DB Tx| Outbox[(Notification Outbox)]
        AlertInst --> |Atomic DB Tx| InApp[(In-App Notifications)]
        
        Dispatcher[NotificationDispatcherService] --> |Poll Pending| Outbox
        Dispatcher --> Attempts[(Delivery Attempts Ledger)]
        
        Dispatcher --> ProviderEmail[Email Provider (SMTP / Mock)]
        Dispatcher --> ProviderWebhook[Webhook Provider (Custom HTTP)]
        Dispatcher --> ProviderSlack[Slack Provider]
        Dispatcher --> ProviderTeams[Microsoft Teams Provider]
    end

    subgraph Frontend [React Enterprise Web UI]
        InApp --> Bell[Notification Bell Badge]
        InApp --> Center[Notification Center Page]
        AlertInst --> Mgt[Alert Management Table]
        AlertInst --> Detail[Alert Deep-Dive View]
        Outbox --> DLQ[Delivery Status & DLQ Panel]
    end
```

---

## 2. Decoupled Architecture & Fault Isolation

A core architectural tenet of Stage 12 is **non-blocking failure isolation**:

1. **Anomaly Detection Integrity**: The Stage 7 cost anomaly detection engine and database transactions must never fail or roll back due to alerting or notification errors.
2. **Transaction Savepoint Isolation**: When anomalies are evaluated within worker routines, evaluation is executed within nested transaction savepoints (`with db.begin_nested():`) or isolated jobs. Any rule matching error, template rendering issue, or outbox serialization fault is logged and quarantined without rolling back underlying anomaly records.
3. **Decoupled Asynchronous Delivery**: The evaluation engine only writes notification entries to the `notification_outbox` table within the local database transaction. Outbound network I/O (SMTP, HTTPS Webhooks, Slack Webhooks) is executed strictly asynchronously by the `NotificationDispatcherService`. Network latency, external timeouts, or relay failures never block API request-response lifecycles or detection pipelines.

---

## 3. Data Flow Architecture

The end-to-end data flow operates in 6 distinct stages:

```
[Cost Anomaly Detected] 
          │
          ▼
[Rule Multi-Dimensional Matcher] (Provider, Account, Service, Region, Thresholds)
          │
          ▼
[Deduplication & Cooldown Filter]
          ├──> If Duplicated within Cooldown: Increment trigger_count, suppress notification
          ├──> If Severity Escalated: Bypass cooldown, escalate level, record audit
          └──> If New / Expired: Create AlertInstance, record AlertHistory
                    │
                    ▼
[Transactional Outbox Enqueueing] (Atomic DB commit of AlertInstance + Outbox + InApp)
          │
          ▼
[Asynchronous Dispatcher] (Batch worker, latency measurement, delivery attempts)
          ├──> Success: Mark DELIVERED, record latency
          └──> Failure: Increment attempts, compute exponential backoff (2^attempts * 60s)
                    └──> If attempts >= 5: Mark DEAD_LETTERED (DLQ)
```

---

## 4. Multi-Cloud Scope & Normalization

The alerting hub natively supports multi-cloud operations across **Amazon Web Services (AWS)**, **Microsoft Azure**, and **Google Cloud Platform (GCP)**:

- **AWS**: Monitors EC2 compute surges, S3 storage expansion, RDS IOPS anomalies, and cross-AZ data transfer spikes.
- **Azure**: Monitors Virtual Machine spikes, Blob storage growth, Cosmos DB request unit surges, and ExpressRoute bandwidth anomalies.
- **GCP**: Monitors Compute Engine capacity expansions, BigQuery analytical scan spikes, Cloud Storage class transitions, and Interconnect egress.
- **Provider Agnostic ("ALL")**: Enterprise rules can target global spend spikes spanning all connected hyperscaler accounts.

---

## 5. Strict Zero Float Guarantee

In compliance with enterprise FinOps standards across CloudSage:
- All financial metrics (`current_cost`, `expected_cost`, `excess_cost`, `percentage_deviation`, `threshold_value`) are represented in Python as `decimal.Decimal` and persisted in PostgreSQL as `Numeric(18, 4)`.
- Floating-point representations (`float`) are strictly forbidden across models, schemas, and arithmetic calculations, preventing floating-point rounding errors in audit trails and notifications.
