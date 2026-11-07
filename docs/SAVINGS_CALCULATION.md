# CloudSage Financial Savings Calculation Engine

## 1. Zero Float Rule Mandate

In enterprise financial engineering and FinOps, floating-point arithmetic (e.g. standard IEEE 754 float/double) introduces unacceptable binary rounding errors ($0.1 + 0.2 = 0.30000000000000004$).

CloudSage enforces the **Zero Float Rule** across all recommendation services:
1. **Python Decimal**: All monetary figures, savings, multipliers, and rates strictly use Python's `decimal.Decimal` module.
2. **PostgreSQL Numeric(18, 4)**: All database columns storing currency, costs, and savings use exact `Numeric(18, 4)` precision.
3. **Deterministic Rounding**: All intermediate financial divisions are quantized using `ROUND_HALF_UP` to 4 decimal places (`Decimal("0.0001")`).

---

## 2. Core Financial Formulas

### A. Resource Decommissioning & Termination
For idle instances, unattached disks, and orphaned snapshots:
$$\text{Monthly Savings} = \text{Current Monthly Cost}$$
$$\text{Projected Monthly Cost} = \$0.0000$$

### B. Single-Tier Rightsizing
For oversized virtual machines and database instances:
$$\text{Monthly Savings} = \max\Big(\$0.0000, \; \text{Current Monthly Cost} - \text{Target Tier Monthly Cost}\Big)$$
$$\text{Projected Monthly Cost} = \text{Target Tier Monthly Cost}$$

### C. Non-Production Environment Scheduling
For dev/staging instances running 168 hours/week (24x7) transitioned to business hours (50 hours/week):
$$\text{Off-Hours Fraction} = \frac{168 - 50}{168} = \frac{118}{168} \approx 0.702381$$
$$\text{Monthly Savings} = \text{quantize}\Big(\text{Current Monthly Cost} \times \text{Off-Hours Fraction}\Big)$$
$$\text{Projected Monthly Cost} = \text{Current Monthly Cost} - \text{Monthly Savings}$$

### D. Cold Storage Lifecycle Tiering
For infrequently accessed data transitioned from Standard to Glacier / Archive:
$$\text{Discount Rate} = 1.0000 - \text{Target Rate Multiplier} = 1.0000 - 0.2000 = 0.8000 \quad (80\%)$$
$$\text{Monthly Savings} = \text{Current Monthly Cost} \times 0.8000$$
$$\text{Projected Monthly Cost} = \text{Current Monthly Cost} \times 0.2000$$

### E. Commitment Discount Simulation
For baseline steady-state on-demand spend converted to 1-year Savings Plans or Reserved Instances:
$$\text{Net Discount} = 0.3000 \quad (30\%)$$
$$\text{Monthly Savings} = \text{Monthly On-Demand Spend} \times 0.3000$$
$$\text{Projected Monthly Cost} = \text{Monthly On-Demand Spend} \times 0.7000$$

---

## 3. Annualization and ROI Metrics

### A. Annualized Financial Impact
Annual savings are calculated as 12 calendar months of projected monthly reduction:
$$\text{Annual Savings} = \text{Monthly Savings} \times 12$$

### B. Realization Rate
Measures the proportion of identified savings successfully implemented and verified:
$$\text{Realization Rate (\%)} = \left(\frac{\text{Verified Realized Monthly Savings}}{\text{Total Identified Monthly Savings}}\right) \times 100$$

### C. Return on Investment (ROI)
For recommendations requiring engineering implementation expenditure:
$$\text{ROI (\%)} = \left(\frac{\text{Annual Savings} - \text{Implementation Cost}}{\text{Implementation Cost}}\right) \times 100$$
If estimated implementation cost is \$0, CloudSage reports a nominal ROI of `999.00%`.
