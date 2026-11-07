# CloudSage Conservative Financial Savings Estimation Methodology

## 1. Zero Float Rule (Financial Determinism)

In financial engineering, binary floating-point representation (`float`) introduces insidious representation inaccuracies (e.g., $0.1 + 0.2 = 0.30000000000000004$). Over millions of cloud billing line items, floating-point drift can result in substantial monetary discrepancies, eroding trust with financial executives and auditors.

CloudSage mandates the **Zero Float Rule** across all layers:
- **Python Backend**: All financial math, multipliers, ratios, and summations utilize `decimal.Decimal`.
- **Database Schema**: All monetary columns are typed `Numeric(18, 4)` and rates are typed `Numeric(18, 6)`.
- **API Payloads**: Currency values serialize to high-precision Decimal strings/numbers.

---

## 2. Savings Calculation Formulas by Waste Category

| Waste Category | Valuation Source Priority | Exact Calculation Formula | Realized Ratio |
| :--- | :--- | :--- | :--- |
| **Idle Compute** | 1. `resource.monthly_cost`<br>2. $\sum \text{unblended\_cost}$ | $\text{savings} = \text{cost}$ | 100% of unblended compute fee |
| **Oversized Compute** | `resource.monthly_cost` | $\text{savings} = (\text{cost} \times \text{Decimal}('0.50')).\text{quantize}(\text{Decimal}('0.0001'))$ | 50% single-tier rightsizing |
| **Unattached Storage** | 1. `resource.monthly_cost`<br>2. $\text{size\_gb} \times \$0.08$ | $\text{savings} = \text{cost}$ | 100% of provisioned disk cost |
| **Orphaned Snapshots** | 1. `resource.monthly_cost`<br>2. $\text{size\_gb} \times \$0.05$ | $\text{savings} = \text{cost}$ | 100% of snapshot storage fee |
| **Underutilized Database** | `resource.monthly_cost` | $\text{savings} = \text{cost}$ | Full instance reclamation |
| **Unassociated IP** | `resource.monthly_cost` | $\text{savings} = \text{cost}$ (Default $\$3.65/\text{month}$) | 100% of idle IPv4 charge |
| **Zero-Target LB** | `resource.monthly_cost` | $\text{savings} = \text{cost}$ (Default $\$18.00/\text{month}$) | 100% of base hourly LB charge |

---

## 3. Annualization & Aggregation Integrity

- **Annualized Savings Calculation**:
  $$\text{Annual Savings} = \text{Monthly Savings} \times \text{Decimal}('12')$$
  Guarantees zero rounding drift across monthly and annualized portfolio aggregations.

- **Anti-Double-Counting Rule**:
  Because findings are deduplicated per resource on `(resource_id, waste_type)`, identical finding types cannot be duplicated. Furthermore, when reporting portfolio totals, findings are grouped by resource to avoid compounding rightsizing and termination savings on the same resource.
