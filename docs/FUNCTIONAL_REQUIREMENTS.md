# CloudSage: Functional Requirements Document (FRD)

## 1. Introduction and Scope

This document details the functional specifications for the CloudSage Multi-Cloud FinOps Copilot platform. CloudSage provides a unified, cross-cloud financial intelligence layer across Amazon Web Services (AWS), Microsoft Azure, and Google Cloud Platform (GCP).

---

## 2. Module A: Multi-Cloud Data Ingestion

The ingestion subsystem is responsible for acquiring billing, usage, and infrastructure metadata from disparate sources reliably and idempotently.

### A.1 AWS Ingestion
- **Data Source**: AWS Cost and Usage Report (CUR) 2.0 (CSV and Parquet formats) delivered to S3, augmented by AWS Cost Explorer API summaries.
- **Payload Attributes**: Ingests line item details including `lineItem/ResourceId`, `lineItem/UnblendedCost`, `lineItem/UsageStartDate`, `lineItem/UsageType`, `pricing/unit`, `resourceTags/user:*`, and AWS region.
- **Utilization Telemetry**: Ingestion of AWS CloudWatch metrics (CPUUtilization, NetworkIn/Out, DiskRead/WriteOps).

### A.2 Azure Ingestion
- **Data Source**: Microsoft Azure Cost Management scheduled exports delivered to Azure Blob Storage (Enterprise Agreement, MCA, or Pay-As-You-Go subscription levels).
- **Payload Attributes**: Ingests line items including `ResourceId`, `CostInBillingCurrency`, `UsageDateTime`, `MeterCategory`, `MeterSubCategory`, `ResourceGroup`, `SubscriptionId`, `Tags`, and resource location.
- **Utilization Telemetry**: Ingestion of Azure Monitor metrics (Percentage CPU, Network In Total, Disk Read/Write Bytes).

### A.3 GCP Ingestion
- **Data Source**: Google Cloud Platform Cloud Billing export to BigQuery / Google Cloud Storage (Standard and Detailed usage cost exports in JSON/CSV/Parquet).
- **Payload Attributes**: Ingests line items including `resource.name`, `cost`, `usage_start_time`, `service.description`, `sku.description`, `project.id`, `labels`, and region/zone.
- **Utilization Telemetry**: Ingestion of GCP Cloud Monitoring metrics (`compute.googleapis.com/instance/cpu/utilization`, network throughput).

### A.4 Synthetic & File-Based Seed Ingestion
- **Local/Test Capability**: Direct ingestion of structured CSV, JSON, and Parquet sample datasets mimicking multi-cloud billing files for offline validation, staging, and automated integration test suites.
- **Dataset Seed Engine**: Pre-packaged synthetic datasets containing known, deterministic waste and anomaly benchmarks.

### A.5 Ingestion Cadence and Idempotency
- **Scheduled Ingestion**: Configurable cron-driven pipeline (hourly, daily, or upon SQS/EventGrid/PubSub object notification).
- **Idempotent Processing**: Each ingestion batch computes SHA-256 content hashes and composite idempotency keys (`provider:account_id:billing_period:line_item_id`) to prevent duplicate billing records during retries.
- **Incremental Loading**: Tracks ingestion watermark timestamps per cloud account to import only net-new or revised billing records.

### A.6 Secure Cloud API Integration Roadmap
- **IAM Role Delegation (AWS)**: Cross-Account IAM Roles with External ID verification; no static access keys.
- **Service Principal Authentication (Azure)**: OIDC federation / Azure App Registration with limited read permissions (`Cost Management Reader`, `Monitoring Reader`).
- **Workload Identity Federation (GCP)**: Service Accounts with `Billing Account Viewer` and `Monitoring Viewer` roles via keyless Workload Identity.

---

## 3. Module B: Unified Data Normalization

Raw cloud billing data is transformed into a standardized canonical model compliant with the **FinOps Open Cost & Usage Specification (FOCUS™ 1.0)**.

### B.1 Canonical Billing Schema
Every ingested line item is mapped to the standard schema:

| Canonical Field | Description | Type | Source Example (AWS / Azure / GCP) |
| :--- | :--- | :--- | :--- |
| `record_id` | Unique UUID for the normalized line item | UUID | Primary Key |
| `provider` | Cloud provider identifier (`AWS`, `AZURE`, `GCP`) | Enum | Derived |
| `billing_account_id`| Master/Payer account or billing account ID | String | `lineItem/UsageAccountId` / `BillingAccountId` / `billing_account_id` |
| `subscription_id` | Sub-account, subscription, or project ID | String | `lineItem/UsageAccountId` / `SubscriptionId` / `project.id` |
| `resource_id` | Globally unique cloud resource identifier | String | ARN / Azure Resource ID / GCP Resource URI |
| `resource_name` | Human-readable name or instance identifier | String | Tag `Name` / VM Name / GCP instance name |
| `service_category` | High-level taxonomy (`COMPUTE`, `STORAGE`, `DB`, `NETWORK`, `AI_ML`, `OTHER`)| Enum | Mapped via taxonomy engine |
| `service_name` | Cloud service name | String | `AmazonEC2` / `Virtual Machines` / `Compute Engine` |
| `region` | Normalized geographical region | String | `us-east-1` / `eastus` / `us-central1` |
| `usage_start_time` | UTC timestamp of billing interval start | Timestamp | ISO 8601 UTC |
| `usage_end_time` | UTC timestamp of billing interval end | Timestamp | ISO 8601 UTC |
| `usage_quantity` | Billed usage volume | Numeric(18,6)| `lineItem/UsageAmount` / `UsageQuantity` / `usage.amount` |
| `usage_unit` | Standardized unit (`HOURS`, `GB_MONTH`, `REQUESTS`, etc.) | String | Normalized unit string |
| `unblended_cost` | Actual net cash expenditure in USD | Numeric(12,4)| Converted to USD standard |
| `pricing_model` | Pricing mechanism (`ON_DEMAND`, `RESERVED`, `SPOT`, `SAVINGS_PLAN`)| Enum | Evaluated pricing model |
| `tags` | Sanitized key-value metadata dictionary | JSONB | Normalized tags (lowercase keys, stripped whitespace)|

### B.2 Normalization Rules
1. **Currency Normalization**: All monetary figures are converted to USD at the exchange rate corresponding to `usage_start_time`.
2. **Service Classification Engine**: Rules-based lookup categorizing hundreds of hyperscaler SKUs into canonical categories (`COMPUTE`, `STORAGE`, `DATABASE`, `NETWORKING`, `ANALYTICS`, `AI_ML`, `SECURITY`, `MANAGEMENT`).
3. **Tag Normalization**: Unifies heterogeneous case conventions (e.g., `Owner`, `owner`, `OWNER` -> `owner`) and extracts standard FinOps tags (`owner`, `environment`, `costcenter`, `application`, `project`).

---

## 4. Module C: Cloud Waste Detection Engine

The Waste Detection Engine executes deterministic analytical heuristics across unified billing records and resource telemetry to identify preventable expenditure.

```
+------------------------------------------------------------------------------------+
|                             WASTE DETECTION HEURISTICS                             |
+--------------------------+---------------------------------------------------------+
| Waste Category           | Detection Criteria & Thresholds                         |
+--------------------------+---------------------------------------------------------+
| Idle Virtual Machines    | - Average CPU Utilization < 5.0% over 7 consecutive days|
|                          | - Maximum Network IO < 5 MB/day                         |
|                          | - Zero active database connections (if applicable)      |
+--------------------------+---------------------------------------------------------+
| Oversized Compute        | - Peak CPU Utilization < 15.0% over 14 consecutive days |
| Instances                | - Peak Memory Utilization < 20.0%                       |
|                          | - Candidate for 1-2 tier downsizing (e.g. 2xlarge->med) |
+--------------------------+---------------------------------------------------------+
| Unattached Storage Disks | - AWS EBS: Volume state = 'available' (unattached) > 3d |
|                          | - Azure: Managed Disk with managedBy = null > 3 days    |
|                          | - GCP: Persistent Disk with in_use_by = empty > 3 days  |
+--------------------------+---------------------------------------------------------+
| Orphaned Snapshots       | - Storage snapshots older than organizational policy    |
|                          |   (e.g., age > 90 days)                                 |
|                          | - Snapshots whose source volume has been deleted        |
+--------------------------+---------------------------------------------------------+
| Idle Networking & IPs    | - Unassociated AWS Elastic IPs (EIPs)                   |
|                          | - Azure Public IP addresses unlinked to any NIC         |
|                          | - GCP Static External IPs reserved without instance     |
|                          | - Load Balancers (ALB/ELB/Gateway) routing 0 requests   |
+--------------------------+---------------------------------------------------------+
| Continuous Non-Prod      | - Instances tagged `environment` IN ('dev','test','qa') |
| Environments             |   running continuously 24x7 without shutdown schedules  |
+--------------------------+---------------------------------------------------------+
```

---

## 5. Module D: Cost Anomaly Detection Engine

The Cost Anomaly Detection Engine continuously evaluates spending patterns against rolling historical baselines to flag cost spikes within minutes of new data ingestion.

### D.1 Baseline Modeling
- **Rolling Window**: Establishes a 30-day trailing baseline for each `(provider, service, account, region)` tuple.
- **Statistical Dispersion**: Computes rolling mean ($\mu$), rolling standard deviation ($\sigma$), Median, and Interquartile Range (IQR).

### D.2 Detection Algorithms
1. **Z-Score Spike Detection**:
   $$\text{Z-Score} = \frac{\text{Cost}_{\text{current}} - \mu_{30\text{d}}}{\sigma_{30\text{d}}}$$
   An anomaly is flagged if $\text{Z-Score} \ge 3.0$ and absolute daily delta $> \$50.00$.
2. **IQR Fences**:
   Identifies outliers where $\text{Cost}_{\text{current}} > Q_3 + 2.5 \times \text{IQR}$.
3. **Change-Point Detection**:
   Flags structural step-function shifts in baseline spend (e.g., a service expenditure doubling and persisting for $> 48$ hours).

### D.3 Attribution and Root-Cause Diagnostics
When an anomaly is detected, the engine executes an automated breakdown query to pinpoint:
- Specific Cloud Service (e.g., `AWS CloudWatch Logs` or `GCP BigQuery`).
- Specific Resource ID / Cluster.
- Initiating Account, Region, and associated Tags (`owner`, `project`).
- Cost driver: Volume surge vs. Unit price shift vs. Tier change.

---

## 6. Module E: AI FinOps Copilot

The AI FinOps Copilot provides natural language conversational analytics for both technical and non-technical stakeholders.

### E.1 Natural Language Query Support
The Copilot resolves core enterprise queries including:
- *"Why did our AWS spending increase this week?"*
- *"Which cloud provider costs us the most?"*
- *"What are our top five wasteful resources?"*
- *"How much money can we potentially save?"*
- *"Which resources have no owner?"*
- *"Compare Azure and AWS spending over the last 90 days."*
- *"Show our monthly cloud expenditure broken down by environment."*

### E.2 Deterministic Grounding & Anti-Hallucination Protocol
> [!IMPORTANT]
> The AI Copilot is **never** permitted to guess, fabricate, or hallucinate financial figures.

```
User Prompt: "Why did AWS spend jump this week?"
                    │
                    ▼
         Intent & Entity Extractor
                    │
                    ▼
      Schema-Constrained SQL Generator (NL2SQL)
                    │
                    ▼
     SQL Validator & AST Safety Guard
     - Disallow INSERT / UPDATE / DELETE / DROP
     - Enforce read-only connection
     - Validate against canonical table schema
                    │
                    ▼
      Execute Query on PostgreSQL Database
                    │
                    ▼
       Return Raw Numerical Record Proof
                    │
                    ▼
       LLM Synthesizes Natural Language Explanation
       - Cites exact figures returned by database
       - Displays tabular proof & generated SQL
```

---

## 7. Module F: Advisory Recommendation Engine

The Recommendation Engine transforms detected waste into prioritized, actionable remediation proposals.

### F.1 Recommendation Taxonomy
- **TERMINATE**: Decommission completely unattached, orphaned, or obsolete assets (e.g., unattached EBS volumes, orphan disks).
- **RIGHTSIZE**: Transition over-provisioned instances to smaller instance families or sizes.
- **SCHEDULE**: Implement automated start/stop schedules for non-production environments (e.g., shutting down dev VMs on weeknights and weekends).
- **PURGE_SNAPSHOT**: Delete redundant snapshots older than compliance retention windows.
- **RELEASE_IP**: Release unassociated static public IP addresses.

### F.2 Scoring and Prioritization Matrix
Recommendations are assigned a Priority Score ($P1$ to $P4$) derived from:
- **Financial Impact**: Projected Monthly Savings ($S_{\text{monthly}}$).
- **Implementation Effort**: Low (1-click/single script), Medium (coordination required), High (downtime risk).
- **Operational Risk Level**:
  - `NONE`: Zero impact to live traffic (e.g., deleting unattached volume unlinked for 30 days).
  - `LOW`: Safe non-production adjustment.
  - `MEDIUM`: Downsizing instance requiring restart.
  - `HIGH`: Modification affecting production resource.

### F.3 Human-in-the-Loop Lifecycle Management
Recommendations strictly traverse audited states:
$$\text{PROPOSED} \longrightarrow \text{UNDER\_REVIEW} \longrightarrow \begin{cases} \text{APPROVED} \longrightarrow \text{IMPLEMENTED} \\ \text{DISMISSED} \\ \text{SNOOZED (30 Days)} \end{cases}$$

---

## 8. Module G: Enterprise Dashboard

A responsive, high-performance web dashboard providing role-tailored financial visualizations:
- **Executive KPI Cards**: Total Spend MTD, Projected Monthly Run Rate, Month-over-Month Delta (%), Identified Waste ($), Realized Savings ($).
- **Multi-Cloud Spend Distribution**: Donut and bar charts comparing AWS, Azure, and GCP spend.
- **Historical Spend Trends**: Interactive time-series charts (Daily/Monthly) with stackable breakdown by Service Category or Cloud Provider.
- **Waste & Savings Radar**: Visual breakdown of savings by category (Idle Compute, Unattached Disks, Snapshots, Rightsizing).
- **Active Anomaly Feed**: High-visibility alert cards displaying active spending spikes with direct links to root-cause diagnoses.
- **Tagging Hygiene Meter**: Gauge chart displaying overall enterprise tagging compliance percentage ($T_{\text{tagged}} / T_{\text{total}}$).

---

## 9. Module H: Alerts and Notifications

### H.1 Notification Triggers
- **Budget Threshold Alerts**: Spend crosses 80%, 100%, or 120% of defined monthly departmental budgets.
- **Cost Anomaly Alerts**: Anomaly Engine flags a statistical surge ($\text{Z-score} \ge 3.0$).
- **High-Value Waste Detection**: Newly discovered waste item with monthly savings $> \$500.00$.
- **Recommendation Status Change**: Notification when an optimization plan is submitted for review or approved.

### H.2 Dispatch Channels & History
- Delivery via **Slack Webhooks**, **Microsoft Teams**, **Email (SMTP/SendGrid)**, and **Generic Webhooks (PagerDuty/ServiceNow)**.
- Full notification history tracking delivery timestamps, payload content, recipient addresses, and HTTP response codes.
