# CloudSage FinOps Intent Classification and Entity Extraction

## 1. Overview

The CloudSage FinOps Copilot features a specialized intent classification engine tailored strictly to the cloud financial management domain. Every user prompt is classified into one of **15 canonical FinOps intents** and enriched with structured entities.

---

## 2. The 15 Canonical FinOps Intents

| # | Intent Name (`CopilotIntent`) | Domain Scope | Example User Query | Target Dataset |
| :-: | :--- | :--- | :--- | :--- |
| **1** | `TOTAL_CLOUD_SPEND` | Multi-cloud expenditure totals, aggregate bills, budget sums | *"What is our total cloud spend this month?"* | `billing_records` |
| **2** | `PROVIDER_COST_COMPARISON` | Comparing AWS, Azure, and GCP costs and percentages | *"Compare spending between AWS and Azure"* | `billing_records` |
| **3** | `SERVICE_COST_BREAKDOWN` | Top-N services, service-level cost breakdowns | *"What are our top 5 most expensive cloud services?"* | `billing_records` |
| **4** | `RESOURCE_COST_ANALYSIS` | Resource ARN/ID cost lookup, top spending resources | *"What is the cost of resource i-0123456789?"* | `billing_records` |
| **5** | `COST_TREND_ANALYSIS` | Time-series daily spend, MoM/WoW trajectory, forecasts | *"Show daily cost trends over the past 30 days"* | `billing_records` |
| **6** | `COST_ANOMALY_EXPLANATION` | Explaining detected anomalies, spikes, sudden surges | *"Why did our AWS bill spike unexpectedly this week?"* | `cost_anomalies` |
| **7** | `WASTE_DETECTION_ANALYSIS` | Idle VMs, unattached disks, orphaned snapshots, idle IPs | *"What cloud waste was detected across our accounts?"* | `waste_detections` |
| **8** | `OPTIMIZATION_RECOMMENDATIONS` | Prioritized optimization proposals, rightsizing, tiering | *"What are your top recommendations to reduce cloud spend?"* | `recommendations` |
| **9** | `SAVINGS_OPPORTUNITY` | Potential monthly and annual dollar savings aggregation | *"How much potential savings can we achieve across all clouds?"* | `recommendations` |
| **10** | `RESOURCE_UTILIZATION` | CPU, memory, disk, network metrics and low utilization | *"Show inventory and utilization metrics for virtual machines"* | `cloud_resources` |
| **11** | `OWNER_COST_ANALYSIS` | Cost allocation by owner tag or engineering team | *"How much did the data engineering team spend this month?"* | `billing_records` |
| **12** | `COST_CENTER_ANALYSIS` | Grouping expenditure by financial cost center code | *"Show cloud spend grouped by cost center"* | `billing_records` |
| **13** | `BILLING_DATA_QUALITY` | Untagged resources, missing records, FOCUS compliance | *"Are there untagged resources or missing billing records?"* | `billing_records` |
| **14** | `GENERAL_FINOPS_QUESTION` | Conceptual definitions (FOCUS 1.0, amortized vs unblended) | *"What is FOCUS 1.0 and how does CloudSage use it?"* | N/A (Knowledge base) |
| **15** | `UNSUPPORTED_OR_AMBIGUOUS_QUERY` | Out-of-domain or ambiguous inquiries (weather, poetry, etc.) | *"What is the weather forecast in Seattle today?"* | N/A (Polite redirection) |

---

## 3. Classification Algorithm & Scoring

Intent classification operates via weighted pattern matching with contextual category boosting:
1. **Multi-Pattern Aggregation**: Queries are evaluated against regular expression banks. For each match, `score += len(matches) * 2`.
2. **Specialized Category Boost**: Specialized analytical intents (Anomalies, Waste, Recommendations, Savings, Comparisons, Resource Cost, Cost Center, Data Quality) receive an additional `+3` weighting over generic spend inquiries.
3. **Intent Score Maximization**: The intent achieving the highest cumulative score is selected (`best_intent = max(intent_scores, key=intent_scores.get)`).
4. **Domain Terminology Fallback**: Queries containing FinOps concepts (e.g. `FOCUS`, `unblended`, `rightsizing`, `amortized`) map to `GENERAL_FINOPS_QUESTION`, while financial tokens (`cost`, `spend`, `budget`, `bill`) map to `TOTAL_CLOUD_SPEND`. All other out-of-domain questions resolve cleanly to `UNSUPPORTED_OR_AMBIGUOUS_QUERY`.

---

## 4. Entity Extraction Rules

The entity extraction engine extracts 5 core FinOps dimensions:

### 1. Cloud Providers
- Patterns: `aws`, `amazon`, `azure`, `microsoft`, `gcp`, `google`
- Canonical Output: `["AWS"]`, `["AZURE"]`, `["GCP"]`

### 2. Hyperscaler Services
- Standardizes service aliases into canonical FOCUS names:
  - `ec2` $\rightarrow$ `Amazon EC2`
  - `s3` $\rightarrow$ `Amazon S3`
  - `rds` $\rightarrow$ `Amazon RDS`
  - `azure vm` $\rightarrow$ `Virtual Machines`
  - `blob` $\rightarrow$ `Blob Storage`
  - `bigquery` $\rightarrow$ `BigQuery`
  - `gce` $\rightarrow$ `Compute Engine`

### 3. Resource Identifiers
- Extracts provider-specific resource syntax:
  - AWS EC2: `i-[a-z0-9]{8,17}`
  - AWS EBS: `vol-[a-z0-9]{8,17}`
  - AWS Snapshot: `snap-[a-z0-9]{8,17}`

### 4. Temporal Windows
- Normalizes relative time phrases into strict UTC datetime boundaries:
  - `"last 7 days"` $\rightarrow$ `now - 7 days` to `now`
  - `"yesterday"` $\rightarrow$ `now - 1 day` to `now`
  - `"last month"` $\rightarrow$ `now - 60 days` to `now - 30 days`
  - Default: `last 30 days`

### 5. Tag & Cost Center Filters
- Extracts owner and cost-center key-value pairs:
  - `owner: data_engineering` $\rightarrow$ `{"owner": "data_engineering"}`
  - `cost-center: CC-9988` $\rightarrow$ `{"cost_center": "CC-9988"}`

