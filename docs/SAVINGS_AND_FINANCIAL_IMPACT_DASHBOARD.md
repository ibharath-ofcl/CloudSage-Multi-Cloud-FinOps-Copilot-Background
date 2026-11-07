# Savings & Financial Impact Dashboard

## 1. Overview & Business Impact

The Savings & Financial Impact Dashboard functions as the organization's **FinOps return on investment (ROI) ledger**. It quantifies both the prospective savings pipeline (recommendations awaiting approval or implementation) and realized savings verified through subsequent billing cycles.

---

## 2. Mathematical Realization Framework

### 2.1 Potential Savings Pipeline
The sum of projected cost reductions across open recommendations:

$$\text{Potential Monthly Savings} = \sum_{r \in \text{OpenRecs}} \text{estimated\_monthly\_savings}_r$$

$$\text{Potential Annual Savings} = 12 \times \text{Potential Monthly Savings}$$

### 2.2 Realized & Verified Savings
When an approved recommendation is implemented by an engineering team, CloudSage monitors post-implementation billing telemetry for 30 consecutive days. Once cost reductions are validated in the normalized `BillingRecord` stream, the savings are marked as verified:

$$\text{Realized Monthly Savings} = \sum_{r \in \text{VerifiedRecs}} \text{verified\_savings}_r$$

### 2.3 Realization Efficiency Rate
The proportion of identified savings opportunities successfully captured by the enterprise:

$$\text{Realization Efficiency} = \left( \frac{\text{Realized Monthly Savings}}{\text{Potential Monthly Savings} + \text{Realized Monthly Savings}} \right) \times 100\%$$

---

## 3. Anti-Double-Counting Guarantees

FinOps platforms frequently suffer from double-counting when multiple engines flag related issues (e.g., an idle VM flagged as both an anomaly spike and a rightsizing recommendation).

CloudSage enforces mathematical anti-double-counting guarantees:
1. **Deduplication by Resource ARN/URI**: When an asset is flagged for rightsizing, separate idle detections for that same asset are suppressed or merged.
2. **Segregation of Ledgers**: Waste, Anomalies, Potential Savings, and Actual Expenditure exist in strictly separate ledger columns and are never cross-summed into misleading totals.
3. **Audit Trail**: Every realized savings figure is backed by an auditable link to specific `BillingRecord` charge items before and after implementation.
