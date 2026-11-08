# Cloud Cost Analytics & Historical Trends

## 1. Overview

The Cloud Cost Analytics module provides deep visibility into multi-cloud spending patterns over time. It normalizes provider-specific time granularities into consistent daily and monthly time series, allowing engineering teams and financial analysts to explore expenditure drivers, service allocations, and historical trends.

---

## 2. Time-Series Aggregation Logic

### 2.1 Daily Time Series
Expenditure line items from `billing_records` are grouped by normalized usage date (`func.date(BillingRecord.usage_start_time)`):

$$\text{Daily Total}_d = \sum_{r \in R_d} \text{unblended\_cost}_r$$

$$\text{AWS}_d = \sum_{r \in R_{d, \text{AWS}}} \text{unblended\_cost}_r, \quad \text{Azure}_d = \sum_{r \in R_{d, \text{AZURE}}} \text{unblended\_cost}_r, \quad \text{GCP}_d = \sum_{r \in R_{d, \text{GCP}}} \text{unblended\_cost}_r$$

### 2.2 Monthly Time Series
For longer observation windows (trailing 3, 6, or 12 months), daily data points are rolled up into month buckets (`YYYY-MM`), providing executive trend trajectories and seasonal comparison capabilities.

### 2.3 Anomaly Event Overlays
The trend visualizer overlays detected anomaly indicators on specific dates where a statistical spike (`CostAnomaly`) occurred. When an analyst hovers over or clicks an anomaly-flagged date, the UI displays the affected service, deviation score, and explanation summary.

---

## 3. Service Breakdown Analytics

CloudSage groups expenditures by standardized hyperscaler service names and normalized categories:
- **COMPUTE**: AWS EC2, Azure Virtual Machines, GCP Compute Engine.
- **STORAGE**: AWS S3, EBS, Azure Blob, Managed Disks, GCP Cloud Storage, Persistent Disk.
- **DATABASE**: AWS RDS, DynamoDB, Azure SQL, CosmosDB, GCP Cloud SQL, Cloud Spanner.
- **NETWORKING**: NAT Gateways, Data Transfer Out (egress), Virtual Networks, Load Balancers.

For every service, CloudSage calculates:
1. **Total Spend ($)**: Sum of net cash expenditure within the filtered period.
2. **Percentage Share (%)**: Relative proportion of total organization cloud spend.
3. **Record Count**: Total billing line items processed.
4. **Associated Resources**: Number of discovered cloud assets in the inventory attributed to the service.

---

## 4. Multi-Dimensional Drilldown Capabilities

The analytics engine supports filtering across any combination of:
- **Provider**: AWS, AZURE, GCP, or ALL (unified multi-cloud).
- **Date Range**: Custom `start_date` and `end_date`.
- **Cloud Account / Subscription / Project**: e.g., AWS 12-digit Account ID, Azure Subscription GUID, GCP Project ID.
- **Service Name**: Exact or partial match (e.g., "Compute", "Storage").
- **Region**: Hyperscaler region (e.g., `us-east-1`, `westeurope`, `us-central1`).
- **Normalized Tags**: Environment (`production`, `staging`, `development`), Owner (`DevOps`, `Finance`), or Cost Center (`CC-101`).
