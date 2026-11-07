"""
CloudSage Synthetic Recommendation Scenarios Generator.
Generates 20 distinct, enterprise-grade multi-cloud recommendation scenarios
across AWS, Azure, and GCP, adhering strictly to the Zero Float Rule.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List
import uuid

from sqlalchemy.orm import Session
from backend.app.core.enums import (
    CloudProvider,
    ImplementationEffort,
    Priority,
    RecommendationAction,
    RecommendationStatus,
    RiskLevel,
    ServiceCategory,
)
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.recommendation import (
    Recommendation,
    RecommendationEvidence,
    RecommendationHistory,
    RecommendationRun,
)
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection
from backend.app.recommendations.correlation import generate_recommendation_key
from backend.app.recommendations.guidance import build_implementation_guidance
from backend.app.recommendations.savings import annualize_savings, build_savings_breakdown


SYNTHETIC_SCENARIOS = [
    # 1. AWS Idle EC2
    {
        "provider": CloudProvider.AWS,
        "account_id": "112233445566",
        "region": "us-east-1",
        "service_name": "AmazonEC2",
        "service_category": ServiceCategory.COMPUTE,
        "resource_id": "i-0a1b2c3d4e5f67890",
        "resource_name": "dev-bastion-host-01",
        "action_type": RecommendationAction.TERMINATE,
        "current_monthly_cost": Decimal("184.5000"),
        "projected_monthly_cost": Decimal("0.0000"),
        "priority": Priority.P2,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.LOW,
        "title": "Terminate Idle EC2 Instance (dev-bastion-host-01)",
        "description": "EC2 instance running in us-east-1 has averaged 0.8% CPU over the past 14 days with zero incoming SSH traffic.",
        "strategy_id": "idle_compute_strategy",
        "tags": {"env": "dev", "owner": "platform-team", "cost_center": "CC-101"},
    },
    # 2. Azure Idle VM
    {
        "provider": CloudProvider.AZURE,
        "account_id": "sub-prod-eastus-01",
        "region": "eastus",
        "service_name": "VirtualMachines",
        "service_category": ServiceCategory.COMPUTE,
        "resource_id": "/subscriptions/sub-prod-eastus-01/resourceGroups/rg-analytics/providers/Microsoft.Compute/virtualMachines/vm-worker-test",
        "resource_name": "vm-worker-test",
        "action_type": RecommendationAction.TERMINATE,
        "current_monthly_cost": Decimal("312.0000"),
        "projected_monthly_cost": Decimal("0.0000"),
        "priority": Priority.P1,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.LOW,
        "title": "Decommission Idle Azure VM (vm-worker-test)",
        "description": "Standard_D8s_v5 VM has been active with no network I/O or batch task activity for 21 days.",
        "strategy_id": "idle_compute_strategy",
        "tags": {"env": "test", "owner": "data-eng", "cost_center": "CC-202"},
    },
    # 3. GCP Idle GCE
    {
        "provider": CloudProvider.GCP,
        "account_id": "prj-ml-research-01",
        "region": "us-central1",
        "service_name": "ComputeEngine",
        "service_category": ServiceCategory.COMPUTE,
        "resource_id": "projects/prj-ml-research-01/zones/us-central1-a/instances/gce-jupyter-idle",
        "resource_name": "gce-jupyter-idle",
        "action_type": RecommendationAction.TERMINATE,
        "current_monthly_cost": Decimal("248.8000"),
        "projected_monthly_cost": Decimal("0.0000"),
        "priority": Priority.P2,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.LOW,
        "title": "Terminate Inactive GCP Notebook Instance (gce-jupyter-idle)",
        "description": "Notebook worker running e2-standard-8 with sub-1% CPU for 18 consecutive days.",
        "strategy_id": "idle_compute_strategy",
        "tags": {"env": "dev", "owner": "ai-research", "cost_center": "CC-303"},
    },
    # 4. AWS EC2 Rightsizing
    {
        "provider": CloudProvider.AWS,
        "account_id": "112233445566",
        "region": "us-west-2",
        "service_name": "AmazonEC2",
        "service_category": ServiceCategory.COMPUTE,
        "resource_id": "i-0987654321fedcba0",
        "resource_name": "api-gateway-node-02",
        "action_type": RecommendationAction.RIGHTSIZE,
        "current_monthly_cost": Decimal("292.0000"),
        "projected_monthly_cost": Decimal("146.0000"),
        "priority": Priority.P2,
        "risk_level": RiskLevel.MEDIUM,
        "implementation_effort": ImplementationEffort.MEDIUM,
        "title": "Rightsize EC2 Instance from m5.2xlarge to m5.xlarge",
        "description": "Instance has sustained average CPU of 14% and memory utilization below 28%. Downsizing cuts compute costs by 50%.",
        "strategy_id": "compute_rightsizing_strategy",
        "tags": {"env": "prod", "owner": "backend-team", "cost_center": "CC-101"},
    },
    # 5. Azure VM Rightsizing
    {
        "provider": CloudProvider.AZURE,
        "account_id": "sub-prod-eastus-01",
        "region": "westeurope",
        "service_name": "VirtualMachines",
        "service_category": ServiceCategory.COMPUTE,
        "resource_id": "/subscriptions/sub-prod-eastus-01/resourceGroups/rg-core/providers/Microsoft.Compute/virtualMachines/vm-payment-gw",
        "resource_name": "vm-payment-gw",
        "action_type": RecommendationAction.RIGHTSIZE,
        "current_monthly_cost": Decimal("480.0000"),
        "projected_monthly_cost": Decimal("240.0000"),
        "priority": Priority.P1,
        "risk_level": RiskLevel.MEDIUM,
        "implementation_effort": ImplementationEffort.MEDIUM,
        "title": "Rightsize Azure VM from Standard_D8s_v5 to Standard_D4s_v5",
        "description": "Production payment gateway node has 8 vCPUs with 95th percentile CPU under 18%. Single-tier downsize preserves headroom.",
        "strategy_id": "compute_rightsizing_strategy",
        "tags": {"env": "prod", "owner": "fintech-team", "cost_center": "CC-202"},
    },
    # 6. GCP GCE Rightsizing
    {
        "provider": CloudProvider.GCP,
        "account_id": "prj-cloudsage-core",
        "region": "europe-west1",
        "service_name": "ComputeEngine",
        "service_category": ServiceCategory.COMPUTE,
        "resource_id": "projects/prj-cloudsage-core/zones/europe-west1-b/instances/gce-cache-node-01",
        "resource_name": "gce-cache-node-01",
        "action_type": RecommendationAction.RIGHTSIZE,
        "current_monthly_cost": Decimal("268.0000"),
        "projected_monthly_cost": Decimal("134.0000"),
        "priority": Priority.P2,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.LOW,
        "title": "Rightsize GCE Instance from e2-standard-8 to e2-standard-4",
        "description": "Cache broker is running with memory utilization under 32% and sub-10% CPU usage.",
        "strategy_id": "compute_rightsizing_strategy",
        "tags": {"env": "staging", "owner": "infra-ops", "cost_center": "CC-303"},
    },
    # 7. AWS Unattached EBS Volume
    {
        "provider": CloudProvider.AWS,
        "account_id": "112233445566",
        "region": "us-east-1",
        "service_name": "AmazonEBS",
        "service_category": ServiceCategory.STORAGE,
        "resource_id": "vol-0123456789abcdef0",
        "resource_name": "unattached-db-data-vol",
        "action_type": RecommendationAction.CLEANUP_UNATTACHED,
        "current_monthly_cost": Decimal("125.0000"),
        "projected_monthly_cost": Decimal("0.0000"),
        "priority": Priority.P3,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.QUICK_WIN,
        "title": "Delete Unattached EBS gp3 Volume (1TB)",
        "description": "1TB gp3 volume detached 45 days ago after instance termination; still incurring monthly provisioned storage charges.",
        "strategy_id": "storage_optimization_strategy",
        "tags": {"env": "dev", "owner": "db-team", "cost_center": "CC-101"},
    },
    # 8. Azure Unattached Managed Disk
    {
        "provider": CloudProvider.AZURE,
        "account_id": "sub-prod-eastus-01",
        "region": "eastus",
        "service_name": "ManagedDisks",
        "service_category": ServiceCategory.STORAGE,
        "resource_id": "/subscriptions/sub-prod-eastus-01/resourceGroups/rg-storage/providers/Microsoft.Compute/disks/disk-scratch-500gb",
        "resource_name": "disk-scratch-500gb",
        "action_type": RecommendationAction.CLEANUP_UNATTACHED,
        "current_monthly_cost": Decimal("78.0000"),
        "projected_monthly_cost": Decimal("0.0000"),
        "priority": Priority.P3,
        "risk_level": RiskLevel.NONE,
        "implementation_effort": ImplementationEffort.QUICK_WIN,
        "title": "Delete Unattached Azure Managed Disk (500GB Premium SSD)",
        "description": "Premium SSD managed disk unattached for over 30 days.",
        "strategy_id": "storage_optimization_strategy",
        "tags": {"env": "test", "owner": "qa-team", "cost_center": "CC-202"},
    },
    # 9. AWS Orphaned EBS Snapshot
    {
        "provider": CloudProvider.AWS,
        "account_id": "112233445566",
        "region": "us-east-1",
        "service_name": "AmazonEBS",
        "service_category": ServiceCategory.STORAGE,
        "resource_id": "snap-0a9b8c7d6e5f43210",
        "resource_name": "temp-migration-snap-2025",
        "action_type": RecommendationAction.DELETE_SNAPSHOT,
        "current_monthly_cost": Decimal("55.0000"),
        "projected_monthly_cost": Decimal("0.0000"),
        "priority": Priority.P3,
        "risk_level": RiskLevel.NONE,
        "implementation_effort": ImplementationEffort.QUICK_WIN,
        "title": "Delete Orphaned EBS Snapshot from 2025",
        "description": "Snapshot associated with decommissioned volume created > 180 days ago.",
        "strategy_id": "storage_optimization_strategy",
        "tags": {"env": "dev", "owner": "infra-ops", "cost_center": "CC-101"},
    },
    # 10. AWS S3 Storage Tiering
    {
        "provider": CloudProvider.AWS,
        "account_id": "112233445566",
        "region": "us-east-1",
        "service_name": "AmazonS3",
        "service_category": ServiceCategory.STORAGE,
        "resource_id": "arn:aws:s3:::corporate-compliance-raw-logs",
        "resource_name": "corporate-compliance-raw-logs",
        "action_type": RecommendationAction.CONVERT_STORAGE_TIER,
        "current_monthly_cost": Decimal("1450.0000"),
        "projected_monthly_cost": Decimal("290.0000"),
        "priority": Priority.P1,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.LOW,
        "title": "Transition Cold S3 Bucket to Glacier Flexible Archive",
        "description": "Over 60TB of access logs older than 90 days stored in S3 Standard. Applying lifecycle transition rule yields 80% cost reduction.",
        "strategy_id": "storage_optimization_strategy",
        "tags": {"env": "prod", "owner": "security-team", "cost_center": "CC-101"},
    },
    # 11. Azure Blob Storage Tiering
    {
        "provider": CloudProvider.AZURE,
        "account_id": "sub-prod-eastus-01",
        "region": "eastus",
        "service_name": "StorageAccounts",
        "service_category": ServiceCategory.STORAGE,
        "resource_id": "/subscriptions/sub-prod-eastus-01/resourceGroups/rg-logs/providers/Microsoft.Storage/storageAccounts/stcoldbackup01",
        "resource_name": "stcoldbackup01",
        "action_type": RecommendationAction.CONVERT_STORAGE_TIER,
        "current_monthly_cost": Decimal("860.0000"),
        "projected_monthly_cost": Decimal("172.0000"),
        "priority": Priority.P1,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.LOW,
        "title": "Transition Azure Blob Container to Cool / Archive Tier",
        "description": "Infrequently accessed audit logs in Hot tier should be moved to Cool tier via lifecycle management policy.",
        "strategy_id": "storage_optimization_strategy",
        "tags": {"env": "prod", "owner": "compliance", "cost_center": "CC-202"},
    },
    # 12. AWS Underutilized RDS Database
    {
        "provider": CloudProvider.AWS,
        "account_id": "112233445566",
        "region": "us-east-1",
        "service_name": "AmazonRDS",
        "service_category": ServiceCategory.DATABASE,
        "resource_id": "arn:aws:rds:us-east-1:112233445566:db:dev-postgres-cluster-01",
        "resource_name": "dev-postgres-cluster-01",
        "action_type": RecommendationAction.RIGHTSIZE,
        "current_monthly_cost": Decimal("640.0000"),
        "projected_monthly_cost": Decimal("320.0000"),
        "priority": Priority.P2,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.MEDIUM,
        "title": "Rightsize Dev RDS Postgres Database (db.m5.2xlarge -> db.m5.xlarge)",
        "description": "Dev database averages 2 active client connections and 6% CPU. Downsizing halves instance charges.",
        "strategy_id": "database_optimization_strategy",
        "tags": {"env": "dev", "owner": "backend-team", "cost_center": "CC-101"},
    },
    # 13. Azure SQL Database Optimization
    {
        "provider": CloudProvider.AZURE,
        "account_id": "sub-prod-eastus-01",
        "region": "eastus",
        "service_name": "SqlDatabase",
        "service_category": ServiceCategory.DATABASE,
        "resource_id": "/subscriptions/sub-prod-eastus-01/resourceGroups/rg-db/providers/Microsoft.Sql/servers/sql-crm-srv/databases/crm-stage",
        "resource_name": "crm-stage",
        "action_type": RecommendationAction.RIGHTSIZE,
        "current_monthly_cost": Decimal("520.0000"),
        "projected_monthly_cost": Decimal("260.0000"),
        "priority": Priority.P2,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.MEDIUM,
        "title": "Reduce DTU / vCore Allocation for Staging Azure SQL DB",
        "description": "Staging SQL database shows under 12% DTU consumption continuously over 30 days.",
        "strategy_id": "database_optimization_strategy",
        "tags": {"env": "stage", "owner": "sales-apps", "cost_center": "CC-202"},
    },
    # 14. GCP Cloud SQL Rightsizing
    {
        "provider": CloudProvider.GCP,
        "account_id": "prj-cloudsage-core",
        "region": "us-central1",
        "service_name": "CloudSQL",
        "service_category": ServiceCategory.DATABASE,
        "resource_id": "projects/prj-cloudsage-core/instances/sql-catalog-replica",
        "resource_name": "sql-catalog-replica",
        "action_type": RecommendationAction.RIGHTSIZE,
        "current_monthly_cost": Decimal("390.0000"),
        "projected_monthly_cost": Decimal("195.0000"),
        "priority": Priority.P2,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.MEDIUM,
        "title": "Rightsize Cloud SQL Read Replica (db-custom-8 -> db-custom-4)",
        "description": "Replica handles minimal read queries with peak CPU below 15%.",
        "strategy_id": "database_optimization_strategy",
        "tags": {"env": "staging", "owner": "catalog-team", "cost_center": "CC-303"},
    },
    # 15. AWS Idle Elastic IP
    {
        "provider": CloudProvider.AWS,
        "account_id": "112233445566",
        "region": "us-east-1",
        "service_name": "AmazonVPC",
        "service_category": ServiceCategory.NETWORKING,
        "resource_id": "eipalloc-01a2b3c4d5e6f7g8h",
        "resource_name": "eip-legacy-gateway",
        "action_type": RecommendationAction.RELEASE_IP,
        "current_monthly_cost": Decimal("7.2000"),
        "projected_monthly_cost": Decimal("0.0000"),
        "priority": Priority.P4,
        "risk_level": RiskLevel.NONE,
        "implementation_effort": ImplementationEffort.QUICK_WIN,
        "title": "Release 2 Unattached AWS Elastic IPs",
        "description": "Static IP addresses unattached to running instances are charged by AWS hourly.",
        "strategy_id": "network_optimization_strategy",
        "tags": {"env": "dev", "owner": "network-team", "cost_center": "CC-101"},
    },
    # 16. Azure Idle Public IP
    {
        "provider": CloudProvider.AZURE,
        "account_id": "sub-prod-eastus-01",
        "region": "eastus",
        "service_name": "PublicIPAddresses",
        "service_category": ServiceCategory.NETWORKING,
        "resource_id": "/subscriptions/sub-prod-eastus-01/resourceGroups/rg-net/providers/Microsoft.Network/publicIPAddresses/pip-old-lb",
        "resource_name": "pip-old-lb",
        "action_type": RecommendationAction.RELEASE_IP,
        "current_monthly_cost": Decimal("5.8000"),
        "projected_monthly_cost": Decimal("0.0000"),
        "priority": Priority.P4,
        "risk_level": RiskLevel.NONE,
        "implementation_effort": ImplementationEffort.QUICK_WIN,
        "title": "Release Unassociated Azure Public IP Address",
        "description": "Public IP resource not bound to any NIC or load balancer frontend.",
        "strategy_id": "network_optimization_strategy",
        "tags": {"env": "test", "owner": "infra-ops", "cost_center": "CC-202"},
    },
    # 17. AWS Anomaly Investigation
    {
        "provider": CloudProvider.AWS,
        "account_id": "112233445566",
        "region": "us-east-1",
        "service_name": "AWSDataTransfer",
        "service_category": ServiceCategory.NETWORKING,
        "resource_id": "arn:aws:ec2:us-east-1:112233445566:natgateway/nat-0123456789abcdef0",
        "resource_name": "nat-main-outbound",
        "action_type": RecommendationAction.INVESTIGATE_ANOMALY,
        "current_monthly_cost": Decimal("2400.0000"),
        "projected_monthly_cost": Decimal("400.0000"),
        "priority": Priority.P1,
        "risk_level": RiskLevel.MEDIUM,
        "implementation_effort": ImplementationEffort.LOW,
        "title": "Investigate High-Severity NAT Gateway Outbound Egress Spike (+480%)",
        "description": "Unbudgeted surge in inter-region and internet data transfer flagged by Anomaly Detection Engine (Z-Score: 4.8).",
        "strategy_id": "anomaly_investigation_strategy",
        "tags": {"env": "prod", "owner": "platform-team", "cost_center": "CC-101"},
    },
    # 18. AWS Compute Savings Plan
    {
        "provider": CloudProvider.AWS,
        "account_id": "112233445566",
        "region": "GLOBAL",
        "service_name": "AmazonEC2",
        "service_category": ServiceCategory.COMPUTE,
        "resource_id": None,
        "resource_name": "EC2-Compute-Savings-Plan",
        "action_type": RecommendationAction.PURCHASE_SAVINGS_PLAN,
        "current_monthly_cost": Decimal("8500.0000"),
        "projected_monthly_cost": Decimal("5950.0000"),
        "priority": Priority.P1,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.LOW,
        "title": "Acquire 1-Year Compute Savings Plan for Steady AWS Workloads",
        "description": "Account maintains a steady $8,500/mo on-demand baseline. A 1-year No Upfront plan saves $2,550/mo ($30,600/yr).",
        "strategy_id": "pricing_usage_strategy",
        "tags": {"env": "prod", "owner": "finops-lead", "cost_center": "FINOPS-CORP"},
    },
    # 19. Azure Reserved Instances
    {
        "provider": CloudProvider.AZURE,
        "account_id": "sub-prod-eastus-01",
        "region": "eastus",
        "service_name": "VirtualMachines",
        "service_category": ServiceCategory.COMPUTE,
        "resource_id": None,
        "resource_name": "Azure-RI-D-Series",
        "action_type": RecommendationAction.RESERVE_CAPACITY,
        "current_monthly_cost": Decimal("4200.0000"),
        "projected_monthly_cost": Decimal("2940.0000"),
        "priority": Priority.P1,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.LOW,
        "title": "Purchase 1-Year Azure Reservations for Standard D-Series Fleet",
        "description": "Production worker cluster runs consistently 24x7 on-demand. 1-year reservation yields 30% savings.",
        "strategy_id": "pricing_usage_strategy",
        "tags": {"env": "prod", "owner": "finops-lead", "cost_center": "FINOPS-CORP"},
    },
    # 20. Non-Prod Environment Scheduling
    {
        "provider": CloudProvider.AWS,
        "account_id": "112233445566",
        "region": "us-east-1",
        "service_name": "AmazonEC2",
        "service_category": ServiceCategory.COMPUTE,
        "resource_id": "i-0feeeddcba9876543",
        "resource_name": "staging-qa-cluster-node",
        "action_type": RecommendationAction.SCHEDULE_SHUTDOWN,
        "current_monthly_cost": Decimal("380.0000"),
        "projected_monthly_cost": Decimal("113.0000"),
        "priority": Priority.P2,
        "risk_level": RiskLevel.LOW,
        "implementation_effort": ImplementationEffort.QUICK_WIN,
        "title": "Enable Nightly & Weekend Shutdown for Staging Node",
        "description": "Staging node runs 24x7 without night/weekend usage. Scheduling shutdown saves 118 idle hours per week (~70% savings).",
        "strategy_id": "environment_scheduling_strategy",
        "tags": {"env": "stage", "owner": "qa-team", "cost_center": "CC-101"},
    },
]


def seed_synthetic_recommendation_scenarios(db: Session) -> List[Recommendation]:
    """
    Seeds all 20 realistic multi-cloud scenarios into PostgreSQL.
    Ensures associated resources, evidence items, and history audit records exist.
    """
    now = datetime.now(timezone.utc)
    seeded_recommendations: List[Recommendation] = []

    for item in SYNTHETIC_SCENARIOS:
        prov_enum: CloudProvider = item["provider"]
        res_id: Optional[str] = item["resource_id"]
        monthly_cost: Decimal = item["current_monthly_cost"]
        projected_cost: Decimal = item["projected_monthly_cost"]
        monthly_savings = monthly_cost - projected_cost
        annual_savings = annualize_savings(monthly_savings)

        # 1. Ensure CloudResource exists if res_id is provided
        if res_id:
            existing_res = db.query(CloudResource).filter(CloudResource.resource_id == res_id).first()
            if not existing_res:
                new_res = CloudResource(
                    resource_id=res_id,
                    provider=prov_enum.value,
                    account_id=item["account_id"],
                    service_category=item["service_category"].value,
                    service_name=item["service_name"],
                    resource_name=item["resource_name"],
                    resource_type="VirtualMachine" if item["service_category"] == ServiceCategory.COMPUTE else "Storage",
                    region=item["region"],
                    environment=item["tags"].get("env", "prod"),
                    owner=item["tags"].get("owner", "cloud-team"),
                    cost_center=item["tags"].get("cost_center", "CC-100"),
                    tags=item["tags"],
                    monthly_cost=monthly_cost,
                    status="ACTIVE",
                    first_discovered_at=now - timedelta(days=60),
                    last_seen_at=now,
                )
                db.add(new_res)
                db.flush()

        rec_key = generate_recommendation_key(
            provider=prov_enum.value,
            account_id=item["account_id"],
            resource_id=res_id,
            action_type=item["action_type"].value,
            strategy_id=item["strategy_id"],
        )

        existing_rec = db.query(Recommendation).filter(Recommendation.recommendation_key == rec_key).first()
        if existing_rec:
            seeded_recommendations.append(existing_rec)
            continue

        guidance = build_implementation_guidance(
            provider=prov_enum,
            action=item["action_type"],
            resource_id=res_id,
            resource_name=item["resource_name"],
        )

        savings_breakdown = build_savings_breakdown(
            current_monthly_cost=monthly_cost,
            projected_monthly_cost=projected_cost,
            monthly_savings=monthly_savings,
            annual_savings=annual_savings,
            formula_name="Synthetic Scenario Projection",
            parameters={"target": item["action_type"].value},
        )

        rec = Recommendation(
            id=uuid.uuid4(),
            recommendation_key=rec_key,
            resource_id=res_id,
            provider=prov_enum.value,
            account_id=item["account_id"],
            region=item["region"],
            service_name=item["service_name"],
            service_category=item["service_category"].value,
            resource_name=item["resource_name"],
            strategy_id=item["strategy_id"],
            strategy_version="1.0",
            action_type=item["action_type"].value,
            priority=item["priority"].value,
            priority_score=Decimal("0.8500") if item["priority"] == Priority.P1 else Decimal("0.6000"),
            risk_level=item["risk_level"].value,
            risk_score=Decimal("0.1000") if item["risk_level"] == RiskLevel.NONE else Decimal("0.2500"),
            confidence_score=Decimal("0.9500"),
            status=RecommendationStatus.PROPOSED.value,
            current_monthly_cost=monthly_cost,
            projected_monthly_cost=projected_cost,
            estimated_monthly_savings=monthly_savings,
            estimated_annual_savings=annual_savings,
            currency="USD",
            implementation_effort=item["implementation_effort"].value,
            title=item["title"],
            description=item["description"],
            remediation_guide=guidance["cli_snippet"],
            savings_calculation=savings_breakdown,
            implementation_guidance=guidance,
            assumptions=["Generated synthetic benchmark scenario."],
            evidence_summary={"scenario_id": item["title"]},
            tags=item["tags"],
            created_at=now,
            updated_at=now,
        )
        db.add(rec)
        db.flush()

        # Add Evidence Item
        ev = RecommendationEvidence(
            id=uuid.uuid4(),
            recommendation_id=rec.id,
            evidence_type="SYNTHETIC_BENCHMARK",
            resource_id=res_id,
            description=f"Synthetic telemetry for {item['title']}",
            telemetry_data={"monthly_cost": str(monthly_cost), "projected_cost": str(projected_cost)},
            confidence_score=Decimal("0.9500"),
            created_at=now,
        )
        db.add(ev)

        # Add History Item
        hist = RecommendationHistory(
            id=uuid.uuid4(),
            recommendation_id=rec.id,
            from_status=None,
            to_status="PROPOSED",
            actor="SyntheticScenarioGenerator",
            action="PROPOSAL_CREATED",
            notes="Seeded synthetic benchmark scenario",
            details={"monthly_savings": str(monthly_savings)},
            created_at=now,
        )
        db.add(hist)

        seeded_recommendations.append(rec)

    db.commit()
    return seeded_recommendations
