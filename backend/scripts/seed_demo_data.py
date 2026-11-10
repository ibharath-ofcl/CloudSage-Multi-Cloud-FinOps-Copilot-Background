#!/usr/bin/env python3
"""
Seeds the local database with realistic multi-cloud FinOps records across AWS, Azure, and GCP.
Populates discovered resources, historical daily billing line items, cost anomalies,
waste detection findings, and advisory recommendations.
"""

import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import backend.app.models
from backend.app.core.database import Base
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.billing import BillingRecord
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource
from backend.app.models.waste import WasteDetection

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../cloudsage.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"


def seed():
    print(f"Connecting to {DATABASE_URL}...")
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Clear existing data in reverse dependency order
    session.query(Recommendation).delete()
    session.query(WasteDetection).delete()
    session.query(CostAnomaly).delete()
    session.query(BillingRecord).delete()
    session.query(CloudResource).delete()
    session.commit()

    now = datetime.now(timezone.utc)
    today = now.date()

    print("Generating Discovered Cloud Resources...")
    resources = [
        # AWS
        CloudResource(
            resource_id="arn:aws:ec2:us-east-1:123456789012:instance/i-0a1b2c3d4e5f6g7h8",
            provider="AWS",
            account_id="123456789012",
            service_name="Amazon Elastic Compute Cloud",
            service_category="COMPUTE",
            resource_type="ec2:instance",
            region="us-east-1",
            status="running",
            owner="DevOps",
            environment="production",
            tags={"environment": "production", "owner": "DevOps", "cost_center": "CC-101", "service": "payment-api"},
        ),
        CloudResource(
            resource_id="arn:aws:ec2:us-east-1:123456789012:volume/vol-0987654321fedcba0",
            provider="AWS",
            account_id="123456789012",
            service_name="Amazon Elastic Block Store",
            service_category="STORAGE",
            resource_type="ebs:volume",
            region="us-east-1",
            status="available",
            owner="DevOps",
            environment="staging",
            tags={"environment": "staging", "owner": "DevOps", "cost_center": "CC-101"},
        ),
        CloudResource(
            resource_id="arn:aws:rds:us-east-1:123456789012:db:prod-pg-cluster",
            provider="AWS",
            account_id="123456789012",
            service_name="Amazon Relational Database Service",
            service_category="DATABASE",
            resource_type="rds:db",
            region="us-east-1",
            status="available",
            owner="DataPlatform",
            environment="production",
            tags={"environment": "production", "owner": "DataPlatform", "cost_center": "CC-201"},
        ),
        # Azure
        CloudResource(
            resource_id="/subscriptions/sub-azure-enterprise-01/resourceGroups/rg-core/providers/Microsoft.Compute/virtualMachines/vm-checkout-worker",
            provider="AZURE",
            account_id="sub-azure-enterprise-01",
            service_name="Virtual Machines",
            service_category="COMPUTE",
            resource_type="compute:vm",
            region="eastus",
            status="running",
            owner="ECommerceTeam",
            environment="production",
            tags={"environment": "production", "owner": "ECommerceTeam", "cost_center": "CC-301"},
        ),
        CloudResource(
            resource_id="/subscriptions/sub-azure-enterprise-01/resourceGroups/rg-data/providers/Microsoft.Sql/servers/sql-analytics/databases/dw-core",
            provider="AZURE",
            account_id="sub-azure-enterprise-01",
            service_name="Azure SQL Database",
            service_category="DATABASE",
            resource_type="sql:database",
            region="eastus",
            status="online",
            owner="Analytics",
            environment="production",
            tags={"environment": "production", "owner": "Analytics", "cost_center": "CC-302"},
        ),
        # GCP
        CloudResource(
            resource_id="//compute.googleapis.com/projects/finops-ai-prod/zones/us-central1-a/instances/gcp-ml-inference-01",
            provider="GCP",
            account_id="finops-ai-prod",
            service_name="Compute Engine",
            service_category="COMPUTE",
            resource_type="compute:instance",
            region="us-central1",
            status="RUNNING",
            owner="MLEngineering",
            environment="production",
            tags={"environment": "production", "owner": "MLEngineering", "cost_center": "CC-401"},
        ),
        CloudResource(
            resource_id="//storage.googleapis.com/finops-ai-prod-archive-backups",
            provider="GCP",
            account_id="finops-ai-prod",
            service_name="Cloud Storage",
            service_category="STORAGE",
            resource_type="storage:bucket",
            region="us-central1",
            status="ACTIVE",
            owner="DataPlatform",
            environment="production",
            tags={"environment": "production", "owner": "DataPlatform", "cost_center": "CC-201"},
        ),
    ]
    session.add_all(resources)
    session.flush()

    print("Generating Historical 30-Day Billing Records...")
    billing_records = []
    rng = random.Random(42)

    for days_ago in range(30, -1, -1):
        day_date = now - timedelta(days=days_ago)
        
        # AWS Daily Compute & Storage
        aws_cost = Decimal(str(round(rng.uniform(140.0, 195.0), 4)))
        billing_records.append(
            BillingRecord(
                record_id=uuid.uuid4(),
                provider="AWS",
                billing_account_id="123456789012",
                subscription_id="123456789012",
                resource_id=resources[0].resource_id,
                service_category="COMPUTE",
                service_name="Amazon Elastic Compute Cloud",
                region="us-east-1",
                usage_start_time=day_date.replace(hour=0, minute=0, second=0),
                usage_end_time=day_date.replace(hour=23, minute=59, second=59),
                usage_quantity=Decimal("24.0"),
                usage_unit="HOURS",
                unblended_cost=aws_cost,
                currency="USD",
                tags={"environment": "production", "owner": "DevOps", "cost_center": "CC-101"},
            )
        )

        # Azure Daily VM & SQL
        azure_cost = Decimal(str(round(rng.uniform(95.0, 140.0), 4)))
        billing_records.append(
            BillingRecord(
                record_id=uuid.uuid4(),
                provider="AZURE",
                billing_account_id="sub-azure-enterprise-01",
                subscription_id="sub-azure-enterprise-01",
                resource_id=resources[3].resource_id,
                service_category="COMPUTE",
                service_name="Virtual Machines",
                region="eastus",
                usage_start_time=day_date.replace(hour=0, minute=0, second=0),
                usage_end_time=day_date.replace(hour=23, minute=59, second=59),
                usage_quantity=Decimal("24.0"),
                usage_unit="HOURS",
                unblended_cost=azure_cost,
                currency="USD",
                tags={"environment": "production", "owner": "ECommerceTeam", "cost_center": "CC-301"},
            )
        )

        # GCP Daily Compute & Storage
        gcp_cost = Decimal(str(round(rng.uniform(65.0, 110.0), 4)))
        billing_records.append(
            BillingRecord(
                record_id=uuid.uuid4(),
                provider="GCP",
                billing_account_id="finops-ai-prod",
                subscription_id="finops-ai-prod",
                resource_id=resources[5].resource_id,
                service_category="COMPUTE",
                service_name="Compute Engine",
                region="us-central1",
                usage_start_time=day_date.replace(hour=0, minute=0, second=0),
                usage_end_time=day_date.replace(hour=23, minute=59, second=59),
                usage_quantity=Decimal("24.0"),
                usage_unit="HOURS",
                unblended_cost=gcp_cost,
                currency="USD",
                tags={"environment": "production", "owner": "MLEngineering", "cost_center": "CC-401"},
            )
        )

    session.add_all(billing_records)

    print("Generating Multi-Cloud Waste Detections...")
    waste_items = [
        WasteDetection(
            resource_id=resources[0].resource_id,
            provider="AWS",
            account_id="123456789012",
            waste_type="IDLE_VM",
            finding_title="Idle Compute Instance (c5.4xlarge)",
            explanation="Average 14-day CPU utilization under 1.2% with 0 active network connections.",
            severity="HIGH",
            status="ACTIVE",
            estimated_monthly_waste=Decimal("284.5000"),
        ),
        WasteDetection(
            resource_id=resources[1].resource_id,
            provider="AWS",
            account_id="123456789012",
            waste_type="UNATTACHED_DISK",
            finding_title="Unattached High-IOPS EBS Volume",
            explanation="Volume vol-0987654321fedcba0 has been unattached from any instance for 28 days.",
            severity="MEDIUM",
            status="ACTIVE",
            estimated_monthly_waste=Decimal("120.0000"),
        ),
        WasteDetection(
            resource_id=resources[3].resource_id,
            provider="AZURE",
            account_id="sub-azure-enterprise-01",
            waste_type="OVERSIZED_VM",
            finding_title="Oversized Standard_D16s_v4 Virtual Machine",
            explanation="Peak memory utilization never exceeded 18% during peak business hours.",
            severity="HIGH",
            status="ACTIVE",
            estimated_monthly_waste=Decimal("345.8000"),
        ),
    ]
    session.add_all(waste_items)

    print("Generating Cost Anomalies...")
    anomalies = [
        CostAnomaly(
            provider="AWS",
            account_id="123456789012",
            service_category="STORAGE",
            service_name="Amazon S3",
            region="us-east-1",
            anomaly_category="SERVICE_SPIKE",
            title="S3 Egress Transfer Surge",
            explanation="Unexpected cross-region data transfer spike exceeding historical baseline by 320%.",
            anomaly_date=today - timedelta(days=2),
            actual_cost=Decimal("450.0000"),
            expected_cost=Decimal("95.0000"),
            estimated_excess_cost=Decimal("355.0000"),
            severity="CRITICAL",
            status="OPEN",
            z_score=Decimal("4.8500"),
        ),
        CostAnomaly(
            provider="AZURE",
            account_id="sub-azure-enterprise-01",
            service_category="DATABASE",
            service_name="Azure SQL Database",
            region="eastus",
            anomaly_category="SKU_INCREASE",
            title="Unplanned SQL vCore Tier Upgrade",
            explanation="Database upgraded from 4 vCores to 16 vCores without tagging attribution.",
            anomaly_date=today - timedelta(days=5),
            actual_cost=Decimal("280.0000"),
            expected_cost=Decimal("85.0000"),
            estimated_excess_cost=Decimal("195.0000"),
            severity="HIGH",
            status="OPEN",
            z_score=Decimal("3.4200"),
        ),
    ]
    session.add_all(anomalies)

    print("Generating FinOps Optimization Recommendations...")
    recommendations = [
        Recommendation(
            resource_id=resources[0].resource_id,
            provider="AWS",
            account_id="123456789012",
            region="us-east-1",
            service_name="Amazon Elastic Compute Cloud",
            action_type="RIGHTSIZE",
            priority="P1",
            risk_level="LOW",
            status="PROPOSED",
            title="Rightsize Idle c5.4xlarge to c5.xlarge",
            description="Downsizing saves 75% compute expenditure without impacting throughput.",
            estimated_monthly_savings=Decimal("213.3750"),
            estimated_annual_savings=Decimal("2560.5000"),
            remediation_guide="aws ec2 modify-instance-attribute --instance-id i-0a1b2c3d4e5f6g7h8 --instance-type c5.xlarge",
        ),
        Recommendation(
            resource_id=resources[1].resource_id,
            provider="AWS",
            account_id="123456789012",
            region="us-east-1",
            service_name="Amazon Elastic Block Store",
            action_type="TERMINATE",
            priority="P2",
            risk_level="NONE",
            status="PROPOSED",
            title="Snapshot and Delete Unattached EBS Volume",
            description="Create backup snapshot and terminate abandoned volume vol-0987654321fedcba0.",
            estimated_monthly_savings=Decimal("120.0000"),
            estimated_annual_savings=Decimal("1440.0000"),
            remediation_guide="aws ec2 create-snapshot --volume-id vol-0987654321fedcba0 && aws ec2 delete-volume --volume-id vol-0987654321fedcba0",
        ),
        Recommendation(
            resource_id=resources[3].resource_id,
            provider="AZURE",
            account_id="sub-azure-enterprise-01",
            region="eastus",
            service_name="Virtual Machines",
            action_type="RIGHTSIZE",
            priority="P1",
            risk_level="LOW",
            status="PROPOSED",
            title="Downsize Oversized Azure VM to Standard_D4s_v4",
            description="Reduces monthly compute spend by 50% while preserving required RAM headroom.",
            estimated_monthly_savings=Decimal("172.9000"),
            estimated_annual_savings=Decimal("2074.8000"),
            remediation_guide="az vm resize --resource-group rg-core --name vm-checkout-worker --size Standard_D4s_v4",
        ),
    ]
    session.add_all(recommendations)

    session.commit()
    print("Database seeding completed successfully!")
    print(f"Summary in {DB_PATH}:")
    print(f"  - Cloud Resources: {len(resources)}")
    print(f"  - 30-Day Daily Billing Records: {len(billing_records)}")
    print(f"  - Waste Detections: {len(waste_items)}")
    print(f"  - Cost Anomalies: {len(anomalies)}")
    print(f"  - Optimization Recommendations: {len(recommendations)}")


if __name__ == "__main__":
    seed()

