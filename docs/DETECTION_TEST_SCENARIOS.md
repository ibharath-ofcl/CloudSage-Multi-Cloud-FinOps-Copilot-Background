# CloudSage Synthetic Waste Test Scenarios Matrix

To guarantee rigorous test coverage across subtle FinOps operational conditions, CloudSage implements 14 deterministic synthetic test scenarios via `SyntheticWasteScenarioGenerator`.

---

## 1. Scenario Catalog & Validation Results

| # | Scenario Identifier | Target Cloud Resource | Injected Telemetry & Topological State | Expected Engine Behavior | Test Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **01** | `scen_01_idle_aws_ec2` | AWS EC2 `m5.large` | 7 days avg CPU 2.1%, peak 4.5%, network 0.1 MB/day; \$180/mo spend | `DETECTED`: `IDLE_COMPUTE`, \$180/mo savings | Verified |
| **02** | `scen_02_underutilized_azure_vm` | Azure VM `Standard_D4s_v5` | 14 days avg CPU 3.5%, peak 8.0%, network 0.2 MB/day; \$192/mo spend | `DETECTED`: `IDLE_COMPUTE`, \$192/mo savings | Verified |
| **03** | `scen_03_oversized_gcp_instance` | GCP VM `n2-standard-8` | 14 days avg CPU 12.0%, peak 35.0%; \$240/mo spend | `DETECTED`: `OVERSIZED_COMPUTE`, \$120/mo savings (50% downsize) | Verified |
| **04** | `scen_04_unattached_aws_ebs` | AWS EBS `gp3` (500 GB) | Status `available`, age 14 days, 0 incoming attachments | `DETECTED`: `UNATTACHED_STORAGE`, \$40/mo savings | Verified |
| **05** | `scen_05_unattached_azure_disk` | Azure Managed Disk `Premium_LRS` | Status `unattached`, age 21 days, 0 incoming attachments | `DETECTED`: `UNATTACHED_STORAGE`, \$65/mo savings | Verified |
| **06** | `scen_06_detached_gcp_disk` | GCP Persistent Disk (1 TB) | Status `ready`, age 10 days, 0 incoming attachments | `DETECTED`: `UNATTACHED_STORAGE`, \$80/mo savings | Verified |
| **07** | `scen_07_orphaned_aws_snapshot` | AWS EBS Snapshot (800 GB) | Age 60 days; parent volume missing/deleted; no retention tags | `DETECTED`: `ORPHANED_SNAPSHOT`, \$40/mo savings | Verified |
| **08** | `scen_08_compliance_azure_snapshot` | Azure Snapshot (1.2 TB) | Age 90 days; parent deleted; tagged with `retention: 7-years` | `CLEAN`: Retained under compliance governance | Verified |
| **09** | `scen_09_underutilized_database` | AWS RDS PostgreSQL `db.m5.xlarge` | 7 days avg connections 0.3, avg CPU 3.2%; \$260/mo spend | `DETECTED`: `UNDERUTILIZED_DATABASE`, \$260/mo savings | Verified |
| **10** | `scen_10_stale_resource_billing` | AWS S3 Bucket / DynamoDB table | Incurring recurring billing, but unobserved in inventory for 25 days | `DETECTED`: `BILLING_BASED_WASTE`, \$85/mo savings | Verified |
| **11** | `scen_11_missing_metrics` | GCP Cloud SQL Database | Active database, zero connection telemetry present | `INSUFFICIENT_DATA`: Mandatory telemetry check passed | Verified |
| **12** | `scen_12_insufficient_history` | AWS EC2 Instance | Launched 12 hours ago (span < 2.5 days); avg CPU 1.0% | `INSUFFICIENT_DATA`: Awaits observation window maturation | Verified |
| **13** | `scen_13_conflicting_signals` | AWS EC2 NAT Proxy Instance | Avg CPU 2.5% (<5%), but network throughput 500 MB/day | `CLEAN`: Recognized as active networking proxy node | Verified |
| **14** | `scen_14_zero_cost` | AWS Free-Tier Volume | Status `available`, age 5 days, but monthly spend is \$0.0000 | `CLEAN` / Zero savings: Non-speculative financial rule | Verified |
