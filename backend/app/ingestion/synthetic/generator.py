"""
CloudSage Multi-Cloud Synthetic Billing Data Generator.
Generates reproducible, high-fidelity billing feeds for AWS, Azure, and GCP matching native provider formats.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import random
from typing import Any, Dict, List, Tuple
from backend.app.core.enums import CloudProvider


class SyntheticDataGenerator:
    """Generates realistic multi-cloud billing datasets with seeded optimization scenarios."""

    AWS_SERVICES = [
        {"code": "AmazonEC2", "category": "COMPUTE", "units": "Hrs", "rate": Decimal("0.0960"), "types": ["m5.large", "t3.medium", "c5.4xlarge"]},
        {"code": "AmazonS3", "category": "STORAGE", "units": "GB-Mo", "rate": Decimal("0.0230"), "types": ["StandardStorage", "GlacierStorage"]},
        {"code": "AmazonRDS", "category": "DATABASE", "units": "Hrs", "rate": Decimal("0.2400"), "types": ["db.r5.large", "db.t3.medium"]},
        {"code": "AWSLambda", "category": "COMPUTE", "units": "Requests", "rate": Decimal("0.0000002"), "types": ["Invocation"]},
        {"code": "AmazonEBS", "category": "STORAGE", "units": "GB-Mo", "rate": Decimal("0.0800"), "types": ["gp3", "io2"]},
        {"code": "AmazonCloudWatch", "category": "MANAGEMENT", "units": "GB", "rate": Decimal("0.5000"), "types": ["Logs"]},
    ]

    AZURE_SERVICES = [
        {"category": "Virtual Machines", "sub": "D Series", "unit": "Hours", "rate": Decimal("0.1920"), "name": "Virtual Machines"},
        {"category": "Storage", "sub": "Blob Storage", "unit": "GB", "rate": Decimal("0.0184"), "name": "Storage Accounts"},
        {"category": "SQL Database", "sub": "General Purpose", "unit": "vCore-Hours", "rate": Decimal("0.3500"), "name": "Azure SQL"},
        {"category": "Azure Functions", "sub": "Consumption", "unit": "Execution Units", "rate": Decimal("0.000016"), "name": "Azure Functions"},
        {"category": "Networking", "sub": "Virtual Network", "unit": "GB", "rate": Decimal("0.0500"), "name": "Bandwidth"},
    ]

    GCP_SERVICES = [
        {"service": "Compute Engine", "sku": "Instance Core running in Americas", "unit": "hour", "rate": Decimal("0.0380")},
        {"service": "Cloud Storage", "sku": "Standard Storage US Regional", "unit": "gibibyte month", "rate": Decimal("0.0200")},
        {"service": "Cloud SQL", "sku": "Cloud SQL for PostgreSQL", "unit": "hour", "rate": Decimal("0.1500")},
        {"service": "BigQuery", "sku": "Analysis (Queries)", "unit": "tebibyte", "rate": Decimal("5.0000")},
        {"service": "Cloud Functions", "sku": "CPU Allocation Time", "unit": "gigahertz hour", "rate": Decimal("0.00001")},
    ]

    TEAMS = ["checkout-squad", "search-team", "platform-eng", "data-analytics", "security-core"]
    ENVIRONMENTS = ["production", "staging", "dev", "test"]

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_multi_cloud_dataset(
        self,
        total_records: int = 1200,
        start_date: datetime = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
        days: int = 7
    ) -> Dict[CloudProvider, List[Dict[str, Any]]]:
        """
        Generates realistic billing records distributed across AWS, Azure, and GCP.
        Includes seeded scenarios: Idle VMs, Unattached Storage, Oversized Compute, Cost Spikes, and Missing Tags.
        """
        records_per_provider = total_records // 3
        return {
            CloudProvider.AWS: self.generate_aws_records(records_per_provider, start_date, days),
            CloudProvider.AZURE: self.generate_azure_records(records_per_provider, start_date, days),
            CloudProvider.GCP: self.generate_gcp_records(records_per_provider, start_date, days),
        }

    def generate_aws_records(self, count: int, start_date: datetime, days: int) -> List[Dict[str, Any]]:
        """Generates realistic AWS CUR CSV-formatted dictionaries."""
        records = []
        account_id = "112233445566"
        payer_id = "112233445566"

        for idx in range(count):
            day_offset = self.rng.randint(0, days - 1)
            hour_offset = self.rng.randint(0, 23)
            dt_start = start_date + timedelta(days=day_offset, hours=hour_offset)
            dt_end = dt_start + timedelta(hours=1)

            # Check scenarios
            is_idle = (idx % 15 == 0)
            is_unattached = (idx % 20 == 0 and not is_idle)
            is_oversized = (idx % 25 == 0 and not is_idle and not is_unattached)
            is_spike = (idx == 42)
            has_no_tags = (idx % 7 == 0 and not is_spike)

            if is_spike:
                svc = [s for s in self.AWS_SERVICES if s["code"] == "AmazonCloudWatch"][0]
            elif is_unattached:
                svc = [s for s in self.AWS_SERVICES if s["code"] == "AmazonEBS"][0]
            elif is_idle or is_oversized:
                svc = [s for s in self.AWS_SERVICES if s["code"] == "AmazonEC2"][0]
            else:
                svc = self.rng.choice(self.AWS_SERVICES)

            qty = Decimal(str(round(self.rng.uniform(1.0, 100.0), 2)))
            cost = (qty * svc["rate"]).quantize(Decimal("0.0001"))

            res_name = f"aws-{svc['code'].lower()}-{idx:04d}"
            if is_idle:
                res_name = f"idle-dev-instance-{idx:04d}"
                cost = Decimal("0.8500")
            elif is_unattached:
                res_name = f"vol-unattached-{idx:04d}"
                cost = Decimal("1.2000")
            elif is_oversized:
                res_name = f"oversized-c5-4xlarge-{idx:04d}"
                cost = Decimal("8.4500")
            elif is_spike:
                res_name = f"runaway-log-ingestion-{idx:04d}"
                cost = Decimal("485.5000")

            resource_id = f"arn:aws:{svc['code'].lower()}:us-east-1:{account_id}:{res_name}"

            tags = {}
            if not has_no_tags:
                tags = {
                    "resourceTags/user:Owner": self.rng.choice(self.TEAMS),
                    "resourceTags/user:Environment": "dev" if is_idle else self.rng.choice(self.ENVIRONMENTS),
                    "resourceTags/user:CostCenter": f"CC-{self.rng.randint(100, 199)}",
                    "resourceTags/user:Name": res_name,
                }

            rec = {
                "identity/LineItemId": f"aws-line-{idx:05d}",
                "bill/PayerAccountId": payer_id,
                "lineItem/UsageAccountId": account_id,
                "lineItem/LineItemType": "Spot" if idx % 10 == 0 else "Usage",
                "lineItem/UsageStartDate": dt_start.isoformat(),
                "lineItem/UsageEndDate": dt_end.isoformat(),
                "lineItem/ProductCode": svc["code"],
                "lineItem/UsageAmount": str(qty),
                "pricing/unit": svc["units"],
                "lineItem/UnblendedCost": str(cost),
                "lineItem/CurrencyCode": "USD",
                "lineItem/ResourceId": resource_id,
                "product/region": "us-east-1",
                "lineItem/AvailabilityZone": "us-east-1a",
                **tags
            }
            records.append(rec)
        return records

    def generate_azure_records(self, count: int, start_date: datetime, days: int) -> List[Dict[str, Any]]:
        """Generates realistic Azure Cost Management export CSV-formatted dictionaries."""
        records = []
        sub_id = "00000000-0000-0000-0000-111122223333"
        rg_name = "rg-enterprise-core"

        for idx in range(count):
            day_offset = self.rng.randint(0, days - 1)
            dt_start = start_date + timedelta(days=day_offset)

            is_idle = (idx % 12 == 0)
            is_unattached = (idx % 18 == 0 and not is_idle)

            if is_idle:
                svc = [s for s in self.AZURE_SERVICES if s["category"] == "Virtual Machines"][0]
            elif is_unattached:
                svc = [s for s in self.AZURE_SERVICES if s["category"] == "Storage"][0]
            else:
                svc = self.rng.choice(self.AZURE_SERVICES)

            qty = Decimal(str(round(self.rng.uniform(1.0, 50.0), 2)))
            cost = (qty * svc["rate"]).quantize(Decimal("0.0001"))

            res_name = f"azure-res-{idx:04d}"
            if is_idle:
                res_name = f"idle-azure-b2s-{idx:04d}"
                cost = Decimal("1.1000")
            elif is_unattached:
                res_name = f"disk-unattached-{idx:04d}"
                cost = Decimal("3.4000")

            resource_id = f"/subscriptions/{sub_id}/resourceGroups/{rg_name}/providers/Microsoft.Compute/{res_name}"

            tags_dict = {
                "owner": self.rng.choice(self.TEAMS),
                "environment": "staging" if is_idle else self.rng.choice(self.ENVIRONMENTS),
                "department": "Infrastructure",
            }
            if idx % 8 == 0:
                tags_dict = {}  # poorly tagged scenario

            rec = {
                "BillingAccountId": "EA-998877",
                "SubscriptionId": sub_id,
                "ResourceGroup": rg_name,
                "ResourceId": resource_id,
                "ResourceName": res_name,
                "MeterCategory": svc["category"],
                "MeterSubCategory": svc["sub"],
                "ConsumedService": svc["name"],
                "Date": dt_start.strftime("%Y-%m-%d"),
                "Quantity": str(qty),
                "UnitOfMeasure": svc["unit"],
                "CostInBillingCurrency": str(cost),
                "BillingCurrency": "USD",
                "ResourceLocation": "eastus",
                "PricingModel": "Reservation" if idx % 9 == 0 else "OnDemand",
                "Tags": tags_dict,
            }
            records.append(rec)
        return records

    def generate_gcp_records(self, count: int, start_date: datetime, days: int) -> List[Dict[str, Any]]:
        """Generates realistic GCP BigQuery billing export JSON-formatted dictionaries."""
        records = []
        billing_acc = "01ABCD-23EFGH-45IJKL"
        project_id = "gcp-prod-analytics-88"

        for idx in range(count):
            day_offset = self.rng.randint(0, days - 1)
            hour_offset = self.rng.randint(0, 23)
            dt_start = start_date + timedelta(days=day_offset, hours=hour_offset)
            dt_end = dt_start + timedelta(hours=1)

            is_idle = (idx % 14 == 0)
            is_unattached = (idx % 22 == 0 and not is_idle)
            is_spike = (idx == 77)

            if is_spike:
                svc = [s for s in self.GCP_SERVICES if s["service"] == "BigQuery"][0]
            elif is_idle:
                svc = [s for s in self.GCP_SERVICES if s["service"] == "Compute Engine"][0]
            elif is_unattached:
                svc = [s for s in self.GCP_SERVICES if s["service"] == "Cloud Storage"][0]
            else:
                svc = self.rng.choice(self.GCP_SERVICES)

            qty = Decimal(str(round(self.rng.uniform(1.0, 80.0), 2)))
            cost = (qty * svc["rate"]).quantize(Decimal("0.0001"))

            res_name = f"gcp-asset-{idx:04d}"
            if is_idle:
                res_name = f"idle-n1-standard-1-{idx:04d}"
                cost = Decimal("0.7500")
            elif is_unattached:
                res_name = f"orphaned-pd-ssd-{idx:04d}"
                cost = Decimal("2.8000")
            elif is_spike:
                res_name = f"unpartitioned-query-scan-{idx:04d}"
                cost = Decimal("620.0000")

            resource_uri = f"//compute.googleapis.com/projects/{project_id}/zones/us-central1-a/instances/{res_name}"

            labels = [
                {"key": "owner", "value": self.rng.choice(self.TEAMS)},
                {"key": "environment", "value": "test" if is_idle else self.rng.choice(self.ENVIRONMENTS)},
                {"key": "project", "value": project_id},
            ]
            if idx % 9 == 0:
                labels = []

            credits = []
            if idx % 6 == 0:
                credits.append({"name": "Sustained Usage Discount", "amount": -float(cost * Decimal("0.20"))})

            rec = {
                "billing_account_id": billing_acc,
                "project": {"id": project_id, "name": "Production Analytics", "number": "987654321"},
                "service": {"id": f"SRV-{idx:03d}", "description": svc["service"]},
                "sku": {"id": f"SKU-{idx:04d}", "description": svc["sku"]},
                "usage_start_time": dt_start.isoformat(),
                "usage_end_time": dt_end.isoformat(),
                "cost": float(cost),
                "currency": "USD",
                "usage": {"amount": float(qty), "unit": svc["unit"], "pricing_unit": svc["unit"]},
                "location": {"location": "us-central1", "region": "us-central1", "zone": "us-central1-a"},
                "resource": {"name": resource_uri, "global_name": resource_uri},
                "labels": labels,
                "credits": credits,
            }
            records.append(rec)
        return records
