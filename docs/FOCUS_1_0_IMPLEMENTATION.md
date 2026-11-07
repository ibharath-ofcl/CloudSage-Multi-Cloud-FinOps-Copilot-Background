# FinOps Open Cost & Usage Specification (FOCUS™ 1.0) Implementation

## 1. Executive Summary & Specification Context

CloudSage aligns its multi-cloud canonical data model and billing normalization pipeline with the **FinOps Open Cost and Usage Specification (FOCUS) 1.0** developed by the FinOps Foundation.

- **Official Specification Reference**: [https://focus.finops.org/](https://focus.finops.org/)
- **FOCUS Specification Version**: `1.0.0`
- **CloudSage Implementation Module**: `backend/app/normalization/focus/`
- **Validation Engine**: `Focus10Validator`
- **Conformance Assessment Engine**: `FocusConformanceEngine`
- **Model Representation**: `Focus10Record`

FOCUS unifies heterogeneous billing data across Amazon Web Services (AWS), Microsoft Azure, and Google Cloud Platform (GCP) into a single, standardized schema with uniform data types, enum definitions, and column names.

---

## 2. FOCUS 1.0 Conformance Matrix

The following matrix documents the implementation status and validation rules for all 28 core dimensions in CloudSage:

| Column Name | Requirement Level | Data Type | CloudSage Implementation Status | Source / Transformation Mapping |
| :--- | :---: | :---: | :---: | :--- |
| `BillingAccountId` | **Mandatory** | String | **Fully Implemented** | AWS Payer ID, Azure Billing Account / Sub ID, GCP Billing Account ID |
| `BillingAccountName` | Recommended | String | **Partially Implemented** | Derived from billing profile or account alias when provided |
| `BillingCurrency` | **Mandatory** | String (ISO 4217) | **Fully Implemented** | Standardized to `"USD"` for global reporting |
| `BillingPeriodStart` | Conditional | DateTime (UTC) | **Fully Implemented** | Start of monthly billing period |
| `BillingPeriodEnd` | Conditional | DateTime (UTC) | **Fully Implemented** | End of monthly billing period |
| `ChargeCategory` | **Mandatory** | Enum | **Fully Implemented** | Values: `Usage`, `Purchase`, `Tax`, `Credit`, `Adjustment`, `Fee` |
| `ChargeClass` | Conditional | Enum | **Partially Implemented** | Values: `Correction`, `Reversal` for retroactive billing edits |
| `ChargeDescription` | Optional | String | **Partially Implemented** | Native line item description |
| `ChargeFrequency` | Optional | Enum | **Partially Implemented** | Values: `One-Time`, `Recurring`, `Usage-Based` |
| `ChargePeriodStart` | **Mandatory** | DateTime (UTC) | **Fully Implemented** | Usage interval start timestamp (`usage_start_time`) |
| `ChargePeriodEnd` | **Mandatory** | DateTime (UTC) | **Fully Implemented** | Usage interval end timestamp (`usage_end_time`) |
| `ConsumedQuantity` | Conditional | Decimal | **Fully Implemented** | Metric consumption amount (`usage_quantity`) |
| `ConsumedUnit` | Conditional | String | **Fully Implemented** | Normalized consumption unit (`HOURS`, `GB_MONTH`, `REQUESTS`) |
| `BilledCost` | **Mandatory** | Decimal ($\ge 0$) | **Fully Implemented** | Net invoiced cost (`unblended_cost`) in USD |
| `EffectiveCost` | **Mandatory** | Decimal ($\ge 0$) | **Fully Implemented** | Amortized cost factoring commitments/credits (`blended_cost`) |
| `ListCost` | Recommended | Decimal ($\ge 0$) | **Fully Implemented** | Public catalog list price before enterprise discounts |
| `PricingCategory` | **Mandatory** | Enum | **Fully Implemented** | Values: `On-Demand`, `Committed`, `Spot`, `Dynamic`, `Tiered`, `Other` |
| `ProviderName` | **Mandatory** | String | **Fully Implemented** | Cloud provider: `AWS`, `Microsoft Azure`, `Google Cloud Platform` |
| `PublisherName` | Optional | String | **Fully Implemented** | Provider name or marketplace 3rd party publisher |
| `RegionId` | Conditional | String | **Fully Implemented** | Hyperscaler region identifier (`us-east-1`, `westeurope`, etc.) |
| `RegionName` | Optional | String | **Partially Implemented** | Human readable region display name |
| `ResourceId` | Conditional | String | **Fully Implemented** | Hyperscaler resource ARN or fully qualified ARM URI |
| `ResourceName` | Recommended | String | **Fully Implemented** | Parsed resource identifier or user-provided `Name` tag |
| `ResourceType` | Conditional | String | **Fully Implemented** | Canonical type: `aws:ec2:instance`, `azure:compute:vm`, etc. |
| `ServiceCategory` | **Mandatory** | Enum | **Fully Implemented** | `Compute`, `Storage`, `Database`, `Network`, `Analytics`, `AI/ML`, `Security` |
| `ServiceName` | **Mandatory** | String | **Fully Implemented** | Native service code: `AmazonEC2`, `Virtual Machines`, `Compute Engine` |
| `SubAccountId` | Conditional | String | **Fully Implemented** | AWS Linked Account ID, Azure Subscription GUID, GCP Project ID |
| `SubAccountName` | Optional | String | **Partially Implemented** | Sub-account display name or project name |
| `Tags` | Recommended | JSON Key-Value | **Fully Implemented** | Sanitized key-value metadata dictionary |
| `x_OriginalCost` | Extension | Decimal | **Fully Implemented** | Pre-conversion original invoice cost amount |
| `x_OriginalCurrency` | Extension | String | **Fully Implemented** | Pre-conversion ISO 4217 original currency code |
| `x_Fingerprint` | Extension | String (SHA-256) | **Fully Implemented** | 64-character composite idempotency hash |

---

## 3. Financial Costs: BilledCost vs. EffectiveCost vs. ListCost

A foundational requirement of FOCUS 1.0 is strict separation of financial perspectives:

1. **`BilledCost`**:
   - Represents the cash amount actually invoiced for the charge period.
   - For on-demand usage, $BilledCost = EffectiveCost$.
   - For pre-paid reservations or savings plans, $BilledCost = 0$ during usage periods, and the lump sum is invoiced at purchase time.
2. **`EffectiveCost`**:
   - Reflects the true economic cost of consumption.
   - Amortizes upfront reservation fees and committed usage discounts across the hours of actual usage.
   - Incorporates promotional and sustained-use credits.
3. **`ListCost`**:
   - The publicly available retail catalog rate for the resource without any commitment, volume, or enterprise contract discounts.
   - Used in FinOps reporting to compute **Negotiated Savings**:
     $$\text{Negotiated Savings} = \text{ListCost} - \text{BilledCost}$$

---

## 4. Automated Validation Engine (`Focus10Validator`)

Every incoming billing record is verified against FOCUS 1.0 validation rules:

- **Mandatory Completeness**: Asserts non-null values for all 11 mandatory dimensions.
- **Data Type Integrity**:
  - Costs must be strictly arbitrary-precision `Decimal` $\ge 0$.
  - Timestamps must be timezone-aware ISO 8601 UTC objects.
  - Currencies must be valid 3-letter ISO 4217 uppercase strings.
- **Enum Conformance**:
  - Validates `ChargeCategory` against: `Usage`, `Purchase`, `Tax`, `Credit`, `Adjustment`, `Fee`.
  - Validates `PricingCategory` against: `On-Demand`, `Committed`, `Spot`, `Dynamic`, `Tiered`, `Other`.
  - Validates `ServiceCategory` against standard FOCUS classes.
- **Weighted Conformance Score**:
  $$\text{Score} = \left(\frac{\text{Mandatory Passed}}{11} \times 70\%\right) + \left(\frac{\text{Conditional Passed}}{6} \times 20\%\right) + \left(\frac{\text{Recommended Passed}}{5} \times 10\%\right)$$

---

## 5. FOCUS Export Capabilities

CloudSage provides programmatic export from the internal `BillingRecord` representation to standard FOCUS 1.0 dictionaries, JSON, and CSV via [`FocusExporter`](file:///Users/bharathbodduvenkata/PROJECTS/CloudSage,%20Multi-Cloud%20FinOps%20Copilot%20Background/backend/app/normalization/focus/exporter.py):

```python
from backend.app.normalization.focus.exporter import FocusExporter

# Export database record to FOCUS dictionary
focus_payload = FocusExporter.to_focus_dict(db_record)
print(focus_payload["ChargeCategory"])   # "Usage"
print(focus_payload["EffectiveCost"])    # Decimal("12.5000")
print(focus_payload["ServiceCategory"])  # "Compute"
```

---

## 6. Known Limitations

1. **Vendor Extension Coverage**: Certain specialized provider fields (e.g. AWS detailed reservation ARN, Azure reservation order ID) are preserved in the `x_` extension dictionary rather than top-level columns.
2. **ChargeClass Granularity**: Retroactive invoice corrections and credit memos are mapped to `Credit` or `Adjustment` ChargeCategory, with ChargeClass populated when supported by the provider feed.
3. **Formal Certification**: CloudSage conforms to the public FOCUS 1.0 specification with automated validation, but does not claim third-party certification.
