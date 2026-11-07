# Multi-Cloud Provider Comparison & Trends

## 1. Objective & Scope

As enterprises adopt multi-cloud architectures, cloud spend becomes fragmented across AWS, Azure, and GCP. The Provider Comparison module unifies these disparate billing feeds into a normalized comparative framework based on the **FinOps Open Cost & Usage Specification (FOCUS™ 1.0)**.

This enables enterprises to answer key strategic questions:
1. What proportion of our infrastructure spend is concentrated in each cloud provider?
2. Are workloads shifting between clouds over time?
3. Which cloud provider is delivering higher cost efficiency for compute vs storage vs databases?

---

## 2. Comparative Metrics Matrix

| Dimension | AWS | Microsoft Azure | Google Cloud Platform |
|---|---|---|---|
| **Identity Identifier** | 12-digit AWS Account ID | Azure Subscription GUID | GCP Project ID & Number |
| **Billed Cost Source** | AWS Cost & Usage Report (CUR 2.0) | Azure Cost Management Export | GCP Cloud Billing Export (BigQuery) |
| **Normalized Cost Model** | FOCUS `BilledCost` & `EffectiveCost` | FOCUS `BilledCost` & `EffectiveCost` | FOCUS `BilledCost` & `EffectiveCost` |
| **Currency Normalization** | Converted to USD via daily ECB/Fed rates | Converted to USD via daily rates | Converted to USD via daily rates |
| **Asset Discovery** | EC2, EBS, S3, RDS, NAT Gateway | VMs, Disks, Storage Accounts, SQL | Compute Engine, PD, GCS, Cloud SQL |

---

## 3. Mathematical Share Allocation

For each cloud provider $p \in \{\text{AWS}, \text{AZURE}, \text{GCP}\}$:

$$\text{Share}_p = \left( \frac{\text{Spend}_p}{\sum_{k} \text{Spend}_k} \right) \times 100\%$$

Where:
- $\text{Spend}_p$ is the exact `Decimal` sum of `BillingRecord.unblended_cost` for provider $p$.
- Sum of all shares strictly equals $100.00\%$ (with standard banking rounding).

---

## 4. Multi-Cloud Correlation & Cross-Cloud Insights

CloudSage's correlation engine automatically links discovered inventory assets (`CloudResource`) to billing line items (`BillingRecord`):
- **Resource Count**: Quantifies active infrastructure footprints per provider.
- **Cost per Resource**: Evaluates average expenditure per asset across providers.
- **Waste Concentration**: Highlights which provider hosts the highest proportion of idle assets or unattached storage volumes.
