# Anomaly Financial Impact & Projections

## 1. Overview

Accurate financial quantification is critical for FinOps prioritization. Minor percentage increases on large budgets can represent tens of thousands of dollars, while massive percentage increases on micro-workloads may represent only pennies.

The **Financial Impact Calculator** (`backend/app/anomaly_detection/impact.py`) computes deterministic dollar deviations, projects monthly and annual impact horizons, assigns severity tiers, and enforces anti-double-counting guarantees.

---

## 2. Core Mathematical Formulations

All operations use strict Python `Decimal` with `ROUND_HALF_UP` to four decimal places (`0.0001`):

### 1. Absolute Deviation
$$\text{Absolute Deviation} = |x_{\text{observed}} - x_{\text{expected}}|$$

### 2. Percentage Deviation
$$\text{Percentage Deviation} = \begin{cases}
\left(\frac{x_{\text{observed}} - x_{\text{expected}}}{x_{\text{expected}}}\right) \times 100 & \text{if } x_{\text{expected}} > 0 \\
100.0000\% & \text{if } x_{\text{expected}} = 0 \text{ and } x_{\text{observed}} > 0 \\
0.0000\% & \text{otherwise}
\end{cases}$$

### 3. Estimated Excess Cost
$$\text{Estimated Excess Cost} = \max\left(0, x_{\text{observed}} - x_{\text{expected}}\right)$$

### 4. Projected Horizon Impact
- **Temporary Spike**: Discrete event duration:
  $$\text{Monthly Impact} = \text{Excess Daily} \times \text{Duration Days}$$
- **Persistent Step & Gradual Escalation**: Projected across standard calendar horizons:
  $$\text{Projected Monthly Impact} = \text{Excess Daily} \times 30.0000\text{ days}$$
  $$\text{Projected Annual Impact} = \text{Excess Daily} \times 365.0000\text{ days}$$

---

## 3. FinOps Severity Tiers

Severity reflects both monetary risk and growth rate:

| Severity Tier | Dollar Thresholds | Percentage Growth Guard | Typical Action SLA |
| :--- | :--- | :--- | :--- |
| **`CRITICAL`** | $\ge \$1,000.00$ excess | OR $\ge 200.0\%$ increase with $\ge \$250.00$ excess | PagerDuty / Same-day immediate triage |
| **`HIGH`** | $\ge \$250.00$ excess | OR $\ge 100.0\%$ increase with $\ge \$50.00$ excess | FinOps weekly sprint triage / Slack alert |
| **`MEDIUM`** | $\ge \$50.00$ excess | OR $\ge 50.0\%$ increase with $\ge \$15.00$ excess | Regular backlog review |
| **`LOW`** | All other qualifying deviations | Minimum threshold $\ge \$10.00$ | Informational / trend observation |

---

## 4. Anti-Double-Counting Guarantees

In multi-dimensional anomaly detection, spending is evaluated concurrently at multiple levels of granularity:
1. Provider level (e.g. AWS overall)
2. Service level (e.g. AWS AmazonDynamoDB)
3. Resource level (e.g. DynamoDB Table `OrderEvents`)

If a runaway table causes a service-level anomaly of $\$800$, and a resource-level anomaly of $\$800$ is also generated for the same table on the same day, adding both would incorrectly state an excess cost of $\$1,600$.

### Hierarchical Deduplication Algorithm (`aggregate_deduplicated_impact`)
1. Create composite entity keys for all anomalies:
   $$\text{Key}_{\text{Resource}} = \text{RES}:p:a:s:r:d$$
   $$\text{Key}_{\text{Service}} = \text{SRV}:p:a:s:d$$
2. If resource-level anomalies exist for service $(p, a, s)$ on date $d$, the parent service-level entry is suppressed in favor of the finer-grained resource entries.
3. The resulting deduplicated sum guarantees that every excess dollar is counted exactly once in executive summaries and financial reports.
