"""
CloudSage Sample Dataset Exporter.
Serializes synthetic multi-cloud datasets into physical sample files under backend/sample_data/.
"""

import csv
import json
import os
from typing import Dict, List
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.synthetic.generator import SyntheticDataGenerator


def get_all_fieldnames(records: List[Dict[str, any]]) -> List[str]:
    """Collects all unique field names across all records preserving order."""
    fields: List[str] = []
    for r in records:
        for k in r.keys():
            if k not in fields:
                fields.append(k)
    return fields


def export_sample_datasets(
    output_dir: str = "backend/sample_data",
    total_records: int = 1200,
    seed: int = 42
) -> Dict[str, str]:
    """Generates and writes sample files for AWS, Azure, and GCP."""
    generator = SyntheticDataGenerator(seed=seed)
    datasets = generator.generate_multi_cloud_dataset(total_records=total_records)

    aws_dir = os.path.join(output_dir, "aws")
    azure_dir = os.path.join(output_dir, "azure")
    gcp_dir = os.path.join(output_dir, "gcp")

    os.makedirs(aws_dir, exist_ok=True)
    os.makedirs(azure_dir, exist_ok=True)
    os.makedirs(gcp_dir, exist_ok=True)

    created_files = {}

    # 1. AWS CUR CSV
    aws_path = os.path.join(aws_dir, "aws_cur_sample.csv")
    aws_records = datasets[CloudProvider.AWS]
    if aws_records:
        fieldnames = get_all_fieldnames(aws_records)
        with open(aws_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(aws_records)
        created_files["aws"] = aws_path

    # 2. Azure Cost Export CSV
    azure_path = os.path.join(azure_dir, "azure_cost_sample.csv")
    azure_records = datasets[CloudProvider.AZURE]
    if azure_records:
        # Convert tags dict to string for CSV
        clean_azure = []
        for r in azure_records:
            item = dict(r)
            if isinstance(item.get("Tags"), dict):
                item["Tags"] = json.dumps(item["Tags"])
            clean_azure.append(item)
        fieldnames = get_all_fieldnames(clean_azure)
        with open(azure_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(clean_azure)
        created_files["azure"] = azure_path

    # 3. GCP Billing JSON
    gcp_path = os.path.join(gcp_dir, "gcp_billing_sample.json")
    gcp_records = datasets[CloudProvider.GCP]
    with open(gcp_path, mode="w", encoding="utf-8") as f:
        json.dump(gcp_records, f, indent=2)
    created_files["gcp"] = gcp_path

    # 4. Dataset Documentation
    readme_path = os.path.join(output_dir, "README.md")
    readme_content = f"""# CloudSage Multi-Cloud Synthetic Benchmark Datasets

This directory contains pre-generated, reproducible multi-cloud billing datasets representing realistic enterprise cloud infrastructure expenditures across AWS, Azure, and GCP.

## Dataset Summary
- **Total Records**: {total_records} line items ({total_records // 3} records per provider).
- **Time Range**: 2026-11-01 to 2026-11-07 (7 calendar days).
- **Random Seed**: {seed} (fully deterministic).

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
"""
    with open(readme_path, mode="w", encoding="utf-8") as f:
        f.write(readme_content)
    created_files["readme"] = readme_path

    return created_files
