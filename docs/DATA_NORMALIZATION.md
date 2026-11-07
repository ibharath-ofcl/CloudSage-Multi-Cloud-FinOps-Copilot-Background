# Data Normalization & FOCUS 1.0 Alignment

This document details the normalization processes applied by the CloudSage Ingestion Engine to convert heterogeneous cloud billing streams into a unified, high-integrity dataset.

---

## 1. FinOps Open Cost & Usage Specification (FOCUS 1.0) Alignment

The CloudSage canonical billing model is designed around the **FOCUS 1.0 Specification** developed by the FinOps Foundation. FOCUS unifies billing definitions across public clouds to enable automated cross-cloud analytics.

### Mapping Matrix to FOCUS 1.0

| FOCUS 1.0 Column Name | CloudSage Canonical Field | Description |
| :--- | :--- | :--- |
| `ProviderName` | `cloud_provider` | Cloud service provider identifier (`AWS`, `AZURE`, `GCP`) |
| `BillingAccountId` | `account_id` | Top-level billing account, payer ID, or subscription |
| `BillingAccountName` | `account_name` | Human-readable billing account identifier |
| `ServiceName` | `service_name` | Clean product name |
| `ServiceCategory` | `service_category` | High-level taxonomy (`COMPUTE`, `STORAGE`, `DATABASE`, etc.) |
| `ResourceId` | `resource_id` | Native cloud resource identifier or ARN |
| `ResourceName` | `resource_name` | Extracted resource name |
| `RegionId` | `region` | Normalized cloud region (e.g., `us-east-1`, `westeurope`) |
| `AvailabilityZone` | `availability_zone` | Specific sub-region zone |
| `ChargePeriodStart` | `usage_start_time` | ISO 8601 UTC timestamp of interval start |
| `ChargePeriodEnd` | `usage_end_time` | ISO 8601 UTC timestamp of interval end |
| `ConsumedQuantity` | `usage_amount` | Numeric usage quantity |
| `ConsumedUnit` | `usage_unit` | Unit of measure (`Hours`, `GB-Hours`, `Requests`) |
| `BilledCost` | `cost_amount` | Invoiced financial cost in native currency |
| `BillingCurrency` | `currency` | ISO 4217 currency code |
| `EffectiveCost` | `cost_in_usd` | Cost normalized to USD for global reporting |
| `PricingCategory` | `pricing_model` | Standardized commitment tier (`ON_DEMAND`, `RESERVED`, etc.) |
| `Tags` | `tags` | Clean JSON dictionary of resource metadata |

---

## 2. Currency Normalization & Conversion

Enterprises frequently receive invoices across multiple local currencies (EUR, GBP, JPY, AUD, CAD, INR). To enable cross-cloud aggregation, executive rollups, and anomaly detection, CloudSage computes a normalized `cost_in_usd` column for every line item.

### 2.1 Currency Conversion Principles
- **No Float Arithmetic**: All conversions use `Decimal` objects.
- **Conversion Equation**:
  $$\text{cost\_in\_usd} = \text{ROUND}\left( \frac{\text{cost\_amount}}{\text{FX\_RATE}[\text{currency}]}, 4 \right)$$
- **Precision**: Rounded to 4 decimal places using `ROUND_HALF_UP`.
- **Baseline Exchange Rates** (stored in `backend/app/ingestion/normalizer.py`):

| Currency Code | Currency Name | Reference Rate (1 USD = X Units) |
| :--- | :--- | :--- |
| `USD` | US Dollar | $1.0000$ |
| `EUR` | Euro | $0.9200$ |
| `GBP` | British Pound | $0.7900$ |
| `JPY` | Japanese Yen | $155.0000$ |
| `CAD` | Canadian Dollar | $1.3800$ |
| `AUD` | Australian Dollar | $1.5200$ |
| `INR` | Indian Rupee | $83.5000$ |
| `CHF` | Swiss Franc | $0.8900$ |

*Future Enhancement*: Production environments will pull real-time daily spot FX rates from ECB or Open Exchange Rates into a `currency_rates` database table.

---

## 3. Timestamp Normalization & UTC Enforcement

Cloud providers report timestamps using varying formats, offsets, and granularities:

| Cloud Provider | Native Format Example | Standardized Target Format |
| :--- | :--- | :--- |
| **AWS CUR** | `2026-11-01T00:00:00Z` or `2026/11/01 00:00:00` | `2026-11-01 00:00:00+00:00` |
| **Azure Cost Export** | `11/01/2026` or `2026-11-01T14:30:00Z` | `2026-11-01 14:30:00+00:00` |
| **GCP BigQuery Export** | `2026-11-01 00:00:00 UTC` or ISO string | `2026-11-01 00:00:00+00:00` |

### Timestamp Rules:
1. **Timezone Awareness**: All parsed datetimes are converted to timezone-aware UTC objects (`datetime.timezone.utc`).
2. **Date-Only Inference**: If a provider supplies only a date (`YYYY-MM-DD`):
   - `usage_start_time` is set to `00:00:00 UTC`.
   - `usage_end_time` is set to `23:59:59 UTC`.
3. **Partition Boundary Integrity**: Ensures partition pruning works accurately across PostgreSQL range-partitioned tables (`billing_records_y2026m11`).

---

## 4. Tag Sanitization & Metadata Extraction

Resource tags are critical for FinOps chargeback, showback, and idle resource attribution. However, tagging standards differ across clouds.

### 4.1 Tag Sanitization Process

1. **Prefix Elimination**:
   - AWS CUR tags (`resourceTags/user:Name`, `resourceTags/aws:createdBy`) are stripped of their `resourceTags/user:` and `resourceTags/aws:` prefixes.
2. **Whitespace Trimming**: Keys and values have leading/trailing whitespace removed.
3. **Case Normalization**: Canonical FinOps attributes are extracted using case-insensitive matching:
   - **Environment**: Extracted from keys `["environment", "env", "stage", "tier"]`. Normalizes values to lowercase (`"production"`, `"staging"`, `"development"`).
   - **Owner**: Extracted from keys `["owner", "created_by", "creator", "team", "author"]`.
   - **Cost Center**: Extracted from keys `["cost_center", "costcenter", "cc", "billing_code"]`.
   - **Project**: Extracted from keys `["project", "application", "service", "app"]`.

### 4.2 Handling Untagged Resources
If a resource has empty or missing tags:
- `tags` is initialized to an empty JSON object `{}`.
- `environment` is set to `None`.
- `owner` is set to `None`.
- Downstream waste detection algorithms tag the resource with `POORLY_TAGGED` waste alerts.
