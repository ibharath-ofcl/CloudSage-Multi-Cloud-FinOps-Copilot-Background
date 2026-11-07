"""
CloudSage Inventory Adapters Unit Tests.
Verifies AWS, Azure, and GCP inventory parsing, state normalization,
name extraction, relationship derivation, and credential handling.
"""

from decimal import Decimal
import json
import pytest
from backend.app.inventory.adapters.aws import AWSInventoryAdapter
from backend.app.inventory.adapters.azure import AzureInventoryAdapter
from backend.app.inventory.adapters.gcp import GCPInventoryAdapter
from backend.app.inventory.mappers.resource_mapper import ResourceMapper
from backend.app.inventory.mappers.state_mapper import StateMapper
from backend.app.inventory.registry import InventoryRegistry


def test_aws_inventory_adapter_parsing():
    adapter = AWSInventoryAdapter()
    sample_payload = {
        "resources": [
            {
                "resource_id": "arn:aws:ec2:us-east-1:123456789012:instance/i-0a1b2c3d4e5f6g7h8",
                "account_id": "123456789012",
                "resource_name": "api-gateway-prod",
                "service_name": "AmazonEC2",
                "resource_type": "ec2:instance",
                "region": "us-east-1",
                "zone": "us-east-1a",
                "status": "running",
                "instance_type": "c5.xlarge",
                "tags": {
                    "Owner": "finops@enterprise.com",
                    "Environment": "production",
                    "CostCenter": "CC-1001",
                    "Department": "Platform",
                    "Project": "FinOps",
                },
                "attached_volume_ids": ["vol-0123456789abcdef0"],
            },
            {
                "resource_id": "arn:aws:ec2:us-east-1:123456789012:snapshot/snap-0987654321fedcba0",
                "account_id": "123456789012",
                "resource_name": "backup-snap",
                "service_name": "AmazonEC2",
                "resource_type": "ec2:snapshot",
                "region": "us-east-1",
                "status": "completed",
                "source_volume_id": "vol-0123456789abcdef0",
            },
        ]
    }

    result = adapter.parse_export(sample_payload)
    assert len(result.errors) == 0
    assert len(result.resources) == 2
    assert len(result.relationships) == 2

    # Verify EC2 instance
    ec2_res = result.resources[0]
    assert ec2_res.resource_id == "arn:aws:ec2:us-east-1:123456789012:instance/i-0a1b2c3d4e5f6g7h8"
    assert ec2_res.status == "active"
    assert ec2_res.environment == "production"
    assert ec2_res.owner == "finops@enterprise.com"
    assert ec2_res.tag_quality_score == Decimal("100.00")

    # Verify relationships
    attached_rel = [r for r in result.relationships if r.relationship_type == "ATTACHED_TO"][0]
    assert attached_rel.source_resource_id == "arn:aws:ec2:us-east-1:123456789012:instance/i-0a1b2c3d4e5f6g7h8"
    assert attached_rel.target_resource_id == "vol-0123456789abcdef0"

    snap_rel = [r for r in result.relationships if r.relationship_type == "SNAPSHOT_OF"][0]
    assert snap_rel.source_resource_id == "arn:aws:ec2:us-east-1:123456789012:snapshot/snap-0987654321fedcba0"
    assert snap_rel.target_resource_id == "vol-0123456789abcdef0"


def test_azure_inventory_adapter_parsing():
    adapter = AzureInventoryAdapter()
    sample_payload = [
        {
            "id": "/subscriptions/sub-123/resourceGroups/rg-core/providers/Microsoft.Compute/virtualMachines/vm-prod-01",
            "name": "vm-prod-01",
            "type": "Microsoft.Compute/virtualMachines",
            "location": "eastus",
            "power_state": "VM deallocated",
            "vm_size": "Standard_E8s_v3",
            "tags": {
                "owner": "sysadmin@enterprise.com",
                "environment": "staging",
                "cost-center": "CC-2002",
            },
            "attached_disk_ids": [
                "/subscriptions/sub-123/resourceGroups/rg-core/providers/Microsoft.Compute/disks/disk-os-01"
            ],
            "vnet_id": "/subscriptions/sub-123/resourceGroups/rg-core/providers/Microsoft.Network/virtualNetworks/vnet-01",
        }
    ]

    result = adapter.parse_export(sample_payload)
    assert len(result.errors) == 0
    assert len(result.resources) == 1
    assert len(result.relationships) == 2  # 1 disk attached, 1 vnet attached

    vm = result.resources[0]
    assert vm.provider == "AZURE"
    assert vm.account_id == "sub-123"
    assert vm.status == "stopped"  # deallocated maps to stopped
    assert vm.environment == "staging"
    assert vm.service_category == "COMPUTE"


def test_gcp_inventory_adapter_parsing():
    adapter = GCPInventoryAdapter()
    sample_payload = {
        "assets": [
            {
                "name": "//compute.googleapis.com/projects/my-gcp-proj/zones/us-central1-b/instances/gce-worker-01",
                "assetType": "compute.googleapis.com/Instance",
                "location": "us-central1",
                "status": "RUNNING",
                "machine_type": "n2-standard-4",
                "labels": {
                    "owner": "data@enterprise.com",
                    "env": "production",
                    "project_id": "DataPlatform",
                },
                "disks": [
                    {"source": "//compute.googleapis.com/projects/my-gcp-proj/zones/us-central1-b/disks/boot-disk-01", "boot": True}
                ],
            }
        ]
    }

    result = adapter.parse_export(sample_payload)
    assert len(result.errors) == 0
    assert len(result.resources) == 1
    assert len(result.relationships) == 1

    gce = result.resources[0]
    assert gce.provider == "GCP"
    assert gce.account_id == "my-gcp-proj"
    assert gce.resource_name == "gce-worker-01"
    assert gce.status == "active"
    assert gce.environment == "production"


def test_resource_mapper_name_and_type_extraction():
    # AWS ARN
    name_aws = ResourceMapper.extract_name_from_id("AWS", "arn:aws:s3:::my-test-bucket-01")
    assert name_aws == "my-test-bucket-01"

    # Azure ARM
    name_az = ResourceMapper.extract_name_from_id(
        "AZURE",
        "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/my-vm-web"
    )
    assert name_az == "my-vm-web"

    # GCP URI
    name_gcp = ResourceMapper.extract_name_from_id(
        "GCP",
        "//compute.googleapis.com/projects/p/zones/z/instances/my-gcp-node"
    )
    assert name_gcp == "my-gcp-node"


def test_state_mapper_normalization():
    # AWS
    assert StateMapper.normalize_state("AWS", "running") == "active"
    assert StateMapper.normalize_state("AWS", "stopped") == "stopped"
    assert StateMapper.normalize_state("AWS", "available") == "active"
    assert StateMapper.normalize_state("AWS", "terminated") == "terminated"

    # Azure
    assert StateMapper.normalize_state("AZURE", "VM running") == "active"
    assert StateMapper.normalize_state("AZURE", "VM deallocated") == "stopped"
    assert StateMapper.normalize_state("AZURE", "Unattached") == "available"

    # GCP
    assert StateMapper.normalize_state("GCP", "RUNNING") == "active"
    assert StateMapper.normalize_state("GCP", "TERMINATED") == "stopped"
    assert StateMapper.normalize_state("GCP", "READY") == "available"


def test_inventory_registry_provider_auto_detection():
    aws_sample = {"resources": [{"resource_id": "arn:aws:ec2:us-east-1:123:instance/i-1", "service_name": "AmazonEC2"}]}
    azure_sample = [{"id": "/subscriptions/sub-1/resourceGroups/rg/providers/Microsoft.Compute/virtualMachines/vm"}]
    gcp_sample = {"assets": [{"name": "//compute.googleapis.com/projects/p/zones/z/instances/inst"}]}

    assert InventoryRegistry.detect_provider(aws_sample) == "AWS"
    assert InventoryRegistry.detect_provider(azure_sample) == "AZURE"
    assert InventoryRegistry.detect_provider(gcp_sample) == "GCP"


def test_live_discovery_safe_unconfigured():
    aws_adapter = AWSInventoryAdapter()
    result = aws_adapter.discover_live()
    # In test environment without AWS keys, safely reports UNCONFIGURED
    assert len(result.errors) > 0
    assert result.errors[0]["status"] in ("UNCONFIGURED", "READ_ONLY_CONFIRMED")
