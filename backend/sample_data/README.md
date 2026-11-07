# CloudSage Multi-Cloud Synthetic Benchmark Datasets

This directory contains pre-generated, reproducible multi-cloud billing datasets representing realistic enterprise cloud infrastructure expenditures across AWS, Azure, and GCP.

## Dataset Summary
- **Total Records**: 30 line items (10 records per provider).
- **Time Range**: 2026-11-01 to 2026-11-07 (7 calendar days).
- **Random Seed**: 42 (fully deterministic).

## Directory Structure
- `aws/aws_cur_sample.csv`: AWS Cost and Usage Report (CUR) format containing EC2, S3, RDS, Lambda, EBS, and CloudWatch line items with resource IDs and tags.
- `azure/azure_cost_sample.csv`: Microsoft Azure Cost Management export format containing Virtual Machines, Managed Disks, Azure SQL, and Functions.
- `gcp/gcp_billing_sample.json`: Google Cloud Platform BigQuery export format containing Compute Engine, Persistent Disks, BigQuery queries, Cloud SQL, and credits.

## Seeded Optimization Scenarios
These datasets contain seeded test cases designed to benchmark future analytical detection engines:
1. **Scenario A (Normal Spend)**: Baseline compute and storage utilization.
2. **Scenario B (Idle VMs)**: Instances with average CPU < 5% (`idle-dev-instance-*`, `idle-azure-b2s-*`, `idle-n1-standard-1-*`).
3. **Scenario C (Unattached Storage)**: Standalone block storage disks (`vol-unattached-*`, `disk-unattached-*`, `orphaned-pd-ssd-*`).
4. **Scenario D (Oversized Compute)**: Over-provisioned `c5.4xlarge` compute instances.
5. **Scenario E (Cost Spikes)**: Unexpected expenditure surges (`runaway-log-ingestion-*`, `unpartitioned-query-scan-*`).
6. **Scenario F (Missing Tags)**: Resources missing mandatory `owner` and `environment` metadata tags.
