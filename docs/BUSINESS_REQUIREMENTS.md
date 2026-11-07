# CloudSage: Business Requirements Document (BRD)

## 1. Context and Problem Statement

Modern enterprise technology infrastructure is predominantly multi-cloud. Organizations deliberately deploy workloads across Amazon Web Services (AWS), Microsoft Azure, and Google Cloud Platform (GCP) to prevent vendor lock-in, optimize latency, utilize best-of-breed managed services, and adhere to regional compliance.

However, decentralized cloud provisioning creates massive financial and operational inefficiencies. Cloud costs represent one of the fastest-growing operating expenditures (OpEx) for tech-enabled enterprises, yet up to **30% to 35% of overall cloud expenditure is squandered on idle, oversized, or unmanaged infrastructure**.

CloudSage is commissioned to solve these specific systemic business challenges.

---

## 2. In-Depth Analysis of Core Business Problems

### Problem 1: Fragmented Billing Data Across Disparate Clouds
* **The Challenge**: Each hyperscaler maintains an entirely proprietary cost reporting structure:
  - AWS exposes detailed CSV/Parquet via AWS Cost and Usage Report (CUR) with over 100 dynamic columns.
  - Microsoft Azure generates Cost Management Exports formatted around Subscriptions, Resource Groups, and Azure Meter IDs.
  - Google Cloud Platform outputs billing exports to BigQuery or Cloud Storage with nested JSON schemas, SKU IDs, and project hierarchies.
* **Business Impact**: Cross-cloud financial aggregation requires finance and engineering teams to spend hundreds of manual hours writing custom ETL scripts, reconciling currency fluctuations, and reconciling billing periods. Reports are inherently backward-looking, arriving weeks after costs are incurred.

### Problem 2: Unnecessary Spending from Idle and Oversized Resources
* **The Challenge**: Engineers commonly provision compute instances sized for peak anticipated traffic (or worst-case scenarios) without downscaling when baseline utilization drops. Non-production environments (dev, test, QA, staging) routinely run 24 hours a day, 7 days a week, despite being active only 40 to 50 hours per week.
* **Business Impact**: Organizations pay full on-demand or reservation rates for compute capacity whose average CPU utilization remains below 5% and memory utilization below 15%. This unutilized capacity yields zero business value while draining capital.

### Problem 3: Forgotten Storage Disks, Snapshots, and Abandoned Infrastructure
* **The Challenge**: When virtual machines (EC2, Azure VM, GCP Compute Engine) are terminated, attached block storage volumes (AWS EBS, Azure Managed Disks, GCP Persistent Disks) often remain unattached in available states. Similarly, automated backup snapshot schedules continue generating daily or hourly snapshots long after the parent workloads have been decommissioned. Unassociated static IP addresses and idle load balancers with zero targets also incur hourly fees.
* **Business Impact**: Storage and networking waste accumulates silently as "micro-leaks". Because individual disks or snapshots cost tens to hundreds of dollars monthly, they evade single-item budget review thresholds, but collectively drain tens of thousands of dollars annually.

### Problem 4: Delayed Detection of Unexpected Cost Increases
* **The Challenge**: In decentralized DevOps workflows, code deployments, recursive API calls, misconfigured Auto-Scaling groups, or rogue data pipeline loops can cause cloud spend to explode overnight. Traditional billing notifications typically trigger only when monthly budget ceilings are breached.
* **Business Impact**: By the time an engineering team or finance analyst notices an anomaly via an end-of-month invoice, the enterprise has absorbed catastrophic financial losses. Detecting anomalies within minutes or hours rather than weeks prevents severe budget blowouts.

### Problem 5: Deficient Resource Ownership, Tagging Hygiene, and Cost Allocation
* **The Challenge**: Cloud resources are frequently spun up without standardized metadata tags denoting `Owner`, `Environment`, `Department`, `CostCenter`, or `Application`. Tagging conventions vary widely across teams (e.g., `Env`, `environment`, `stage`, `STAGE`).
* **Business Impact**: Without accurate allocation metadata, the enterprise cannot establish chargeback or showback accounting. Shared infrastructure costs cannot be accurately attributed to business units, obscuring the true unit economics of software products and services.

### Problem 6: Information Asymmetry and Lack of Accessible Cost Intelligence
* **The Challenge**: Understanding cloud cost drivers requires deep familiarity with cloud architectures, SKU descriptions, and billing query syntax. Business leaders, product managers, and finance analysts cannot independently extract answers to fundamental operational questions (e.g., *"Why did AWS spend jump 25% last week?"* or *"Which team owns the top 10 costliest resources?"*).
* **Business Impact**: Decision-makers remain dependent on scarce cloud engineering bandwidth to construct ad-hoc reports, causing communication lag, uninformed strategic decisions, and friction between engineering and finance.

---

## 3. Business Objectives and Success Targets

CloudSage addresses these enterprise challenges with the following business objectives:

```
+------------------------------------------------------------------------------------+
|                               BUSINESS TARGETS                                     |
+------------------------------------+-----------------------------------------------+
| Metric / Objective                 | Target Value                                  |
+------------------------------------+-----------------------------------------------+
| Cloud Waste Reduction              | Identify 20% to 35% in direct cost savings    |
| Ingestion & Normalization Latency  | Normalization complete within < 10 minutes    |
| Anomaly Time-to-Detect (TTD)       | Anomaly alert dispatched within < 15 minutes  |
| Tagging Compliance Auditing        | 100% auditing of unowned / untagged resources |
| Self-Service Query Adoption        | Reduce engineering ad-hoc reporting by > 75%  |
| Advisory Safety Guarantee          | 100% human-verified actions (0 auto-destruct) |
+------------------------------------+-----------------------------------------------+
```

---

## 4. Alignment with the FinOps Lifecycle

CloudSage implements the three foundational phases established by the FinOps Foundation:

```
               +-------------------------------------------+
               |             1. INFORM                     |
               |  - Unified Multi-Cloud Visibility         |
               |  - Granular Cost Allocation & Tagging     |
               |  - Conversational AI Copilot              |
               |  - Real-Time Budget & Trend Dashboards    |
               +---------------------+---------------------+
                                     |
                                     v
               +-------------------------------------------+
               |            2. OPTIMIZE                    |
               |  - Continuous Waste Detection (Compute/Stg)|
               |  - Statistical Cost Anomaly Detection     |
               |  - Prioritized Advisory Recommendations   |
               |  - Rightsizing & Idling Analysis          |
               +---------------------+---------------------+
                                     |
                                     v
               +-------------------------------------------+
               |             3. OPERATE                    |
               |  - Human-in-the-Loop Approval Workflows   |
               |  - Multi-Channel Alerts (Slack/Email)     |
               |  - Engineering Accountability Metrics     |
               |  - Continuous Verification & Governance   |
               +-------------------------------------------+
```

---

## 5. Advisory-Only Mandate & Operational Safety

Enterprise environments mandate strict operational safeguards. Automated modification or deletion of cloud infrastructure carries immense risk of downtime, customer data loss, and SLA penalties.

### The CloudSage Advisory Pledge:
1. **Advisory by Design**: CloudSage recommendations are advisory proposals. The system will **never** trigger autonomous destructive operations (e.g., `ec2:TerminateInstances`, `az disk delete`, `gcloud compute instances delete`).
2. **Detailed Impact Evidence**: Every recommendation provides supporting utilization graphs, historical cost run-rates, risk ratings, and step-by-step remediation commands.
3. **Formal Approval States**: Proposed actions progress through audited operational states:
   `PROPOSED` -> `UNDER_REVIEW` -> `APPROVED` -> `DISMISSED` or `IMPLEMENTED`.
4. **Separation of Duties**: Financial analysts can review and endorse recommendations, but only authorized Engineering Leads or FinOps Engineers can formally approve remediation plans.

---

## 6. Financial Impact & Value Realization Model

```
Gross Cloud Spend ($10M / Year)
       │
       ├──> 30% Identified Inefficiencies (~$3,000,000)
       │       ├── Idle VMs & Instances (~$1,200,000)
       │       ├── Unattached Disks & Forgotten Snapshots (~$800,000)
       │       ├── Oversized Compute Instances (~$700,000)
       │       └── Unused Networking & Orphaned IPs (~$300,000)
       │
       └──> CloudSage Realized Annualized Net Savings: $1,500,000 - $2,250,000
            (Assuming conservative 50% - 75% recommendation execution rate)
```

Beyond direct dollar savings, CloudSage yields substantial indirect economic benefits:
- **Engineering Productivity**: Eliminates manual cross-cloud billing spreadsheet compilation.
- **Budget Predictability**: Quenches sudden billing surprises through rapid anomaly detection.
- **Executive Alignment**: Unifies executive, finance, and engineering stakeholders through shared, verified data.
