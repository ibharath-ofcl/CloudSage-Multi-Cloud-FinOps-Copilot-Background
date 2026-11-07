"""
CloudSage 20 Synthetic Multi-Cloud Anomaly Scenarios Generator.
Generates comprehensive 30-day baseline and anomalous billing records + inventory resources
for 20 real-world enterprise FinOps cost spike and structural shift scenarios across AWS, Azure, and GCP.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource


SYNTHETIC_SCENARIO_DEFINITIONS = [
    # 1. AWS EC2 Auto-Scaling Loop Surge
    {
        "id": "SCEN_01_AWS_EC2_AUTOSCALE_SURGE",
        "name": "AWS EC2 Auto-Scaling Loop Surge",
        "provider": "AWS",
        "account_id": "111122223333",
        "service_category": "COMPUTE",
        "service_name": "AmazonEC2",
        "region": "us-east-1",
        "resource_id": "arn:aws:ec2:us-east-1:111122223333:instance/i-autoscale-rogue",
        "resource_name": "checkout-service-worker-pool",
        "resource_type": "ec2:instance",
        "sku": "c5.4xlarge-Hourly",
        "baseline_daily_cost": Decimal("150.0000"),
        "anomaly_daily_cost": Decimal("1450.0000"),
        "usage_quantity": Decimal("1200.0000"),
        "owner": "platform-eng@company.com",
        "env": "production",
        "category": "SERVICE_SPIKE",
    },
    # 2. AWS DynamoDB Provisioned Throughput Spike
    {
        "id": "SCEN_02_AWS_DYNAMODB_THROUGHPUT_SPIKE",
        "name": "AWS DynamoDB Provisioned Capacity Spike",
        "provider": "AWS",
        "account_id": "111122223333",
        "service_category": "DATABASE",
        "service_name": "AmazonDynamoDB",
        "region": "us-east-1",
        "resource_id": "arn:aws:dynamodb:us-east-1:111122223333:table/OrderEvents",
        "resource_name": "OrderEvents",
        "resource_type": "dynamodb:table",
        "sku": "TimedThroughput-WriteCapacity",
        "baseline_daily_cost": Decimal("45.0000"),
        "anomaly_daily_cost": Decimal("680.0000"),
        "usage_quantity": Decimal("10000.0000"),
        "owner": "backend-team@company.com",
        "env": "production",
        "category": "RESOURCE_SPIKE",
    },
    # 3. AWS S3 Cross-Region Data Transfer Surge
    {
        "id": "SCEN_03_AWS_S3_CROSS_REGION_TRANSFER",
        "name": "AWS S3 Cross-Region Data Transfer Surge",
        "provider": "AWS",
        "account_id": "111122223333",
        "service_category": "STORAGE",
        "service_name": "AmazonS3",
        "region": "us-east-1",
        "resource_id": "arn:aws:s3:::analytics-lake-backup",
        "resource_name": "analytics-lake-backup",
        "resource_type": "s3:bucket",
        "sku": "DataTransfer-Out-Bytes",
        "baseline_daily_cost": Decimal("20.0000"),
        "anomaly_daily_cost": Decimal("520.0000"),
        "usage_quantity": Decimal("26000.0000"),
        "owner": "data-eng@company.com",
        "env": "production",
        "category": "SERVICE_SPIKE",
    },
    # 4. AWS SageMaker Training Endpoint Forgotten
    {
        "id": "SCEN_04_AWS_SAGEMAKER_ENDPOINT_ORPHAN",
        "name": "AWS SageMaker Forgotten GPU Endpoint",
        "provider": "AWS",
        "account_id": "111122223333",
        "service_category": "AI_ML",
        "service_name": "AmazonSageMaker",
        "region": "us-west-2",
        "resource_id": "arn:aws:sagemaker:us-west-2:111122223333:endpoint/llm-finetune-p3",
        "resource_name": "llm-finetune-p3",
        "resource_type": "sagemaker:endpoint",
        "sku": "ml.p3.8xlarge-Hourly",
        "baseline_daily_cost": Decimal("0.0000"),  # New spend
        "anomaly_daily_cost": Decimal("580.0000"),
        "usage_quantity": Decimal("24.0000"),
        "owner": "ml-research@company.com",
        "env": "dev",
        "category": "NEW_SPEND",
    },
    # 5. AWS NAT Gateway Data Processing Explosion
    {
        "id": "SCEN_05_AWS_NAT_GATEWAY_EXPLOSION",
        "name": "AWS NAT Gateway Processing Surge",
        "provider": "AWS",
        "account_id": "111122223333",
        "service_category": "NETWORK",
        "service_name": "AmazonVPC",
        "region": "us-east-1",
        "resource_id": "arn:aws:ec2:us-east-1:111122223333:natgateway/nat-0987654321fedcba",
        "resource_name": "main-vpc-nat-gw",
        "resource_type": "vpc:natgateway",
        "sku": "NatGateway-Bytes",
        "baseline_daily_cost": Decimal("35.0000"),
        "anomaly_daily_cost": Decimal("620.0000"),
        "usage_quantity": Decimal("14000.0000"),
        "owner": "devops@company.com",
        "env": "production",
        "category": "SERVICE_SPIKE",
    },
    # 6. AWS RDS Database Read Replica Stampede
    {
        "id": "SCEN_06_AWS_RDS_REPLICA_STAMPEDE",
        "name": "AWS RDS Overprovisioned Read Replicas",
        "provider": "AWS",
        "account_id": "111122223333",
        "service_category": "DATABASE",
        "service_name": "AmazonRDS",
        "region": "us-east-1",
        "resource_id": "arn:aws:rds:us-east-1:111122223333:db:aurora-prod-ro-pool",
        "resource_name": "aurora-prod-ro-pool",
        "resource_type": "rds:cluster-instance",
        "sku": "db.r5.4xlarge-Hourly",
        "baseline_daily_cost": Decimal("180.0000"),
        "anomaly_daily_cost": Decimal("890.0000"),
        "usage_quantity": Decimal("120.0000"),
        "owner": "dba@company.com",
        "env": "production",
        "category": "RESOURCE_SPIKE",
    },
    # 7. Azure Virtual Machines Batch Job Runaway
    {
        "id": "SCEN_07_AZURE_BATCH_RUNAWAY_VMS",
        "name": "Azure Batch Worker Pool Runaway",
        "provider": "AZURE",
        "account_id": "sub-prod-001",
        "service_category": "COMPUTE",
        "service_name": "Virtual Machines",
        "region": "eastus",
        "resource_id": "/subscriptions/sub-prod-001/resourceGroups/rg-batch/providers/Microsoft.Compute/virtualMachines/batch-worker-vm",
        "resource_name": "batch-worker-pool-vm",
        "resource_type": "Microsoft.Compute/virtualMachines",
        "sku": "Standard_D8s_v5",
        "baseline_daily_cost": Decimal("60.0000"),
        "anomaly_daily_cost": Decimal("750.0000"),
        "usage_quantity": Decimal("960.0000"),
        "owner": "analytics@company.com",
        "env": "production",
        "category": "RESOURCE_SPIKE",
    },
    # 8. Azure SQL Database Elastic Pool DTU Escalation
    {
        "id": "SCEN_08_AZURE_SQL_ELASTIC_POOL_SPIKE",
        "name": "Azure SQL Elastic Pool Scale-Up",
        "provider": "AZURE",
        "account_id": "sub-prod-001",
        "service_category": "DATABASE",
        "service_name": "SQL Database",
        "region": "eastus",
        "resource_id": "/subscriptions/sub-prod-001/resourceGroups/rg-data/providers/Microsoft.Sql/servers/sql-srv-prod/elasticPools/pool-core",
        "resource_name": "pool-core-production",
        "resource_type": "Microsoft.Sql/elasticPools",
        "sku": "GP_Gen5_64",
        "baseline_daily_cost": Decimal("110.0000"),
        "anomaly_daily_cost": Decimal("980.0000"),
        "usage_quantity": Decimal("24.0000"),
        "owner": "db-admin@company.com",
        "env": "production",
        "category": "SERVICE_SPIKE",
    },
    # 9. Azure Cosmos DB Request Units (RU/s) Misconfiguration
    {
        "id": "SCEN_09_AZURE_COSMOS_RU_OVERRIDE",
        "name": "Azure Cosmos DB Provisioned RU/s Surge",
        "provider": "AZURE",
        "account_id": "sub-prod-001",
        "service_category": "DATABASE",
        "service_name": "Azure Cosmos DB",
        "region": "westus2",
        "resource_id": "/subscriptions/sub-prod-001/resourceGroups/rg-cosmos/providers/Microsoft.DocumentDB/databaseAccounts/cosmos-session-store",
        "resource_name": "cosmos-session-store",
        "resource_type": "Microsoft.DocumentDB/databaseAccounts",
        "sku": "100_RU/s_Provisioned",
        "baseline_daily_cost": Decimal("40.0000"),
        "anomaly_daily_cost": Decimal("600.0000"),
        "usage_quantity": Decimal("50000.0000"),
        "owner": "app-dev@company.com",
        "env": "production",
        "category": "RESOURCE_SPIKE",
    },
    # 10. Azure App Service Premium Plan Scaling Surge
    {
        "id": "SCEN_10_AZURE_APP_SERVICE_SCALE_SURGE",
        "name": "Azure App Service Max Workers Surge",
        "provider": "AZURE",
        "account_id": "sub-prod-001",
        "service_category": "COMPUTE",
        "service_name": "Azure App Service",
        "region": "eastus",
        "resource_id": "/subscriptions/sub-prod-001/resourceGroups/rg-web/providers/Microsoft.Web/serverfarms/asp-frontend",
        "resource_name": "asp-frontend-prod",
        "resource_type": "Microsoft.Web/serverfarms",
        "sku": "P2v3-Hourly",
        "baseline_daily_cost": Decimal("75.0000"),
        "anomaly_daily_cost": Decimal("690.0000"),
        "usage_quantity": Decimal("720.0000"),
        "owner": "frontend-team@company.com",
        "env": "production",
        "category": "SERVICE_SPIKE",
    },
    # 11. Azure Blob Storage Hot Tier Sudden Migration
    {
        "id": "SCEN_11_AZURE_BLOB_HOT_TIER_MIGRATION",
        "name": "Azure Blob Archive to Hot Tier Surge",
        "provider": "AZURE",
        "account_id": "sub-prod-001",
        "service_category": "STORAGE",
        "service_name": "Storage Accounts",
        "region": "eastus",
        "resource_id": "/subscriptions/sub-prod-001/resourceGroups/rg-storage/providers/Microsoft.Storage/storageAccounts/stcoldarchive01",
        "resource_name": "stcoldarchive01",
        "resource_type": "Microsoft.Storage/storageAccounts",
        "sku": "Hot-DataStored-GB",
        "baseline_daily_cost": Decimal("25.0000"),
        "anomaly_daily_cost": Decimal("550.0000"),
        "usage_quantity": Decimal("50000.0000"),
        "owner": "storage-admin@company.com",
        "env": "production",
        "category": "RESOURCE_SPIKE",
    },
    # 12. Azure Bandwidth Inter-Region Egress Leak
    {
        "id": "SCEN_12_AZURE_INTER_REGION_EGRESS",
        "name": "Azure Inter-Region Egress Surge",
        "provider": "AZURE",
        "account_id": "sub-prod-001",
        "service_category": "NETWORK",
        "service_name": "Bandwidth",
        "region": "eastus",
        "resource_id": "/subscriptions/sub-prod-001/resourceGroups/rg-net/providers/Microsoft.Network/bandwidth/egress-backup",
        "resource_name": "egress-backup-stream",
        "resource_type": "Microsoft.Network/bandwidth",
        "sku": "DataTransfer-Out-Zone1",
        "baseline_daily_cost": Decimal("15.0000"),
        "anomaly_daily_cost": Decimal("480.0000"),
        "usage_quantity": Decimal("9000.0000"),
        "owner": "infra@company.com",
        "env": "production",
        "category": "SERVICE_SPIKE",
    },
    # 13. GCP Compute Engine GPU Cluster Spin-Up
    {
        "id": "SCEN_13_GCP_COMPUTE_GPU_CLUSTER",
        "name": "GCP Compute Engine A100 GPU Cluster",
        "provider": "GCP",
        "account_id": "prj-ml-prod-888",
        "service_category": "COMPUTE",
        "service_name": "Compute Engine",
        "region": "us-central1",
        "resource_id": "//compute.googleapis.com/projects/prj-ml-prod-888/zones/us-central1-a/instances/gpu-worker-a100-01",
        "resource_name": "gpu-worker-a100-01",
        "resource_type": "compute.googleapis.com/Instance",
        "sku": "NVIDIA-A100-GPU-Hourly",
        "baseline_daily_cost": Decimal("50.0000"),
        "anomaly_daily_cost": Decimal("1650.0000"),
        "usage_quantity": Decimal("96.0000"),
        "owner": "ai-lead@company.com",
        "env": "production",
        "category": "RESOURCE_SPIKE",
    },
    # 14. GCP BigQuery Unpartitioned Multi-Terabyte Query Loop
    {
        "id": "SCEN_14_GCP_BIGQUERY_UNPARTITIONED_LOOP",
        "name": "GCP BigQuery Unpartitioned Analysis Loop",
        "provider": "GCP",
        "account_id": "prj-analytics-777",
        "service_category": "ANALYTICS",
        "service_name": "BigQuery",
        "region": "us-central1",
        "resource_id": "//bigquery.googleapis.com/projects/prj-analytics-777/datasets/clickstream/tables/events_all",
        "resource_name": "events_all",
        "resource_type": "bigquery.googleapis.com/Table",
        "sku": "Analysis-TB",
        "baseline_daily_cost": Decimal("80.0000"),
        "anomaly_daily_cost": Decimal("1250.0000"),
        "usage_quantity": Decimal("200.0000"),
        "owner": "data-analyst@company.com",
        "env": "production",
        "category": "SERVICE_SPIKE",
    },
    # 15. GCP Cloud Spanner Node Allocation Leap
    {
        "id": "SCEN_15_GCP_SPANNER_NODE_LEAP",
        "name": "GCP Cloud Spanner Node Expansion",
        "provider": "GCP",
        "account_id": "prj-core-banking-999",
        "service_category": "DATABASE",
        "service_name": "Cloud Spanner",
        "region": "us-central1",
        "resource_id": "//spanner.googleapis.com/projects/prj-core-banking-999/instances/spanner-core-ledger",
        "resource_name": "spanner-core-ledger",
        "resource_type": "spanner.googleapis.com/Instance",
        "sku": "Spanner-Node-Hour",
        "baseline_daily_cost": Decimal("72.0000"),
        "anomaly_daily_cost": Decimal("720.0000"),
        "usage_quantity": Decimal("240.0000"),
        "owner": "fin-infra@company.com",
        "env": "production",
        "category": "RESOURCE_SPIKE",
    },
    # 16. GCP Cloud Storage Multi-Regional Egress Surge
    {
        "id": "SCEN_16_GCP_GCS_EGRESS_SURGE",
        "name": "GCP Cloud Storage Public Egress Surge",
        "provider": "GCP",
        "account_id": "prj-analytics-777",
        "service_category": "STORAGE",
        "service_name": "Cloud Storage",
        "region": "us-central1",
        "resource_id": "//storage.googleapis.com/public-assets-prod",
        "resource_name": "public-assets-prod",
        "resource_type": "storage.googleapis.com/Bucket",
        "sku": "Network-Egress-Worldwide",
        "baseline_daily_cost": Decimal("30.0000"),
        "anomaly_daily_cost": Decimal("590.0000"),
        "usage_quantity": Decimal("6000.0000"),
        "owner": "webmaster@company.com",
        "env": "production",
        "category": "SERVICE_SPIKE",
    },
    # 17. GCP Google Kubernetes Engine (GKE) Cluster Node Pool Explosion
    {
        "id": "SCEN_17_GCP_GKE_NODE_POOL_EXPLOSION",
        "name": "GCP GKE Cluster Autoscaler Surge",
        "provider": "GCP",
        "account_id": "prj-core-banking-999",
        "service_category": "COMPUTE",
        "service_name": "Google Kubernetes Engine",
        "region": "us-central1",
        "resource_id": "//container.googleapis.com/projects/prj-core-banking-999/zones/us-central1-a/clusters/k8s-prod-cluster",
        "resource_name": "k8s-prod-cluster",
        "resource_type": "container.googleapis.com/Cluster",
        "sku": "GKE-Enterprise-vCPU",
        "baseline_daily_cost": Decimal("140.0000"),
        "anomaly_daily_cost": Decimal("1100.0000"),
        "usage_quantity": Decimal("1500.0000"),
        "owner": "sre@company.com",
        "env": "production",
        "category": "SERVICE_SPIKE",
    },
    # 18. Multi-Cloud Log Ingestion Rate Surge
    {
        "id": "SCEN_18_AWS_CLOUDWATCH_LOG_SURGE",
        "name": "AWS CloudWatch Debug Logs Surge",
        "provider": "AWS",
        "account_id": "111122223333",
        "service_category": "MONITORING",
        "service_name": "AmazonCloudWatch",
        "region": "us-east-1",
        "resource_id": "arn:aws:logs:us-east-1:111122223333:log-group:/aws/k8s/application-prod",
        "resource_name": "/aws/k8s/application-prod",
        "resource_type": "logs:loggroup",
        "sku": "DataScanned-LogIngestion",
        "baseline_daily_cost": Decimal("25.0000"),
        "anomaly_daily_cost": Decimal("490.0000"),
        "usage_quantity": Decimal("980.0000"),
        "owner": "observability@company.com",
        "env": "production",
        "category": "SERVICE_SPIKE",
    },
    # 19. SKU Price / Rate Change
    {
        "id": "SCEN_19_AWS_SKU_PRICE_DIVERGENCE",
        "name": "AWS Dedicated Host Rate Shift",
        "provider": "AWS",
        "account_id": "111122223333",
        "service_category": "COMPUTE",
        "service_name": "AmazonEC2",
        "region": "us-west-2",
        "resource_id": "arn:aws:ec2:us-west-2:111122223333:dedicated-host/h-0123456789abcdef0",
        "resource_name": "h-0123456789abcdef0",
        "resource_type": "ec2:dedicated-host",
        "sku": "r5-DedicatedHost-Hourly",
        "baseline_daily_cost": Decimal("100.0000"),
        "anomaly_daily_cost": Decimal("250.0000"),
        "usage_quantity": Decimal("24.0000"),  # Same 24h usage, but cost surged 2.5x
        "owner": "procurement@company.com",
        "env": "production",
        "category": "SKU_PRICE_CHANGE",
    },
    # 20. Sudden Persistent Step Increase Post-Deployment
    {
        "id": "SCEN_20_AZURE_PERSISTENT_STEP_DEPLOYMENT",
        "name": "Azure Microservices v2.0 Permanent Step Shift",
        "provider": "AZURE",
        "account_id": "sub-prod-001",
        "service_category": "COMPUTE",
        "service_name": "Azure Container Apps",
        "region": "eastus",
        "resource_id": "/subscriptions/sub-prod-001/resourceGroups/rg-apps/providers/Microsoft.App/containerApps/auth-service-v2",
        "resource_name": "auth-service-v2",
        "resource_type": "Microsoft.App/containerApps",
        "sku": "ContainerApps-ActivevCPU-Hour",
        "baseline_daily_cost": Decimal("85.0000"),
        "anomaly_daily_cost": Decimal("480.0000"),  # Remains elevated across multiple days
        "usage_quantity": Decimal("500.0000"),
        "owner": "auth-team@company.com",
        "env": "production",
        "category": "PERSISTENT_STEP",
    },
]


def seed_synthetic_anomalies(
    db: Session,
    reference_date: Optional[date] = None,
    baseline_days: int = 21,
) -> Dict[str, Any]:
    """
    Seeds database with all 20 realistic synthetic anomaly scenarios.
    Creates underlying Stage 5 CloudResource inventory items and 30+ days of BillingRecords.
    """
    if not reference_date:
        reference_date = date.today()

    total_resources = 0
    total_billing_records = 0

    for scen in SYNTHETIC_SCENARIO_DEFINITIONS:
        p = scen["provider"]
        acc = scen["account_id"]
        res_id = scen["resource_id"]
        res_name = scen["resource_name"]
        res_type = scen["resource_type"]
        srv_cat = scen["service_category"]
        srv_name = scen["service_name"]
        reg = scen["region"]
        sku = scen["sku"]
        base_cost = scen["baseline_daily_cost"]
        anom_cost = scen["anomaly_daily_cost"]
        usage_qty = scen["usage_quantity"]
        owner = scen["owner"]
        env = scen["env"]
        cat = scen["category"]

        # 1. Upsert Stage 5 CloudResource
        existing_res = db.query(CloudResource).filter(
            CloudResource.resource_id == res_id,
            CloudResource.provider == p,
        ).first()

        if not existing_res:
            cloud_res = CloudResource(
                resource_id=res_id,
                provider=p,
                account_id=acc,
                resource_name=res_name,
                service_category=srv_cat,
                service_name=srv_name,
                resource_type=res_type,
                region=reg,
                status="active",
                owner=owner,
                environment=env,
                project=acc,
                cost_center="CC-ENGINEERING",
                tags={"owner": owner, "env": env, "scenario": scen["id"]},
            )
            db.add(cloud_res)
            total_resources += 1

        # 2. Generate daily billing records
        # Trailing baseline window: (reference_date - baseline_days) to (reference_date - 1)
        start_day = reference_date - timedelta(days=baseline_days)

        for day_offset in range(baseline_days):
            current_day = start_day + timedelta(days=day_offset)
            start_dt = datetime.combine(current_day, time.min, tzinfo=timezone.utc)
            end_dt = start_dt + timedelta(days=1)

            # Normal baseline variance (+- 5%)
            cost = base_cost
            if base_cost > Decimal("0.0000"):
                # Deterministic slight variation
                var = Decimal(str((day_offset % 5) - 2)) * Decimal("0.02") * base_cost
                cost = (base_cost + var).quantize(Decimal("0.0001"))

            # Skip creating records if new spend scenario (0 baseline)
            if cost > Decimal("0.0000") or scen["id"] != "SCEN_04_AWS_SAGEMAKER_ENDPOINT_ORPHAN":
                rec_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"SYN-{scen['id']}-BL-{current_day.isoformat()}")
                existing_rec = db.query(BillingRecord).filter(BillingRecord.record_id == rec_uuid).first()
                if not existing_rec:
                    b_rec = BillingRecord(
                        record_id=rec_uuid,
                        provider=p,
                        billing_account_id=acc,
                        subscription_id=acc,
                        service_category=srv_cat,
                        service_name=srv_name,
                        region=reg,
                        resource_id=res_id,
                        resource_name=res_name,
                        usage_start_time=start_dt,
                        usage_end_time=end_dt,
                        unblended_cost=cost,
                        blended_cost=cost,
                        list_cost=cost,
                        usage_quantity=(usage_qty / Decimal("10.0")).quantize(Decimal("0.0001")),
                        usage_unit="Hours",
                        pricing_model="ON_DEMAND",
                        tags={"owner": owner, "env": env, "scenario": scen["id"]},
                    )
                    db.add(b_rec)
                    total_billing_records += 1

        # 3. Generate Anomaly Day Billing Record(s)
        # If persistent step, generate across last 4 days; otherwise on reference_date
        num_anom_days = 4 if cat == "PERSISTENT_STEP" else 1

        for a_idx in range(num_anom_days):
            a_day = reference_date - timedelta(days=(num_anom_days - 1 - a_idx))
            a_start_dt = datetime.combine(a_day, time.min, tzinfo=timezone.utc)
            a_end_dt = a_start_dt + timedelta(days=1)

            anom_rec_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"SYN-{scen['id']}-ANOM-{a_day.isoformat()}")
            existing_anom = db.query(BillingRecord).filter(BillingRecord.record_id == anom_rec_uuid).first()
            if not existing_anom:
                b_rec_anom = BillingRecord(
                    record_id=anom_rec_uuid,
                    provider=p,
                    billing_account_id=acc,
                    subscription_id=acc,
                    service_category=srv_cat,
                    service_name=srv_name,
                    region=reg,
                    resource_id=res_id,
                    resource_name=res_name,
                    usage_start_time=a_start_dt,
                    usage_end_time=a_end_dt,
                    unblended_cost=anom_cost,
                    blended_cost=anom_cost,
                    list_cost=anom_cost,
                    usage_quantity=usage_qty,
                    usage_unit="Hours",
                    pricing_model="ON_DEMAND",
                    tags={"owner": owner, "env": env, "scenario": scen["id"], "is_anomaly": "true"},
                )
                db.add(b_rec_anom)
                total_billing_records += 1

    db.commit()

    return {
        "scenarios_seeded": len(SYNTHETIC_SCENARIO_DEFINITIONS),
        "resources_created": total_resources,
        "billing_records_created": total_billing_records,
        "reference_date": reference_date.isoformat(),
    }
