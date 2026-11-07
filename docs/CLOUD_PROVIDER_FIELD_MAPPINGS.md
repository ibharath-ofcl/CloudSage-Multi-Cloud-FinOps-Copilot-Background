# Cloud Provider Field Mappings & Normalization Taxonomy

This document details the exact field-level mapping rules from Amazon Web Services (AWS CUR), Microsoft Azure Cost Management, and Google Cloud Platform (GCP BigQuery Export) into CloudSage's canonical billing schema and FOCUS 1.0 specification.

---

## 1. Canonical Schema Reference (`BillingRecord`)

All provider reports are mapped to the canonical `BillingRecord` entity:

| Canonical Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `id` | `UUID` | Yes | Unique database primary key |
| `cloud_provider` | `VARCHAR(32)` | Yes | Normalized provider (`AWS`, `AZURE`, `GCP`) |
| `account_id` | `VARCHAR(128)` | Yes | Provider account ID / Subscription ID / Project ID |
| `account_name` | `VARCHAR(255)` | No | Human-readable account or project display name |
| `service_name` | `VARCHAR(128)` | Yes | Standardized provider service name |
| `service_category` | `VARCHAR(64)` | Yes | Normalized category (`COMPUTE`, `STORAGE`, `DATABASE`, etc.) |
| `resource_id` | `VARCHAR(512)` | No | Native cloud resource identifier or ARN |
| `resource_name` | `VARCHAR(255)` | No | Logical name or parsed resource identifier |
| `region` | `VARCHAR(64)` | No | Geographic region (e.g., `us-east-1`, `eastus`) |
| `availability_zone`| `VARCHAR(64)` | No | Availability zone or sub-region zone |
| `usage_start_time` | `TIMESTAMP WITH TZ` | Yes | Start of billing interval (UTC) |
| `usage_end_time` | `TIMESTAMP WITH TZ` | Yes | End of billing interval (UTC) |
| `usage_amount` | `NUMERIC(18, 4)` | No | Raw quantity of consumed units |
| `usage_unit` | `VARCHAR(64)` | No | Billing unit of measurement (Hours, GB-Mo, etc.) |
| `cost_amount` | `NUMERIC(18, 4)` | Yes | Effective or unblended cost in original currency |
| `currency` | `VARCHAR(3)` | Yes | ISO 4217 currency code (e.g., `USD`, `EUR`) |
| `cost_in_usd` | `NUMERIC(18, 4)` | Yes | Normalized expenditure in US Dollars |
| `pricing_model` | `VARCHAR(32)` | Yes | `ON_DEMAND`, `RESERVED`, `SAVINGS_PLAN`, `SPOT` |
| `tags` | `JSONB` | Yes | Key-value dictionary of resource metadata tags |
| `environment` | `VARCHAR(32)` | No | Extracted environment (`production`, `development`) |
| `owner` | `VARCHAR(128)` | No | Extracted owner identity or email address |
| `fingerprint` | `VARCHAR(64)` | Yes | SHA-256 idempotency fingerprint |
| `raw_data` | `JSONB` | No | Original provider line item payload |

---

## 2. AWS Cost and Usage Report (CUR) Mappings

AWS CUR exports support legacy column names and modern CUR 2.0 export naming conventions.

| Canonical Field | Primary AWS CUR Column | Fallback / Variant Column | Transformation Rule |
| :--- | :--- | :--- | :--- |
| `cloud_provider` | Constant `"AWS"` | - | Constant value |
| `account_id` | `lineItem/UsageAccountId` | `bill/PayerAccountId` | Stripped of whitespace |
| `account_name` | `lineItem/UsageAccountName`| `bill/BillingEntity` | Default to `AWS Account <id>` |
| `service_name` | `lineItem/ProductCode` | `product/ProductName` | Provider service code |
| `service_category` | Derived from `ProductCode` | `product/servicecode` | Normalized via Service Taxonomy |
| `resource_id` | `lineItem/ResourceId` | Extracted from ARN | Optional; empty string stored as `None` |
| `resource_name` | Derived from `ResourceId` | Tag `resourceTags/user:Name` | Resource identifier or tag name |
| `region` | `product/region` | `lineItem/AvailabilityZone` | Region code (e.g. `us-east-1`) |
| `availability_zone`| `lineItem/AvailabilityZone`| - | AZ string (e.g. `us-east-1a`) |
| `usage_start_time` | `lineItem/UsageStartDate` | - | Parsed ISO 8601 UTC timestamp |
| `usage_end_time` | `lineItem/UsageEndDate` | - | Parsed ISO 8601 UTC timestamp |
| `usage_amount` | `lineItem/UsageAmount` | `pricing/publicOnDemandRate`| Converted to `Decimal(18, 4)` |
| `usage_unit` | `pricing/unit` | `lineItem/Unit` | String representation |
| `cost_amount` | `lineItem/UnblendedCost` | `lineItem/NetUnblendedCost` | Converted to `Decimal(18, 4)` |
| `currency` | `pricing/currency` | `lineItem/CurrencyCode` | Upper-case ISO 4217 code (default `USD`) |
| `pricing_model` | `pricing/term` | `lineItem/LineItemType` | Mapped to standardized enum |
| `tags` | Prefix `resourceTags/user:`| Prefix `resourceTags/aws:` | Extracted into clean JSON dictionary |

### AWS Edge Cases & Rules
- **Missing Resource IDs**: CloudWatch, Data Transfer, and S3 API calls frequently lack a `lineItem/ResourceId`. The adapter handles missing resource IDs safely without skipping records.
- **Tag Prefix Stripping**: AWS prepends `resourceTags/user:` or `resourceTags/aws:`. The adapter strips these prefixes to store clean key names (e.g., `resourceTags/user:Environment` $\to$ `environment`).
- **Tag Casing**: Tags are normalized to case-insensitive matching for `Owner`, `Environment`, `CostCenter`, and `Project`.

---

## 3. Microsoft Azure Cost Management Mappings

Azure exports vary between Enterprise Agreements (EA), Microsoft Customer Agreements (MCA), and Pay-As-You-Go subscriptions.

| Canonical Field | Primary Azure Column | Fallback / Variant Column | Transformation Rule |
| :--- | :--- | :--- | :--- |
| `cloud_provider` | Constant `"AZURE"` | - | Constant value |
| `account_id` | `subscriptionId` | `subscriptionGuid`, `SubscriptionId` | Azure subscription GUID |
| `account_name` | `subscriptionName` | `SubscriptionName` | Clean display name |
| `service_name` | `MeterCategory` | `ConsumedService`, `serviceName` | Standardized service name |
| `service_category` | Derived from `MeterCategory`| `serviceFamily` | Normalized via Service Taxonomy |
| `resource_id` | `ResourceId` | `resourceId`, `InstanceId` | Fully qualified Azure ARM URI |
| `resource_name` | Derived from `ResourceId` | Tag `Name` | Resource name extracted from ARM path |
| `region` | `ResourceLocation` | `Location`, `resourceLocation` | Azure region (e.g. `eastus`) |
| `availability_zone`| `Zone` | - | Sub-zone if present |
| `usage_start_time` | `Date` | `UsageDateTime`, `usageStartDate` | Parsed ISO 8601 UTC timestamp |
| `usage_end_time` | `Date` | `UsageDateTime` (+ 1 day) | Parsed UTC timestamp |
| `usage_amount` | `UsageQuantity` | `quantity` | Converted to `Decimal(18, 4)` |
| `usage_unit` | `UnitOfMeasure` | `unitOfMeasure` | Standardized unit string |
| `cost_amount` | `CostInBillingCurrency`| `PreTaxCost`, `Cost` | Converted to `Decimal(18, 4)` |
| `currency` | `BillingCurrency` | `Currency`, `currency` | Upper-case ISO 4217 code |
| `pricing_model` | `PricingModel` | `ChargeType` | Mapped to standardized enum |
| `tags` | `Tags` | `tags` | Parsed JSON or semicolon-delimited string |

### Azure Edge Cases & Rules
- **Tags Format**: Azure outputs tags in two distinct formats:
  1. Serialized JSON string: `{"env": "prod", "owner": "finops"}`
  2. Semicolon-delimited key-value string: `"env: prod; owner: finops"`
  The adapter detects both formats and parses them into a uniform JSON dictionary.
- **Resource ID Parsing**: Full ARM Resource IDs (`/subscriptions/.../resourceGroups/.../providers/.../virtualMachines/myVM`) are parsed to isolate the logical resource name (`myVM`).
- **Date vs. Timestamp**: When Azure reports single dates without timestamps (e.g., `2026-11-01`), `usage_start_time` is set to `00:00:00 UTC` and `usage_end_time` is set to `23:59:59 UTC`.

---

## 4. Google Cloud Platform (GCP) BigQuery Export Mappings

GCP exports nested JSON structures or flattened CSV tables from BigQuery.

| Canonical Field | Primary GCP Field (JSON/BigQuery) | GCP CSV Column | Transformation Rule |
| :--- | :--- | :--- | :--- |
| `cloud_provider` | Constant `"GCP"` | Constant `"GCP"` | Constant value |
| `account_id` | `project.id` | `project_id` | GCP Project ID |
| `account_name` | `project.name` | `project_name` | GCP Project Name |
| `service_name` | `service.description` | `service_description` | GCP Service Name |
| `service_category` | Derived from `service.description` | Derived | Normalized via Service Taxonomy |
| `resource_id` | Extracted from `labels` / `system_labels` | `resource_name` | Full resource URI or label identifier |
| `resource_name` | Extracted from `resource_id` | `resource_name` | Logical resource name |
| `region` | `location.region` | `region` | Region string (e.g. `us-central1`) |
| `availability_zone`| `location.zone` | `zone` | Zone string (e.g. `us-central1-a`) |
| `usage_start_time` | `usage_start_time` | `usage_start_time` | Parsed ISO 8601 UTC timestamp |
| `usage_end_time` | `usage_end_time` | `usage_end_time` | Parsed ISO 8601 UTC timestamp |
| `usage_amount` | `usage.amount` | `usage_amount` | Converted to `Decimal(18, 4)` |
| `usage_unit` | `usage.unit` | `usage_unit` | Standardized unit string |
| `cost_amount` | Calculated net: `cost + SUM(credits)`| `cost` | Converted to `Decimal(18, 4)` |
| `currency` | `currency` | `currency` | Upper-case ISO 4217 code |
| `pricing_model` | Derived from `sku.description` / credits | `pricing_model` | Mapped to standardized enum |
| `tags` | Array of `{key, value}` in `labels` | `labels` | Normalized into `{k: v}` JSON object |

### GCP Edge Cases & Rules
- **Credit Deductions**: GCP emits separate negative line items or nested credit arrays (`credits: [{amount: -12.50, type: "COMMITTED_USAGE_DISCOUNT"}]`). The adapter nets out promotional and sustained-use credits against the gross cost.
- **Labels Array Representation**: BigQuery exports labels as lists of key-value objects:
  `[{"key": "env", "value": "production"}, {"key": "team", "value": "data"}]`
  The adapter flattens this array into a clean JSON dictionary: `{"env": "production", "team": "data"}`.
- **Resource Information**: In standard GCP billing, resources may not be logged unless detailed export is enabled. When absent, the adapter synthesizes a stable identifier based on `project.id` and `service.id`.

---

## 5. Service Category Normalization Taxonomy

CloudSage classifies all provider services into 9 canonical categories:

| Canonical Category | AWS Examples | Azure Examples | GCP Examples |
| :--- | :--- | :--- | :--- |
| `COMPUTE` | Amazon EC2, AWS Lambda, ECS, EKS, Fargate, Batch | Virtual Machines, Container Instances, AKS, App Service | Compute Engine, Cloud Run, GKE, Cloud Functions |
| `STORAGE` | Amazon S3, Amazon EBS, Amazon EFS, Glacier | Azure Blob Storage, Azure Files, Managed Disks, Archive | Cloud Storage, Persistent Disk, Filestore |
| `DATABASE` | Amazon RDS, DynamoDB, Aurora, ElastiCache, Redshift | Azure SQL, Cosmos DB, Azure Database for PostgreSQL | Cloud SQL, Cloud Spanner, Bigtable, Firestore |
| `NETWORKING` | Amazon VPC, CloudFront, Route 53, NAT Gateway, Direct Connect | Virtual Network, Azure DNS, Application Gateway, VPN | Cloud Load Balancing, Cloud CDN, Cloud DNS, NAT |
| `ANALYTICS` | Amazon EMR, Athena, Kinesis, OpenSearch, QuickSight | Azure Synapse, Databricks, Event Hubs, Stream Analytics | BigQuery, Dataproc, Dataflow, Pub/Sub |
| `AI_ML` | Amazon SageMaker, Bedrock, Rekognition, Comprehend | Azure OpenAI, Machine Learning Studio, Cognitive Services | Vertex AI, Gemini API, Cloud Translation |
| `SECURITY` | AWS IAM, KMS, GuardDuty, WAF, Secrets Manager | Microsoft Sentinel, Key Vault, Microsoft Defender | Cloud KMS, Secret Manager, Security Command Center |
| `MANAGEMENT` | CloudWatch, CloudTrail, Systems Manager, Config | Azure Monitor, Automation, Log Analytics | Cloud Monitoring, Cloud Logging, Cloud Trace |
| `OTHER` | Unclassified marketplace charges, support plans | Support plans, unclassified licenses | Support contracts, marketplace items |

---

## 6. Pricing Model Normalization Taxonomy

All provider commitments, spot purchases, and on-demand charges map to 5 unified models:

| Unified Pricing Model | Description | AWS Identifiers | Azure Identifiers | GCP Identifiers |
| :--- | :--- | :--- | :--- | :--- |
| `ON_DEMAND` | Pay-as-you-go, uncommitted usage | `OnDemand`, `RunInstances` | `OnDemand`, `PayAsYouGo` | `On Demand`, standard rate |
| `RESERVED` | Fixed 1-year or 3-year term commitments | `Reserved`, `HeavyUsage` | `Reservation`, `Reserved VM` | `Committed Usage Discount`, `CUD` |
| `SAVINGS_PLAN` | Flexible spend commitments | `SavingsPlanCoveredUsage` | `SavingsPlan` | `Flexible CUD` |
| `SPOT` | Surplus capacity at steep discounts | `Spot`, `SpotUsage` | `Spot`, `LowPriority` | `Preemptible`, `Spot` |
| `OTHER` | Free tiers, credits, refunds | `FreeTier`, `Credit` | `FreeTier`, `Promotion` | `Free Tier`, `Promotional Credit` |
