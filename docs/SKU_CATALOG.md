# Multi-Cloud SKU Catalog & Taxonomy Normalization

## 1. Executive Summary

Cloud providers use disparate terminology for identical technical concepts (e.g. AWS calls virtual machines `AmazonEC2`, Azure calls them `Virtual Machines`, and GCP calls them `Compute Engine`). 

The CloudSage **SKU Catalog Engine** normalizes multi-cloud service identifiers into unified FinOps categories and subcategories with transparent confidence scoring and audit provenance.

- **Module**: `backend/app/normalization/catalog/`
- **Database Model**: `SkuCatalogMapping` (`sku_catalog_mappings` table)
- **Lookup Engine**: `CatalogLookupEngine`
- **Cache**: `SkuCatalogCache`

---

## 2. Taxonomy Hierarchy

Every cloud resource is mapped to a three-tier taxonomic hierarchy:

$$\text{Category} \longrightarrow \text{Service Family} \longrightarrow \text{Resource Type}$$

| Canonical Category | Service Family Examples | Canonical Resource Type Examples |
| :--- | :--- | :--- |
| `COMPUTE` | Virtual Machine, Serverless Function, Container Cluster | `aws:ec2:instance`, `azure:compute:vm`, `gcp:compute:instance` |
| `STORAGE` | Object Storage, Block Storage, File Storage, Cold Archive | `aws:s3:bucket`, `aws:ebs:volume`, `azure:storage:blob`, `gcp:storage:bucket` |
| `DATABASE` | Relational Database, NoSQL Document, In-Memory Cache | `aws:rds:db_instance`, `azure:sql:databases`, `gcp:sql:instance` |
| `NETWORKING` | Virtual Network, Load Balancer, CDN, DNS, NAT Gateway | `aws:cloudfront:distribution`, `azure:network:vnet`, `gcp:compute:forwardingrule` |
| `ANALYTICS` | Data Warehouse, Big Data Processing, Event Streaming | `gcp:bigquery:dataset`, `aws:emr:cluster`, `azure:synapse:workspace` |
| `AI_ML` | Managed Model Training, Real-Time Inference, GenAI API | `aws:sagemaker:endpoint`, `azure:cognitive:openai`, `gcp:vertex:model` |
| `SECURITY` | Key Management, Secrets Store, Web Application Firewall | `aws:kms:key`, `azure:keyvault:vault`, `gcp:kms:key` |
| `MANAGEMENT` | Telemetry & Logs, Configuration Audit, Backup Policy | `aws:cloudwatch:alarm`, `azure:monitor:workspace`, `gcp:monitoring:metric` |
| `OTHER` | Unclassified marketplace charges, support tiers | `aws:support:business`, `azure:support:standard` |

---

## 3. Resolution Sequence & Provenance Tracking

When resolving a provider line item, `CatalogLookupEngine.resolve_service` executes the following tiered resolution:

```
                      ┌──────────────────────────────────────────────┐
                      │    CatalogLookupEngine.resolve_service       │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │     Tier 1: In-Memory LRU Catalog Cache      │
                      └──────────────┬───────────────────────────────┘
                                     │ (Miss)
                                     ▼
                      ┌──────────────────────────────────────────────┐
                      │     Tier 2: PostgreSQL sku_catalog_mappings  │
                      │     (Enterprise User & Custom Overrides)     │
                      │     Confidence: 1.0000 | Provenance: USER    │
                      └──────────────┬───────────────────────────────┘
                                     │ (Miss)
                                     ▼
                      ┌──────────────────────────────────────────────┐
                      │     Tier 3: Static System Catalog Mappings   │
                      │     (Pre-verified Hyperscaler Signatures)    │
                      │     Confidence: 1.0000 | Provenance: SYSTEM  │
                      └──────────────┬───────────────────────────────┘
                                     │ (Miss)
                                     ▼
                      ┌──────────────────────────────────────────────┐
                      │     Tier 4: Fuzzy Keyword Heuristic Matcher  │
                      │     Confidence: 0.8500 | Provenance: HEURISTIC│
                      └──────────────┬───────────────────────────────┘
                                     │ (Miss)
                                     ▼
                      ┌──────────────────────────────────────────────┐
                      │     Tier 5: Unknown SKU Quarantine Handler   │
                      │     Category: 'OTHER' | Confidence: 0.5000   │
                      │     is_known: False | Provenance: UNKNOWN    │
                      └──────────────────────────────────────────────┘
```

---

## 4. Unknown SKU Policy: No Fabrication

> [!IMPORTANT]
> **FinOps Anti-Fabrication Rule**: When an unrecognized service or custom marketplace SKU is ingested, CloudSage **never** hallucinates or fabricates a category.
> 
> Instead, the engine:
> 1. Sets `is_known = False`.
> 2. Maps `canonical_category = "OTHER"`.
> 3. Sets `service_family = "Unclassified"`.
> 4. Assigns a lower confidence score (`0.5000`).
> 5. Marks provenance as `"UNKNOWN"`.
> 6. Flags the line item for human FinOps review via the Data Quality framework.

---

## 5. Usage Unit Normalization

Raw billing files express usage in dozens of non-standard units (`Hrs`, `Hours`, `GB-Mo`, `Gigabyte-Months`, `calls`). The catalog engine standardizes these into standard FinOps units:

| Raw Input Variant | Standardized FOCUS Unit | Unit Description |
| :--- | :---: | :--- |
| `Hrs`, `hour`, `hours`, `hr` | `HOURS` | Standard elapsed compute duration |
| `gb-mo`, `gb-month`, `gigabyte-months` | `GB_MONTH` | Cumulative monthly data storage volume |
| `requests`, `calls`, `invocations`, `count` | `REQUESTS` | API requests or serverless executions |
| `bytes`, `byte` | `BYTES` | Data transfer or raw storage size |
| `sec`, `seconds` | `SECONDS` | Sub-hour serverless execution duration |
| `tb` | `TB` | Analytical scan or warehouse query volume |
