# Cloud Cost Aggregation and Time-Series Construction

## 1. Overview

Accurate anomaly detection requires high-quality, contiguous time-series data. Raw multi-cloud billing records arrive as discrete line items with variable timestamps, discontinuous usage intervals, and mixed credits.

The **Billing Time-Series Aggregation Service** (`backend/app/anomaly_detection/aggregation.py`) transforms fragmented billing records into clean, contiguous daily expenditure and usage series across standardized cloud dimensions.

---

## 2. Aggregation Dimensions

The engine aggregates spending across six hierarchical dimensions:

| Dimension Type | Grouping Key Structure | Use Case |
| :--- | :--- | :--- |
| **`PROVIDER`** | `provider` (e.g. `AWS`) | Macro provider-level budget tracking and overall spending trends. |
| **`ACCOUNT`** | `provider/account_id` (e.g. `AZURE/sub-prod-001`) | Subscription, account, and project-level cost containment. |
| **`SERVICE`** | `provider/account_id/service_name` | Service-level expenditure spikes (e.g. AmazonEC2, BigQuery, Cosmos DB). |
| **`REGION`** | `provider/region` (e.g. `GCP/us-central1`) | Regional expenditure deviations and unplanned geographical expansion. |
| **`RESOURCE`** | `provider/account_id/service_category/service_name/region/resource_id` | Individual resource runaway costs (e.g. specific VM, table, bucket). |
| **`SKU`** | `provider/account_id/service_name/pricing_model` | Pricing model shifts and specific licensing/rate deviations. |

---

## 3. Contiguous Date Zero-Filling

Cloud services with intermittent usage (such as serverless functions, batch pools, or spot clusters) frequently have calendar days with zero billing line items. Treating missing dates as absent rather than zero corrupts rolling window calculations and time-series lags.

### Zero-Filling Protocol
1. For any evaluation window $[T_{start}, T_{end}]$, compute the exact set of contiguous calendar dates:
   $$D = \{ T_{start}, T_{start} + 1\text{ day}, \dots, T_{end} \}$$
2. For each dimensional bucket, sum positive `unblended_cost` for records falling on date $d \in D$.
3. If no records exist for date $d$, instantiate a `TimeSeriesPoint`:
   $$\text{cost} = \text{Decimal}("0.0000"), \quad \text{usage\_quantity} = \text{Decimal}("0.0000"), \quad \text{source\_records} = []$$
4. Guarantee that:
   $$\text{len}(\text{points}) = (T_{end} - T_{start}).\text{days} + 1$$

---

## 4. Credit & Refund Isolation

Billing records frequently contain negative line items representing provider credits, SLA refunds, enterprise discount adjustments, and committed use rebates.

```
+----------------------------------------------------------------------------------------------------+
|                                    CREDIT ISOLATION PRINCIPLE                                      |
| Negative credit adjustments are excluded from the positive daily expenditure series used to        |
| compute baseline distributions.                                                                    |
+----------------------------------------------------------------------------------------------------+
```

### Why Credit Isolation is Mandatory:
- **Prevents Artificial Standard Deviation Inflation**: Including large negative credits distorts the baseline standard deviation ($\sigma$), artificially widening Tukey fences and suppression thresholds, causing actual cost spikes to go undetected.
- **Prevents False Anomalies on Credit Expiration**: When a temporary promotional credit expires, daily net spend returns to normal catalog rates. If net spend was tracked with credits, the return to normal catalog rates would be incorrectly flagged as an anomalous cost explosion.
- **Separate Audit Trail**: Negative credits and adjustments are preserved in the database and surfaced during root-cause attribution to explain billing reconciliations.

