"""
CloudSage Synthetic Waste Demonstration Scenarios.
Generates reproducible test scenarios covering all 14 FinOps edge cases specified in Stage 6.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from backend.app.core.enums import CloudProvider, ServiceCategory
from backend.app.models.billing import BillingRecord
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource, ResourceMetric


class SyntheticWasteScenarioGenerator:
    """Generates 14 deterministic synthetic test scenarios for waste detection verification."""

    @classmethod
    def seed_all_scenarios(cls, db: Session) -> Dict[str, str]:
        """Seeds all 14 scenarios into the database."""
        now = datetime.now(timezone.utc)
        scenario_map = {}

        # Scenario 1: Idle AWS EC2 instance with continuous compute charges
        s1_id = "arn:aws:ec2:us-east-1:123456789012:instance/i-scen-01-idle-aws"
        r1 = CloudResource(
            resource_id=s1_id,
            provider="AWS",
            account_id="123456789012",
            resource_name="prod-web-idle",
            service_category="COMPUTE",
            service_name="AmazonEC2",
            resource_type="ec2:instance",
            region="us-east-1",
            status="active",
            monthly_cost=Decimal("180.0000"),
            discovery_status="CONFIRMED",
            resource_metadata={"instance_type": "m5.large"},
        )
        db.add(r1)
        # 7 days of low CPU (< 5%) and low network
        for day in range(7):
            ts = now - timedelta(days=day)
            db.add(ResourceMetric(
                resource_id=s1_id,
                metric_name="cpu_utilization_pct",
                timestamp=ts,
                average_value=Decimal("2.1000"),
                peak_value=Decimal("4.5000"),
                sample_count=24,
            ))
            db.add(ResourceMetric(
                resource_id=s1_id,
                metric_name="network_in_bytes",
                timestamp=ts,
                average_value=Decimal("100000.0"),  # ~0.1 MB/day
                peak_value=Decimal("200000.0"),
                sample_count=24,
            ))
        scenario_map["scen_01_idle_aws_ec2"] = s1_id

        # Scenario 2: Underutilized Azure VM with sufficient CPU observations
        s2_id = "/subscriptions/sub-az/resourceGroups/rg-scen/providers/Microsoft.Compute/virtualMachines/vm-scen-02-underutilized"
        r2 = CloudResource(
            resource_id=s2_id,
            provider="AZURE",
            account_id="sub-az",
            resource_name="vm-az-underutilized",
            service_category="COMPUTE",
            service_name="VirtualMachines",
            resource_type="Microsoft.Compute/virtualMachines",
            region="eastus",
            status="active",
            monthly_cost=Decimal("240.0000"),
            discovery_status="CONFIRMED",
            resource_metadata={"vm_size": "Standard_D4s_v3"},
        )
        db.add(r2)
        for day in range(7):
            db.add(ResourceMetric(
                resource_id=s2_id,
                metric_name="Percentage CPU",
                timestamp=now - timedelta(days=day),
                average_value=Decimal("3.2000"),
                peak_value=Decimal("8.5000"),
                sample_count=24,
            ))
        scenario_map["scen_02_underutilized_azure_vm"] = s2_id

        # Scenario 3: Oversized GCP Compute Engine instance
        s3_id = "//compute.googleapis.com/projects/proj-gcp/zones/us-central1-a/instances/gce-scen-03-oversized"
        r3 = CloudResource(
            resource_id=s3_id,
            provider="GCP",
            account_id="proj-gcp",
            resource_name="gce-big-oversized",
            service_category="COMPUTE",
            service_name="ComputeEngine",
            resource_type="compute.googleapis.com/Instance",
            region="us-central1",
            status="active",
            monthly_cost=Decimal("450.0000"),
            discovery_status="CONFIRMED",
            resource_metadata={"machine_type": "n2-standard-16", "vcpus": 16},
        )
        db.add(r3)
        for day in range(14):
            db.add(ResourceMetric(
                resource_id=s3_id,
                metric_name="cpu_utilization",
                timestamp=now - timedelta(days=day),
                average_value=Decimal("12.5000"),  # Between 5% and 20%
                peak_value=Decimal("38.0000"),    # < 50%
                sample_count=24,
            ))
        scenario_map["scen_03_oversized_gcp_instance"] = s3_id

        # Scenario 4: Unattached AWS EBS volume
        s4_id = "arn:aws:ec2:us-east-1:123456789012:volume/vol-scen-04-unattached"
        r4 = CloudResource(
            resource_id=s4_id,
            provider="AWS",
            account_id="123456789012",
            resource_name="ebs-unattached-spare",
            service_category="STORAGE",
            service_name="AmazonEC2",
            resource_type="ec2:volume",
            region="us-east-1",
            status="available",  # unattached
            monthly_cost=Decimal("80.0000"),
            first_discovered_at=now - timedelta(days=15),
            resource_metadata={"size_gb": 1000},
        )
        db.add(r4)
        scenario_map["scen_04_unattached_aws_ebs"] = s4_id

        # Scenario 5: Unattached Azure Managed Disk
        s5_id = "/subscriptions/sub-az/resourceGroups/rg-scen/providers/Microsoft.Compute/disks/disk-scen-05-unattached"
        r5 = CloudResource(
            resource_id=s5_id,
            provider="AZURE",
            account_id="sub-az",
            resource_name="az-disk-unattached",
            service_category="STORAGE",
            service_name="ManagedDisks",
            resource_type="Microsoft.Compute/disks",
            region="eastus",
            status="Unattached",
            monthly_cost=Decimal("40.0000"),
            first_discovered_at=now - timedelta(days=10),
            resource_metadata={"size_gb": 500},
        )
        db.add(r5)
        scenario_map["scen_05_unattached_azure_disk"] = s5_id

        # Scenario 6: Detached GCP Persistent Disk
        s6_id = "//compute.googleapis.com/projects/proj-gcp/zones/us-central1-a/disks/gce-scen-06-detached"
        r6 = CloudResource(
            resource_id=s6_id,
            provider="GCP",
            account_id="proj-gcp",
            resource_name="gce-disk-detached",
            service_category="STORAGE",
            service_name="ComputeEngine",
            resource_type="compute.googleapis.com/Disk",
            region="us-central1",
            status="READY",  # unattached
            monthly_cost=Decimal("25.0000"),
            first_discovered_at=now - timedelta(days=8),
            resource_metadata={"size_gb": 300},
        )
        db.add(r6)
        scenario_map["scen_06_detached_gcp_disk"] = s6_id

        # Scenario 7: Orphaned AWS snapshot with deleted parent volume
        s7_id = "arn:aws:ec2:us-east-1:123456789012:snapshot/snap-scen-07-orphaned"
        r7 = CloudResource(
            resource_id=s7_id,
            provider="AWS",
            account_id="123456789012",
            resource_name="snap-old-orphaned",
            service_category="STORAGE",
            service_name="AmazonEC2",
            resource_type="ec2:snapshot",
            region="us-east-1",
            status="completed",
            monthly_cost=Decimal("35.0000"),
            first_discovered_at=now - timedelta(days=90),
        )
        db.add(r7)
        # Relationship indicating parent volume was deleted
        db.add(ResourceRelationship(
            source_resource_id=s7_id,
            target_resource_id="vol-deleted-nonexistent",
            relationship_type="SNAPSHOT_OF",
            provider="AWS",
            relationship_metadata={"parent_deleted": True},
        ))
        scenario_map["scen_07_orphaned_aws_snapshot"] = s7_id

        # Scenario 8: Azure snapshot with retention tags (informational, not waste)
        s8_id = "/subscriptions/sub-az/resourceGroups/rg-scen/providers/Microsoft.Compute/snapshots/snap-scen-08-compliance"
        r8 = CloudResource(
            resource_id=s8_id,
            provider="AZURE",
            account_id="sub-az",
            resource_name="snap-compliance-backup",
            service_category="STORAGE",
            service_name="ManagedDisks",
            resource_type="Microsoft.Compute/snapshots",
            region="eastus",
            status="Succeeded",
            monthly_cost=Decimal("15.0000"),
            tags={"retention": "7_years_compliance", "donotdelete": "true"},
            first_discovered_at=now - timedelta(days=120),
        )
        db.add(r8)
        scenario_map["scen_08_compliance_azure_snapshot"] = s8_id

        # Scenario 9: Underutilized Managed Database with connection metrics
        s9_id = "arn:aws:rds:us-east-1:123456789012:db:rds-scen-09-underutilized"
        r9 = CloudResource(
            resource_id=s9_id,
            provider="AWS",
            account_id="123456789012",
            resource_name="aurora-idle-db",
            service_category="DATABASE",
            service_name="AmazonRDS",
            resource_type="rds:db",
            region="us-east-1",
            status="available",
            monthly_cost=Decimal("310.0000"),
        )
        db.add(r9)
        for day in range(7):
            db.add(ResourceMetric(
                resource_id=s9_id,
                metric_name="DatabaseConnections",
                timestamp=now - timedelta(days=day),
                average_value=Decimal("0.5000"),  # Near zero connections
                peak_value=Decimal("1.0000"),
                sample_count=24,
            ))
            db.add(ResourceMetric(
                resource_id=s9_id,
                metric_name="cpu_utilization_pct",
                timestamp=now - timedelta(days=day),
                average_value=Decimal("1.8000"),
                peak_value=Decimal("4.0000"),
                sample_count=24,
            ))
        scenario_map["scen_09_underutilized_database"] = s9_id

        # Scenario 10: Stale resource with recurring billing charges
        s10_id = "arn:aws:ec2:us-east-1:123456789012:instance/i-scen-10-stale"
        r10 = CloudResource(
            resource_id=s10_id,
            provider="AWS",
            account_id="123456789012",
            resource_name="abandoned-old-node",
            service_category="COMPUTE",
            service_name="AmazonEC2",
            resource_type="ec2:instance",
            region="us-east-1",
            status="active",
            monthly_cost=Decimal("120.0000"),
            discovery_status="STALE",  # Not observed in >14 days
            last_inventory_sync_at=now - timedelta(days=25),
        )
        db.add(r10)
        scenario_map["scen_10_stale_resource_billing"] = s10_id

        # Scenario 11: Compute instance with MISSING metrics (produces INSUFFICIENT_DATA)
        s11_id = "arn:aws:ec2:us-east-1:123456789012:instance/i-scen-11-missing-metrics"
        r11 = CloudResource(
            resource_id=s11_id,
            provider="AWS",
            account_id="123456789012",
            resource_name="instance-no-metrics",
            service_category="COMPUTE",
            service_name="AmazonEC2",
            resource_type="ec2:instance",
            region="us-east-1",
            status="active",
            monthly_cost=Decimal("95.0000"),
        )
        db.add(r11)
        scenario_map["scen_11_missing_metrics"] = s11_id

        # Scenario 12: Compute instance with INSUFFICIENT observation window (< 3 days)
        s12_id = "arn:aws:ec2:us-east-1:123456789012:instance/i-scen-12-insufficient-history"
        r12 = CloudResource(
            resource_id=s12_id,
            provider="AWS",
            account_id="123456789012",
            resource_name="new-instance-short-window",
            service_category="COMPUTE",
            service_name="AmazonEC2",
            resource_type="ec2:instance",
            region="us-east-1",
            status="active",
            monthly_cost=Decimal("150.0000"),
        )
        db.add(r12)
        # Only 1 day of metrics
        db.add(ResourceMetric(
            resource_id=s12_id,
            metric_name="cpu_utilization_pct",
            timestamp=now - timedelta(hours=12),
            average_value=Decimal("2.0000"),
            peak_value=Decimal("3.0000"),
            sample_count=12,
        ))
        scenario_map["scen_12_insufficient_history"] = s12_id

        # Scenario 13: Conflicting utilization signals (low CPU < 5%, but high network > 100 MB/day)
        s13_id = "arn:aws:ec2:us-east-1:123456789012:instance/i-scen-13-conflicting-signals"
        r13 = CloudResource(
            resource_id=s13_id,
            provider="AWS",
            account_id="123456789012",
            resource_name="proxy-gateway-node",
            service_category="COMPUTE",
            service_name="AmazonEC2",
            resource_type="ec2:instance",
            region="us-east-1",
            status="active",
            monthly_cost=Decimal("170.0000"),
        )
        db.add(r13)
        for day in range(7):
            ts = now - timedelta(days=day)
            db.add(ResourceMetric(
                resource_id=s13_id,
                metric_name="cpu_utilization_pct",
                timestamp=ts,
                average_value=Decimal("2.5000"),  # Low CPU
                peak_value=Decimal("5.0000"),
                sample_count=24,
            ))
            db.add(ResourceMetric(
                resource_id=s13_id,
                metric_name="network_in_bytes",
                timestamp=ts,
                average_value=Decimal("524288000.0"),  # 500 MB/day (High network!)
                peak_value=Decimal("1048576000.0"),
                sample_count=24,
            ))
        scenario_map["scen_13_conflicting_signals"] = s13_id

        # Scenario 14: Resource with NO reliable cost evidence ($0.0000)
        s14_id = "arn:aws:ec2:us-east-1:123456789012:volume/vol-scen-14-zero-cost"
        r14 = CloudResource(
            resource_id=s14_id,
            provider="AWS",
            account_id="123456789012",
            resource_name="vol-free-tier",
            service_category="STORAGE",
            service_name="AmazonEC2",
            resource_type="ec2:volume",
            region="us-east-1",
            status="available",
            monthly_cost=Decimal("0.0000"),
            first_discovered_at=now - timedelta(days=5),
            resource_metadata={},  # No size_gb
        )
        db.add(r14)
        scenario_map["scen_14_zero_cost"] = s14_id

        db.commit()
        return scenario_map
