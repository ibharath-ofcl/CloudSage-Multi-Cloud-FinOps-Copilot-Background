# Synthetic Multi-Cloud Anomaly Scenarios Catalog

## 1. Overview

To validate the Cost Anomaly Detection Engine against real-world FinOps challenges, CloudSage includes a comprehensive generator of **20 enterprise synthetic anomaly scenarios** (`backend/app/anomaly_detection/synthetic.py`).

Each scenario models 14 to 30 days of baseline empirical behavior, authentic cloud resources in Stage 5 `CloudResource` inventory, and specific cost spike or structural shift anomalies across AWS, Microsoft Azure, and Google Cloud Platform.

---

## 2. Complete Scenario Catalog

| ID | Scenario Name | Provider | Service | Anomaly Pattern | Baseline / Anomaly Spend |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **01** | AWS EC2 Auto-Scaling Loop Surge | **AWS** | `AmazonEC2` | `SERVICE_SPIKE` | $\$150.00 \to \$1,450.00$ / day |
| **02** | AWS DynamoDB Provisioned Capacity Spike | **AWS** | `AmazonDynamoDB` | `RESOURCE_SPIKE` | $\$45.00 \to \$680.00$ / day |
| **03** | AWS S3 Cross-Region Data Transfer Surge | **AWS** | `AmazonS3` | `SERVICE_SPIKE` | $\$20.00 \to \$520.00$ / day |
| **04** | AWS SageMaker Forgotten GPU Endpoint | **AWS** | `AmazonSageMaker` | `NEW_SPEND` | $\$0.00 \to \$580.00$ / day |
| **05** | AWS NAT Gateway Processing Surge | **AWS** | `AmazonVPC` | `SERVICE_SPIKE` | $\$35.00 \to \$620.00$ / day |
| **06** | AWS RDS Overprovisioned Read Replicas | **AWS** | `AmazonRDS` | `RESOURCE_SPIKE` | $\$180.00 \to \$890.00$ / day |
| **07** | Azure Batch Worker Pool Runaway | **AZURE** | `Virtual Machines` | `RESOURCE_SPIKE` | $\$60.00 \to \$750.00$ / day |
| **08** | Azure SQL Elastic Pool Scale-Up | **AZURE** | `SQL Database` | `SERVICE_SPIKE` | $\$110.00 \to \$980.00$ / day |
| **09** | Azure Cosmos DB Provisioned RU/s Surge | **AZURE** | `Azure Cosmos DB` | `RESOURCE_SPIKE` | $\$40.00 \to \$600.00$ / day |
| **10** | Azure App Service Max Workers Surge | **AZURE** | `Azure App Service` | `SERVICE_SPIKE` | $\$75.00 \to \$690.00$ / day |
| **11** | Azure Blob Archive to Hot Tier Surge | **AZURE** | `Storage Accounts` | `RESOURCE_SPIKE` | $\$25.00 \to \$550.00$ / day |
| **12** | Azure Inter-Region Egress Surge | **AZURE** | `Bandwidth` | `SERVICE_SPIKE` | $\$15.00 \to \$480.00$ / day |
| **13** | GCP Compute Engine A100 GPU Cluster | **GCP** | `Compute Engine` | `RESOURCE_SPIKE` | $\$50.00 \to \$1,650.00$ / day |
| **14** | GCP BigQuery Unpartitioned Analysis Loop | **GCP** | `BigQuery` | `SERVICE_SPIKE` | $\$80.00 \to \$1,250.00$ / day |
| **15** | GCP Cloud Spanner Node Expansion | **GCP** | `Cloud Spanner` | `RESOURCE_SPIKE` | $\$72.00 \to \$720.00$ / day |
| **16** | GCP Cloud Storage Public Egress Surge | **GCP** | `Cloud Storage` | `SERVICE_SPIKE` | $\$30.00 \to \$590.00$ / day |
| **17** | GCP GKE Cluster Autoscaler Surge | **GCP** | `Google Kubernetes Engine` | `SERVICE_SPIKE` | $\$140.00 \to \$1,100.00$ / day |
| **18** | AWS CloudWatch Debug Logs Surge | **AWS** | `AmazonCloudWatch` | `SERVICE_SPIKE` | $\$25.00 \to \$490.00$ / day |
| **19** | AWS Dedicated Host Rate Shift | **AWS** | `AmazonEC2` | `SKU_PRICE_CHANGE` | $\$100.00 \to \$250.00$ / day |
| **20** | Azure Microservices v2.0 Permanent Step Shift | **AZURE** | `Azure Container Apps` | `PERSISTENT_STEP` | $\$85.00 \to \$480.00$ / day |

---

## 3. Seeding Protocol

To seed these scenarios into the development or testing database:

```python
from backend.app.core.database import SyncSessionLocal
from backend.app.anomaly_detection.synthetic import seed_synthetic_anomalies

session = SyncSessionLocal()
result = seed_synthetic_anomalies(db=session, baseline_days=21)
print(f"Seeded {result['scenarios_seeded']} scenarios with {result['billing_records_created']} records.")
```

