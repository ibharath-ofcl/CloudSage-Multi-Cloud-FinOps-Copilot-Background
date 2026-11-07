# CloudSage 20 Synthetic Recommendation Scenarios Catalog

## 1. Overview

The synthetic scenarios generator in `backend/app/recommendations/synthetic.py` provisions 20 realistic multi-cloud scenarios spanning Amazon Web Services (AWS), Microsoft Azure, and Google Cloud Platform (GCP).

These scenarios serve as automated benchmarks for integration testing, demonstration, and algorithm verification.

---

## 2. Scenarios Inventory

| ID | Provider | Resource Name / ID | Action | Baseline Cost | Monthly Savings | Priority | Strategy |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **01** | AWS | `dev-bastion-host-01` (`i-0a1b2c3d4e5f67890`) | `TERMINATE` | \$184.50 | \$184.50 | `P2` | `idle_compute_strategy` |
| **02** | Azure | `vm-worker-test` (`Standard_D8s_v5`) | `TERMINATE` | \$312.00 | \$312.00 | `P1` | `idle_compute_strategy` |
| **03** | GCP | `gce-jupyter-idle` (`e2-standard-8`) | `TERMINATE` | \$248.80 | \$248.80 | `P2` | `idle_compute_strategy` |
| **04** | AWS | `api-gateway-node-02` (`m5.2xlarge` $\to$ `m5.xlarge`) | `RIGHTSIZE` | \$292.00 | \$146.00 | `P2` | `compute_rightsizing_strategy` |
| **05** | Azure | `vm-payment-gw` (`Standard_D8s_v5` $\to$ `Standard_D4s_v5`) | `RIGHTSIZE` | \$480.00 | \$240.00 | `P1` | `compute_rightsizing_strategy` |
| **06** | GCP | `gce-cache-node-01` (`e2-standard-8` $\to$ `e2-standard-4`) | `RIGHTSIZE` | \$268.00 | \$134.00 | `P2` | `compute_rightsizing_strategy` |
| **07** | AWS | `unattached-db-data-vol` (`1TB gp3 volume`) | `CLEANUP_UNATTACHED` | \$125.00 | \$125.00 | `P3` | `storage_optimization_strategy` |
| **08** | Azure | `disk-scratch-500gb` (`500GB Premium SSD`) | `CLEANUP_UNATTACHED` | \$78.00 | \$78.00 | `P3` | `storage_optimization_strategy` |
| **09** | AWS | `temp-migration-snap-2025` (`EBS Snapshot`) | `DELETE_SNAPSHOT` | \$55.00 | \$55.00 | `P3` | `storage_optimization_strategy` |
| **10** | AWS | `corporate-compliance-raw-logs` (`60TB S3 Bucket`) | `CONVERT_STORAGE_TIER` | \$1,450.00 | \$1,160.00 | `P1` | `storage_optimization_strategy` |
| **11** | Azure | `stcoldbackup01` (`Azure Blob Container`) | `CONVERT_STORAGE_TIER` | \$860.00 | \$688.00 | `P1` | `storage_optimization_strategy` |
| **12** | AWS | `dev-postgres-cluster-01` (`db.m5.2xlarge` $\to$ `db.m5.xlarge`) | `RIGHTSIZE` | \$640.00 | \$320.00 | `P2` | `database_optimization_strategy` |
| **13** | Azure | `crm-stage` (`Azure SQL Database`) | `RIGHTSIZE` | \$520.00 | \$260.00 | `P2` | `database_optimization_strategy` |
| **14** | GCP | `sql-catalog-replica` (`Cloud SQL Read Replica`) | `RIGHTSIZE` | \$390.00 | \$195.00 | `P2` | `database_optimization_strategy` |
| **15** | AWS | `eip-legacy-gateway` (`2 Unallocated Elastic IPs`) | `RELEASE_IP` | \$7.20 | \$7.20 | `P4` | `network_optimization_strategy` |
| **16** | Azure | `pip-old-lb` (`Unassociated Public IP`) | `RELEASE_IP` | \$5.80 | \$5.80 | `P4` | `network_optimization_strategy` |
| **17** | AWS | `nat-main-outbound` (`NAT Gateway Egress Surge`) | `INVESTIGATE_ANOMALY` | \$2,400.00 | \$2,000.00 | `P1` | `anomaly_investigation_strategy` |
| **18** | AWS | `EC2-Compute-Savings-Plan` (`1-Year No Upfront`) | `PURCHASE_SAVINGS_PLAN` | \$8,500.00 | \$2,550.00 | `P1` | `pricing_usage_strategy` |
| **19** | Azure | `Azure-RI-D-Series` (`1-Year Reserved Instances`) | `RESERVE_CAPACITY` | \$4,200.00 | \$1,260.00 | `P1` | `pricing_usage_strategy` |
| **20** | AWS | `staging-qa-cluster-node` (`50 hrs/wk Schedule`) | `SCHEDULE_SHUTDOWN` | \$380.00 | \$267.00 | `P2` | `environment_scheduling_strategy` |

---

## 3. Financial Totals of Synthetic Scenarios

- **Total Baseline Monthly Spend**: \$21,570.30 / month
- **Total Estimated Monthly Savings**: \$10,037.80 / month
- **Total Estimated Annual Savings**: \$120,453.60 / year
- **Overall Potential Savings Reduction**: ~46.5%
