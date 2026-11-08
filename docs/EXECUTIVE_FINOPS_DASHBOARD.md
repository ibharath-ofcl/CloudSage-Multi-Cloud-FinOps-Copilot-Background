# Executive FinOps Dashboard Specification

## 1. Overview & Objective

The Executive FinOps Dashboard provides leadership (CFO, VP of Cloud Infrastructure, Head of FinOps, Engineering Directors) with an authoritative, real-time snapshot of the organization's multi-cloud financial health.

It consolidates expenditure across **Amazon Web Services (AWS)**, **Microsoft Azure**, and **Google Cloud Platform (GCP)** into normalized, auditable metrics without requiring manual spreadsheet aggregation.

---

## 2. Core Executive KPI Metrics

| KPI Card | Technical Definition | Source Entity | Currency Rule |
|---|---|---|---|
| **Total Cloud Spend** | Sum of unblended net cash cost across all scoped billing records | `BillingRecord.unblended_cost` | Strict Decimal (`Numeric(18, 4)`) |
| **Month-to-Date (MTD) Spend** | Sum of unblended expenditure from the 1st day of the current calendar month to now | `BillingRecord.unblended_cost` where `usage_start_time >= current_month_start` | Strict Decimal |
| **Previous Period Spend** | Sum of expenditure for the complete preceding calendar month | `BillingRecord.unblended_cost` for prior month window | Strict Decimal |
| **Month-over-Month (MoM) Change** | Percentage deviation between MTD and prior period spend: $$\Delta\% = \frac{\text{MTD} - \text{Prev}}{\text{Prev}} \times 100$$ | Calculated dynamically | Decimal percentage rounded to 2 decimal places |
| **Active Cost Anomalies** | Count of open, unresolved statistical cost spike incidents | `CostAnomaly.status == 'OPEN'` | Integer count |
| **Anomalous Excess Cost** | Sum of excess unbudgeted dollars incurred by active anomalies | `CostAnomaly.estimated_excess_cost` | Strict Decimal |
| **Active Waste Findings** | Count of open idle, orphaned, or oversized resource findings | `WasteDetection.status == 'ACTIVE'` | Integer count |
| **Identified Monthly Waste** | Run-rate monthly spend attributed directly to identified waste | `WasteDetection.estimated_monthly_waste` | Strict Decimal |
| **Potential Monthly Savings** | Actionable monthly savings from proposed and approved recommendations | `Recommendation.estimated_monthly_savings` | Strict Decimal |
| **Potential Annual Savings** | Projected annualized cost reduction: $$12 \times \text{Potential Monthly}$$ | `Recommendation.estimated_annual_savings` | Strict Decimal |
| **Verified Realized Savings** | Measured, post-implementation cost reduction verified from billing telemetry | `Recommendation.verified_savings` | Strict Decimal |
| **Data Freshness Timestamp** | Most recent ingestion timestamp of billing telemetry in the database | `max(BillingRecord.created_at)` | ISO 8601 UTC |

---

## 3. Strict Zero Float Rule Compliance

Financial precision errors erode executive trust. CloudSage enforces zero floating-point arithmetic across the entire aggregation and presentation pipeline:

1. **Database Schema**: Stored as PostgreSQL `Numeric(18, 4)`.
2. **Backend Service**: Processed exclusively using Python `Decimal` with explicit quantization (`quantize(Decimal("0.0001"))`).
3. **Pydantic Validation**: Schemas serialize monetary amounts as exact strings or exact Decimal numbers.
4. **Rounding Policy**: Standard `ROUND_HALF_EVEN` financial rounding with zero drift.

---

## 4. Visual Layout & UX Standards

1. **Executive Header**: Displays organization name, selected scope (multi-cloud or specific provider), environment filter, data freshness indicator, export options, and AI Copilot trigger.
2. **Top KPI Row**: 6 responsive KPI cards with color-coded directionality:
   - For Costs: An increase is highlighted in red (negative trend); a decrease is highlighted in green (positive trend).
   - For Savings: An increase is highlighted in green (positive trend).
3. **Middle Analytics Row**:
   - Left: 30-day multi-cloud stacked spending trend (AWS, Azure, GCP).
   - Right: Provider cost distribution donut chart and resource count breakdown.
4. **Bottom Incident & Findings Row**:
   - Left: Top 5 cloud services by expenditure.
   - Center: Active critical and high cost anomalies with explanation snippets.
   - Right: Top actionable infrastructure waste detections with monthly run-rate impact.
