"""
CloudSage Synthetic Inventory Generator.
Produces realistic multi-cloud inventory datasets for AWS, Azure, and GCP
with rich metadata, lifecycle states, tags, and directional topology relationships.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import os
from typing import Any, Dict, List, Optional


class SyntheticInventoryGenerator:
    """Generates synthetic hyperscaler inventory datasets for testing and demonstrations."""

    @classmethod
    def generate_aws_inventory(cls, count: int = 20) -> List[Dict[str, Any]]:
        """Generates realistic AWS inventory export payload."""
        resources = []
        now = datetime.now(timezone.utc)

        # 1. EC2 Instances & Attached EBS Volumes
        for i in range(1, 6):
            inst_id = f"i-0{i}a1b2c3d4e5f{i:02d}"
            vol1_id = f"vol-0{i}1122334455a{i:02d}"
            vol2_id = f"vol-0{i}9988776655b{i:02d}"
            snap_id = f"snap-0{i}aabbccddeeff{i:02d}"

            inst_status = "running" if i != 4 else "stopped"
            env = "production" if i in (1, 2) else ("staging" if i == 3 else "development")

            # EC2 instance
            resources.append({
                "resource_id": f"arn:aws:ec2:us-east-1:123456789012:instance/{inst_id}",
                "account_id": "123456789012",
                "resource_name": f"web-server-prod-0{i}" if i <= 2 else f"app-server-dev-0{i}",
                "service_name": "AmazonEC2",
                "resource_type": "ec2:instance",
                "region": "us-east-1",
                "availability_zone": "us-east-1a",
                "status": inst_status,
                "instance_type": "m5.large" if i <= 2 else "t3.medium",
                "created_at": (now - timedelta(days=60 + i * 5)).isoformat(),
                "tags": {
                    "Name": f"web-server-prod-0{i}",
                    "Owner": f"devops{i}@enterprise.com",
                    "Department": "Platform Engineering",
                    "Environment": env,
                    "CostCenter": f"CC-{1000 + i * 10}",
                    "Project": "CloudMigration",
                },
                "attached_volume_ids": [
                    f"arn:aws:ec2:us-east-1:123456789012:volume/{vol1_id}",
                    f"arn:aws:ec2:us-east-1:123456789012:volume/{vol2_id}",
                ],
            })

            # Attached OS Volume
            resources.append({
                "resource_id": f"arn:aws:ec2:us-east-1:123456789012:volume/{vol1_id}",
                "account_id": "123456789012",
                "resource_name": f"root-vol-0{i}",
                "service_name": "AmazonEC2",
                "resource_type": "ec2:volume",
                "region": "us-east-1",
                "status": "in-use",
                "size_gb": 100,
                "volume_type": "gp3",
                "created_at": (now - timedelta(days=60 + i * 5)).isoformat(),
                "tags": {
                    "Owner": f"devops{i}@enterprise.com",
                    "Environment": env,
                    "AttachedInstance": inst_id,
                },
            })

            # Data Volume
            resources.append({
                "resource_id": f"arn:aws:ec2:us-east-1:123456789012:volume/{vol2_id}",
                "account_id": "123456789012",
                "resource_name": f"data-vol-0{i}",
                "service_name": "AmazonEC2",
                "resource_type": "ec2:volume",
                "region": "us-east-1",
                "status": "in-use",
                "size_gb": 500,
                "volume_type": "gp3",
                "created_at": (now - timedelta(days=60 + i * 5)).isoformat(),
                "tags": {
                    "Owner": f"devops{i}@enterprise.com",
                    "Environment": env,
                },
            })

            # Snapshot of OS Volume
            resources.append({
                "resource_id": f"arn:aws:ec2:us-east-1:123456789012:snapshot/{snap_id}",
                "account_id": "123456789012",
                "resource_name": f"backup-snap-0{i}",
                "service_name": "AmazonEC2",
                "resource_type": "ec2:snapshot",
                "region": "us-east-1",
                "status": "completed",
                "created_at": (now - timedelta(days=30 + i)).isoformat(),
                "source_volume_id": f"arn:aws:ec2:us-east-1:123456789012:volume/{vol1_id}",
                "tags": {
                    "Environment": env,
                    "AutomatedBackup": "true",
                },
            })

        # Unattached orphan volume
        resources.append({
            "resource_id": "arn:aws:ec2:us-east-1:123456789012:volume/vol-09999999orphan",
            "account_id": "123456789012",
            "resource_name": "abandoned-temp-disk",
            "service_name": "AmazonEC2",
            "resource_type": "ec2:volume",
            "region": "us-east-1",
            "status": "available",  # unattached!
            "size_gb": 250,
            "volume_type": "gp2",
            "created_at": (now - timedelta(days=45)).isoformat(),
            "tags": {},  # untagged
        })

        # S3 Buckets
        for b in range(1, 4):
            resources.append({
                "resource_id": f"arn:aws:s3:::enterprise-data-archive-{b}",
                "account_id": "123456789012",
                "resource_name": f"enterprise-data-archive-{b}",
                "service_name": "AmazonS3",
                "resource_type": "s3:bucket",
                "region": "us-east-1",
                "status": "active",
                "created_at": (now - timedelta(days=120)).isoformat(),
                "tags": {
                    "Owner": "storage-team@enterprise.com",
                    "Environment": "production",
                    "CostCenter": "CC-2000",
                },
            })

        # RDS Databases
        for d in range(1, 3):
            resources.append({
                "resource_id": f"arn:aws:rds:us-east-1:123456789012:db:aurora-prod-cluster-{d}",
                "account_id": "123456789012",
                "resource_name": f"aurora-prod-cluster-{d}",
                "service_name": "AmazonRDS",
                "resource_type": "rds:db",
                "region": "us-east-1",
                "status": "available",
                "created_at": (now - timedelta(days=90)).isoformat(),
                "tags": {
                    "Owner": "dba@enterprise.com",
                    "Department": "Database Operations",
                    "Environment": "production",
                    "CostCenter": "CC-3000",
                },
            })

        return resources

    @classmethod
    def generate_azure_inventory(cls, count: int = 20) -> List[Dict[str, Any]]:
        """Generates realistic Azure inventory export payload."""
        resources = []
        now = datetime.now(timezone.utc)
        sub = "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"
        rg = "rg-enterprise-core"

        for i in range(1, 6):
            vm_name = f"az-prod-vm-{i:02d}"
            disk_name = f"az-os-disk-{i:02d}"
            snap_name = f"az-disk-snap-{i:02d}"
            vnet_name = "vnet-enterprise-eastus"

            vm_arm = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{vm_name}"
            disk_arm = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/disks/{disk_name}"
            snap_arm = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/snapshots/{snap_name}"
            vnet_arm = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet_name}"

            env = "production" if i <= 3 else "development"
            vm_state = "VM running" if i != 5 else "VM deallocated"

            # Virtual Machine
            resources.append({
                "resource_id": vm_arm,
                "subscription_id": sub,
                "resource_name": vm_name,
                "resource_type": "Microsoft.Compute/virtualMachines",
                "service_name": "VirtualMachines",
                "region": "eastus",
                "status": vm_state,
                "vm_size": "Standard_D4s_v3",
                "created_at": (now - timedelta(days=50 + i * 4)).isoformat(),
                "tags": {
                    "owner": f"azureadmin{i}@enterprise.com",
                    "environment": env,
                    "department": "Infrastructure",
                    "cost-center": f"CC-{4000 + i * 10}",
                    "project": "CloudCore",
                },
                "attached_disk_ids": [disk_arm],
                "vnet_id": vnet_arm,
            })

            # Managed Disk
            resources.append({
                "resource_id": disk_arm,
                "subscription_id": sub,
                "resource_name": disk_name,
                "resource_type": "Microsoft.Compute/disks",
                "service_name": "ManagedDisks",
                "region": "eastus",
                "status": "Attached",
                "disk_size_gb": 128,
                "sku": "Premium_LRS",
                "created_at": (now - timedelta(days=50 + i * 4)).isoformat(),
                "tags": {
                    "owner": f"azureadmin{i}@enterprise.com",
                    "environment": env,
                },
            })

            # Snapshot
            resources.append({
                "resource_id": snap_arm,
                "subscription_id": sub,
                "resource_name": snap_name,
                "resource_type": "Microsoft.Compute/snapshots",
                "service_name": "ManagedDisks",
                "region": "eastus",
                "status": "Succeeded",
                "created_at": (now - timedelta(days=20 + i)).isoformat(),
                "source_resource_id": disk_arm,
                "tags": {
                    "environment": env,
                },
            })

        # Unattached Azure Disk
        unattached_arm = f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/disks/disk-unattached-spare"
        resources.append({
            "resource_id": unattached_arm,
            "subscription_id": sub,
            "resource_name": "disk-unattached-spare",
            "resource_type": "Microsoft.Compute/disks",
            "service_name": "ManagedDisks",
            "region": "eastus",
            "status": "Unattached",
            "disk_size_gb": 512,
            "sku": "StandardSSD_LRS",
            "created_at": (now - timedelta(days=35)).isoformat(),
            "tags": {},
        })

        # Storage Account
        resources.append({
            "resource_id": f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/stenterpriseblob01",
            "subscription_id": sub,
            "resource_name": "stenterpriseblob01",
            "resource_type": "Microsoft.Storage/storageAccounts",
            "service_name": "StorageAccounts",
            "region": "eastus",
            "status": "Succeeded",
            "created_at": (now - timedelta(days=100)).isoformat(),
            "tags": {
                "owner": "storage@enterprise.com",
                "environment": "production",
                "cost-center": "CC-5000",
            },
        })

        # Azure SQL
        resources.append({
            "resource_id": f"/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Sql/servers/sql-srv-prod/databases/crm-db",
            "subscription_id": sub,
            "resource_name": "crm-db",
            "resource_type": "Microsoft.Sql/servers/databases",
            "service_name": "AzureSQL",
            "region": "eastus",
            "status": "Online",
            "created_at": (now - timedelta(days=80)).isoformat(),
            "tags": {
                "owner": "crmteam@enterprise.com",
                "environment": "production",
                "cost-center": "CC-6000",
            },
        })

        return resources

    @classmethod
    def generate_gcp_inventory(cls, count: int = 20) -> List[Dict[str, Any]]:
        """Generates realistic GCP Cloud Asset Inventory payload."""
        resources = []
        now = datetime.now(timezone.utc)
        project = "enterprise-finops-prod-01"

        for i in range(1, 6):
            inst_name = f"gce-app-node-{i:02d}"
            disk_name = f"gce-boot-disk-{i:02d}"
            snap_name = f"gce-snap-backup-{i:02d}"
            zone = "us-central1-a"

            inst_uri = f"//compute.googleapis.com/projects/{project}/zones/{zone}/instances/{inst_name}"
            disk_uri = f"//compute.googleapis.com/projects/{project}/zones/{zone}/disks/{disk_name}"
            snap_uri = f"//compute.googleapis.com/projects/{project}/global/snapshots/{snap_name}"
            vpc_uri = f"//compute.googleapis.com/projects/{project}/global/networks/enterprise-vpc-default"

            inst_status = "RUNNING" if i != 5 else "TERMINATED"
            env = "production" if i <= 3 else "test"

            # GCE Instance
            resources.append({
                "resource_id": inst_uri,
                "project_id": project,
                "resource_name": inst_name,
                "resource_type": "compute.googleapis.com/Instance",
                "service_name": "ComputeEngine",
                "region": "us-central1",
                "zone": zone,
                "status": inst_status,
                "machine_type": "e2-standard-4",
                "created_at": (now - timedelta(days=40 + i * 3)).isoformat(),
                "labels": {
                    "owner": f"gcpengineer{i}@enterprise.com",
                    "env": env,
                    "dept": "Analytics",
                    "cost_center": f"cc-{7000 + i * 10}",
                    "project_id": "FinOpsGCP",
                },
                "attached_disks": [disk_uri],
                "network_interfaces": [{"network": vpc_uri}],
            })

            # Persistent Disk
            resources.append({
                "resource_id": disk_uri,
                "project_id": project,
                "resource_name": disk_name,
                "resource_type": "compute.googleapis.com/Disk",
                "service_name": "ComputeEngine",
                "region": "us-central1",
                "zone": zone,
                "status": "ATTACHED",
                "size_gb": 100,
                "created_at": (now - timedelta(days=40 + i * 3)).isoformat(),
                "labels": {
                    "owner": f"gcpengineer{i}@enterprise.com",
                    "env": env,
                },
            })

            # Snapshot
            resources.append({
                "resource_id": snap_uri,
                "project_id": project,
                "resource_name": snap_name,
                "resource_type": "compute.googleapis.com/Snapshot",
                "service_name": "ComputeEngine",
                "region": "us-central1",
                "status": "READY",
                "created_at": (now - timedelta(days=15 + i)).isoformat(),
                "source_disk": disk_uri,
                "labels": {
                    "env": env,
                },
            })

        # Detached GCP disk
        detached_uri = f"//compute.googleapis.com/projects/{project}/zones/us-central1-a/disks/gce-disk-detached-old"
        resources.append({
            "resource_id": detached_uri,
            "project_id": project,
            "resource_name": "gce-disk-detached-old",
            "resource_type": "compute.googleapis.com/Disk",
            "service_name": "ComputeEngine",
            "region": "us-central1",
            "zone": "us-central1-a",
            "status": "READY",  # unattached
            "size_gb": 300,
            "created_at": (now - timedelta(days=60)).isoformat(),
            "labels": {},
        })

        # Cloud Storage Bucket
        resources.append({
            "resource_id": f"//storage.googleapis.com/projects/{project}/buckets/enterprise-lake-data",
            "project_id": project,
            "resource_name": "enterprise-lake-data",
            "resource_type": "storage.googleapis.com/Bucket",
            "service_name": "CloudStorage",
            "region": "us-central1",
            "status": "RUNNABLE",
            "created_at": (now - timedelta(days=150)).isoformat(),
            "labels": {
                "owner": "dataeng@enterprise.com",
                "env": "production",
                "cost_center": "cc-8000",
            },
        })

        # Cloud SQL
        resources.append({
            "resource_id": f"//sqladmin.googleapis.com/projects/{project}/instances/postgres-shared-instance",
            "project_id": project,
            "resource_name": "postgres-shared-instance",
            "resource_type": "sqladmin.googleapis.com/Instance",
            "service_name": "CloudSQL",
            "region": "us-central1",
            "status": "RUNNABLE",
            "created_at": (now - timedelta(days=110)).isoformat(),
            "labels": {
                "owner": "dbadmin@enterprise.com",
                "env": "production",
                "cost_center": "cc-9000",
            },
        })

        return resources

    @classmethod
    def export_sample_files(cls, target_dir: str = "backend/sample_data/inventory") -> Dict[str, str]:
        """Exports synthetic sample inventory JSON files to disk."""
        os.makedirs(target_dir, exist_ok=True)

        aws_data = cls.generate_aws_inventory()
        azure_data = cls.generate_azure_inventory()
        gcp_data = cls.generate_gcp_inventory()

        aws_path = os.path.join(target_dir, "aws_inventory_sample.json")
        azure_path = os.path.join(target_dir, "azure_inventory_sample.json")
        gcp_path = os.path.join(target_dir, "gcp_inventory_sample.json")

        with open(aws_path, "w", encoding="utf-8") as f:
            json.dump({"resources": aws_data}, f, indent=2)

        with open(azure_path, "w", encoding="utf-8") as f:
            json.dump({"resources": azure_data}, f, indent=2)

        with open(gcp_path, "w", encoding="utf-8") as f:
            json.dump({"resources": gcp_data}, f, indent=2)

        return {
            "AWS": aws_path,
            "AZURE": azure_path,
            "GCP": gcp_path,
        }
