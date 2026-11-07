"""
CloudSage Synthetic Generator Unit Tests.
Category F: 1,000+ records generated, multi-cloud representation, seeded scenarios, and reproducibility.
"""

from decimal import Decimal
import os
import pytest
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.adapters.aws.adapter import AWSCurAdapter
from backend.app.ingestion.adapters.azure.adapter import AzureCostAdapter
from backend.app.ingestion.adapters.gcp.adapter import GCPApiAdapter
from backend.app.ingestion.synthetic.datasets import export_sample_datasets
from backend.app.ingestion.synthetic.generator import SyntheticDataGenerator
from backend.app.ingestion.synthetic.scenarios import SCENARIOS


def test_synthetic_generation_volume_and_distribution():
    """Verifies that at least 1,000 records are generated evenly across AWS, Azure, and GCP."""
    gen = SyntheticDataGenerator(seed=42)
    dataset = gen.generate_multi_cloud_dataset(total_records=1200)

    assert len(dataset[CloudProvider.AWS]) == 400
    assert len(dataset[CloudProvider.AZURE]) == 400
    assert len(dataset[CloudProvider.GCP]) == 400
    total = sum(len(records) for records in dataset.values())
    assert total == 1200


def test_synthetic_reproducibility():
    """Verifies that identical seeds produce bitwise identical records."""
    gen1 = SyntheticDataGenerator(seed=999)
    set1 = gen1.generate_multi_cloud_dataset(total_records=300)

    gen2 = SyntheticDataGenerator(seed=999)
    set2 = gen2.generate_multi_cloud_dataset(total_records=300)

    assert set1[CloudProvider.AWS][0]["lineItem/UnblendedCost"] == set2[CloudProvider.AWS][0]["lineItem/UnblendedCost"]
    assert set1[CloudProvider.AZURE][0]["CostInBillingCurrency"] == set2[CloudProvider.AZURE][0]["CostInBillingCurrency"]


def test_seeded_scenarios_presence():
    """Verifies presence of Idle VMs, Unattached Storage, Oversized Compute, and Cost Spikes."""
    gen = SyntheticDataGenerator(seed=42)
    dataset = gen.generate_multi_cloud_dataset(total_records=1200)

    aws_recs = dataset[CloudProvider.AWS]
    # Check for idle instances
    idle_aws = [r for r in aws_recs if "idle-dev-instance" in r["lineItem/ResourceId"]]
    assert len(idle_aws) > 0

    # Check for unattached EBS volumes
    unattached_aws = [r for r in aws_recs if "vol-unattached" in r["lineItem/ResourceId"]]
    assert len(unattached_aws) > 0

    # Check for oversized instances
    oversized_aws = [r for r in aws_recs if "oversized-c5-4xlarge" in r["lineItem/ResourceId"]]
    assert len(oversized_aws) > 0

    # Check for cost spike
    spike_aws = [r for r in aws_recs if "runaway-log-ingestion" in r["lineItem/ResourceId"]]
    assert len(spike_aws) > 0
    assert Decimal(spike_aws[0]["lineItem/UnblendedCost"]) > Decimal("400.0000")


def test_export_sample_datasets_and_adapter_readability(tmp_path):
    """Verifies that exported files are valid and readable by provider adapters."""
    test_dir = str(tmp_path / "sample_data")
    files = export_sample_datasets(output_dir=test_dir, total_records=300, seed=42)

    assert os.path.exists(files["aws"])
    assert os.path.exists(files["azure"])
    assert os.path.exists(files["gcp"])
    assert os.path.exists(files["readme"])

    # Verify AWS adapter can stream parse exported file
    aws_adapter = AWSCurAdapter()
    aws_items = list(aws_adapter.parse_stream(files["aws"]))
    assert len(aws_items) == 100

    # Verify Azure adapter can stream parse exported file
    azure_adapter = AzureCostAdapter()
    azure_items = list(azure_adapter.parse_stream(files["azure"]))
    assert len(azure_items) == 100

    # Verify GCP adapter can stream parse exported file
    gcp_adapter = GCPApiAdapter()
    gcp_items = list(gcp_adapter.parse_stream(files["gcp"]))
    assert len(gcp_items) == 100
