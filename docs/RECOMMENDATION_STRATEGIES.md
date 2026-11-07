# CloudSage Optimization Strategies Catalog

## 1. Strategy Overview

CloudSage implements eight pluggable, evidence-based optimization strategies registered in `RecommendationRegistry`. Each strategy targets specific hyperscaler cost inefficiencies across AWS, Azure, and GCP.

---

## 2. Strategy Specifications

### Strategy 1: Idle Compute Decommissioning (`idle_compute_strategy`)
- **Target Inefficiency**: Virtual machines running 24x7 with sub-5% average CPU utilization and near-zero network I/O over 14+ observation days.
- **Data Sources**: Stage 6 `IDLE_VM` findings, CloudWatch / Azure Monitor / Cloud Monitoring telemetry.
- **Recommended Action**: `TERMINATE`
- **Savings Formula**: 100% of current monthly expenditure:
  $$\text{Monthly Savings} = \text{Current Monthly Cost}$$
- **Hyperscaler Implementations**:
  - AWS: `aws ec2 terminate-instances --instance-ids <id>`
  - Azure: `az vm delete --resource-group <rg> --name <name> --yes`
  - GCP: `gcloud compute instances delete <name> --zone <zone> --quiet`
- **Risk Level**: `LOW` (Dev/Test) / `MEDIUM` (Production)
- **Effort**: `LOW`

---

### Strategy 2: Compute Instance Rightsizing (`compute_rightsizing_strategy`)
- **Target Inefficiency**: Compute instances provisioned with excessive vCPUs or RAM where peak utilization never exceeds 20% CPU / 30% RAM.
- **Data Sources**: Stage 6 `OVERSIZED_COMPUTE` findings, historical metric percentiles.
- **Recommended Action**: `RIGHTSIZE`
- **Savings Formula**: Difference between current instance type hourly rate and target downsized tier rate:
  $$\text{Monthly Savings} = \text{Current Monthly Cost} - \text{Projected Monthly Cost}$$
- **Canonical Downsizing Paths**:
  - AWS: `m5.2xlarge` (8 vCPU / 32GB) $\to$ `m5.xlarge` (4 vCPU / 16GB) [50% reduction]
  - Azure: `Standard_D8s_v5` (8 vCPU / 32GB) $\to$ `Standard_D4s_v5` (4 vCPU / 16GB) [50% reduction]
  - GCP: `e2-standard-8` (8 vCPU / 32GB) $\to$ `e2-standard-4` (4 vCPU / 16GB) [50% reduction]
- **Risk Level**: `MEDIUM`
- **Effort**: `MEDIUM`

---

### Strategy 3: Storage & Snapshot Optimization (`storage_optimization_strategy`)
- **Target Inefficiency**:
  1. Block storage volumes detached from any running instance for > 14 days.
  2. Orphaned volume snapshots created > 90 days ago whose parent volume was deleted.
  3. Uncompressed archival log buckets stored in standard tier.
- **Data Sources**: Stage 6 `UNATTACHED_DISK`, `ORPHANED_SNAPSHOT`, Stage 5 inventory relationships.
- **Recommended Actions**: `CLEANUP_UNATTACHED`, `DELETE_SNAPSHOT`, `CONVERT_STORAGE_TIER`
- **Savings Formulas**:
  - Unattached Volume / Snapshot: 100% elimination of provisioned GB-month charges.
  - S3 / Blob Lifecycle Tiering: 80% discount moving Standard $\to$ Glacier / Cool / Nearline.
- **Risk Level**: `NONE` (Orphaned Snapshot) / `LOW` (Unattached Disk)
- **Effort**: `QUICK_WIN`

---

### Strategy 4: Database Rightsizing & Tier Optimization (`database_optimization_strategy`)
- **Target Inefficiency**: Provisioned managed databases (AWS RDS, Azure SQL / Cosmos, GCP Cloud SQL) maintaining sub-5 active connections and < 10% CPU.
- **Data Sources**: Stage 6 `UNDERUTILIZED_DATABASE` findings, database connection telemetry.
- **Recommended Action**: `RIGHTSIZE` or `PAUSE`
- **Savings Formula**: 50% reduction on instance tier; 70% reduction if nightly paused for non-prod clusters.
- **Risk Level**: `MEDIUM`
- **Effort**: `MEDIUM`

---

### Strategy 5: Network & Elastic IP Optimization (`network_optimization_strategy`)
- **Target Inefficiency**:
  1. Static Public IPs allocated but unassociated with any network interface.
  2. Application Load Balancers with zero registered healthy backend targets.
- **Data Sources**: Stage 6 `IDLE_IP`, `ZERO_TARGET_LB` findings.
- **Recommended Actions**: `RELEASE_IP`, `TERMINATE`
- **Savings Formula**:
  - AWS Elastic IP: \$0.005/hour (\$3.60/month per unallocated IP).
  - Idle ALB / Gateway: \$18.00 - \$25.00/month per load balancer.
- **Risk Level**: `NONE`
- **Effort**: `QUICK_WIN`

---

### Strategy 6: Cost Anomaly & Spike Investigation (`anomaly_investigation_strategy`)
- **Target Inefficiency**: Unacknowledged `HIGH` or `CRITICAL` statistical cost surges identified by Stage 7 Anomaly Detection Engine (e.g. data transfer egress spikes, runaway lambda invocations, SKU pricing shifts).
- **Data Sources**: Stage 7 `cost_anomalies` records (Z-Score $\ge 3.0$ or $>100\%$ spike).
- **Recommended Action**: `INVESTIGATE_ANOMALY`
- **Savings Formula**: Avoided 30-day unbudgeted overrun:
  $$\text{Projected Monthly Savings} = \text{Observed Daily Excess Cost} \times 30$$
- **Risk Level**: `MEDIUM`
- **Effort**: `LOW`

---

### Strategy 7: Commitment Discounts & Savings Plans (`pricing_usage_strategy`)
- **Target Inefficiency**: High-volume, steady-state compute and database fleets running continuously on on-demand pricing models.
- **Data Sources**: Stage 4 FOCUS billing records aggregating on-demand spend $> \$500$/month.
- **Recommended Actions**: `PURCHASE_SAVINGS_PLAN`, `RESERVE_CAPACITY`
- **Savings Formula**: Simulates 1-year or 3-year term commitments with 30% average net discount:
  $$\text{Monthly Savings} = \text{Monthly On-Demand Spend} \times 0.3000$$
- **Risk Level**: `LOW`
- **Effort**: `LOW`

---

### Strategy 8: Non-Production Environment Scheduling (`environment_scheduling_strategy`)
- **Target Inefficiency**: Development, staging, and QA environments running 168 hours/week (24x7) when engineering teams operate only during business hours (50 hours/week).
- **Data Sources**: Stage 6 `CONTINUOUS_NON_PROD` findings, resource environment tags (`env=dev`, `env=test`, `env=stage`).
- **Recommended Action**: `SCHEDULE_SHUTDOWN`
- **Savings Formula**:
  $$\text{Monthly Savings} = \text{Current Monthly Cost} \times \frac{168 - 50}{168} = \text{Current Cost} \times 0.7024$$
- **Risk Level**: `LOW`
- **Effort**: `QUICK_WIN`
