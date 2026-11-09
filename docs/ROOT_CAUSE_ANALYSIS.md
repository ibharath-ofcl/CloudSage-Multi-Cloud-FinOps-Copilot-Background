# Multi-Dimensional Root Cause Analysis: Algorithms & Mathematics

## Overview

Cloud cost anomalies are rarely uniform; they are driven by specific combinations of resources, regions, SKUs, and consumption patterns. CloudSage's Root Cause Analysis (RCA) engine decomposes anomalous expenditure into understandable, quantifiable components using mathematically sound decomposition models.

---

## 1. 10-Dimensional FOCUS Decomposition

CloudSage projects anomalous expenditure across 10 orthogonal dimensions:

$$D = \{ \text{PROVIDER}, \text{ACCOUNT}, \text{REGION}, \text{SERVICE}, \text{RESOURCE\_ID}, \text{SKU}, \text{ENVIRONMENT}, \text{OWNER}, \text{COST\_CENTER}, \text{BILLING\_TAGS} \}$$

For any dimension $d \in D$, with unique values $\{v_1, v_2, \dots, v_n\}$:

$$\text{Spend}(v_i) = \sum_{r \in R(v_i)} \text{EffectiveCost}(r)$$

Where $R(v_i)$ represents all normalized billing line items matching dimension value $v_i$.

### Anti-Double Counting Guarantee
Within each dimension slice:
$$\sum_{i=1}^n \text{Spend}(v_i) = \text{TotalSliceSpend}$$
Every line item is attributed to exactly one partition per dimension. Cross-dimensional totals are evaluated independently to prevent double counting across parallel hierarchical views.

### Dominant Dimension Identification
The dominant dimension is selected by maximizing the Gini concentration ratio and primary contributor share:
$$d^* = \arg\max_{d \in D} \left( \frac{\max_{v \in d} \text{ExcessSpend}(v)}{\text{TotalExcessSpend}} \right)$$

---

## 2. Pareto 80/20 Contribution Ranking

The Pareto principle states that roughly 80% of consequences come from 20% of causes. In cloud billing, a tiny fraction of resources typically drives the vast majority of unexpected spending spikes.

### Ranking Algorithm
1. **Calculate Contributor Impact**:
   For each distinct entity $e_j \in E$ (e.g., individual instances, storage buckets, API endpoints):
   $$\text{Excess}(e_j) = \text{Actual}(e_j) - \text{Baseline}(e_j)$$

2. **Sort in Descending Order**:
   Order entities such that $\text{Excess}(e_1) \ge \text{Excess}(e_2) \ge \dots \ge \text{Excess}(e_m)$.

3. **Compute Contribution Share & Cumulative Curve**:
   $$\text{Share}(e_j) = \frac{\text{Excess}(e_j)}{\sum_{k=1}^m \text{Excess}(e_k)} \times 100\%$$
   $$\text{CumulativeShare}(e_j) = \sum_{k=1}^j \text{Share}(e_k)$$

4. **Identify Pareto Cutoff**:
   The Pareto 80 set is defined as:
   $$E_{80} = \{ e_1, e_2, \dots, e_p \} \quad \text{where} \quad p = \min \{ j \mid \text{CumulativeShare}(e_j) \ge 80\% \}$$

Entities in $E_{80}$ are highlighted as **Primary Cost Drivers**, while entities outside $E_{80}$ are designated as **Long-Tail Variations**.

---

## 3. Economic Growth Accounting: Usage vs. Price

Cloud spend variance between baseline period $t_0$ and anomaly period $t_1$ is governed by two independent levers:
1. **Quantity (Usage)**: How much resource was consumed ($Q$).
2. **Price (Rate)**: What effective rate was paid per unit ($P$).

$$\text{Cost}_0 = Q_0 \cdot P_0$$
$$\text{Cost}_1 = Q_1 \cdot P_1$$

Where:
$$\Delta Q = Q_1 - Q_0, \quad \Delta P = P_1 - P_0$$

### Exact Three-Way Decomposition
$$\Delta \text{Cost} = \text{Cost}_1 - \text{Cost}_0 = Q_1 \cdot P_1 - Q_0 \cdot P_0$$
$$= (Q_0 + \Delta Q)(P_0 + \Delta P) - Q_0 \cdot P_0$$
$$= Q_0 \cdot P_0 + \Delta Q \cdot P_0 + Q_0 \cdot \Delta P + \Delta Q \cdot \Delta P - Q_0 \cdot P_0$$
$$\mathbf{\Delta \text{Cost} = \Delta Q \cdot P_0 + \Delta P \cdot Q_0 + \Delta Q \cdot \Delta P}$$

### Interpretation of Terms
| Term | Component Name | FinOps Meaning | Example Causes |
|---|---|---|---|
| $\Delta Q \cdot P_0$ | **Usage Volume Effect** | Variance caused purely by increased workload consumption at baseline pricing. | Autoscaling spikes, runaway batch jobs, unthrottled loop execution, uncompressed backups. |
| $\Delta P \cdot Q_0$ | **Price Rate Effect** | Variance caused purely by unit rate changes at baseline consumption level. | Reserved Instance expiration, On-Demand fallback, tier change, regional egress pricing change. |
| $\Delta Q \cdot \Delta P$ | **Mix / Joint Effect** | Interactive compound effect when both volume and unit rate shifted simultaneously. | Scaling out on expensive on-demand instances during peak pricing periods. |

### Handling Net-New Infrastructure ($Q_0 = 0$)
When an entity did not exist in the baseline period ($Q_0 = 0$):
$$\Delta Q = Q_1 - 0 = Q_1$$
$$\Delta P = P_1 - 0 = P_1$$
The engine categorizes this as `NET_NEW_RESOURCE_EFFECT`, ensuring clear distinction between existing workload expansion and newly deployed services.

---

## 4. Time-Series Continuity & Moving Averages

Real-world billing feeds suffer from missing records, delayed provider reporting, and zero-spend days. The engine guarantees resilient analysis through:

### Daily Grid Reconstruction
Given anomaly date $T_a$, a continuous daily evaluation window is constructed:
$$W = [T_a - 14\text{ days}, T_a + 2\text{ days}]$$
Any date $t \in W$ lacking billing records is populated with $0.0000$ USD spend, preventing broken index errors or artificial gaps in trendlines.

### 7-Day Rolling Moving Average
To eliminate day-of-week seasonality (e.g., weekend dropoffs in development environments), each day's rolling expectation is computed over the trailing 7 days:
$$\text{SMA}_7(t) = \frac{1}{7} \sum_{k=1}^7 \text{Spend}(t - k)$$

### Variance Metrics
- **Day-over-Day (DoD)**:
  $$\text{DoD}(T_a) = \frac{\text{Spend}(T_a) - \text{Spend}(T_a - 1)}{\max(\text{Spend}(T_a - 1), \epsilon)} \times 100\%$$
- **Week-over-Week (WoW)**:
  $$\text{WoW}(T_a) = \frac{\text{Spend}(T_a) - \text{Spend}(T_a - 7)}{\max(\text{Spend}(T_a - 7), \epsilon)} \times 100\%$$
- **Month-over-Month (MoM)**:
  $$\text{MoM}(T_a) = \frac{\text{Spend}(T_a) - \text{SMA}_7(T_a)}{\max(\text{SMA}_7(T_a), \epsilon)} \times 100\%$$

---

## 5. Evidence-Grounded Confidence Scoring

Every finding is assigned an empirical confidence score ($C \in [0.0, 1.0]$) and tier:
- `HIGH` ($C \ge 0.85$): Corroborated by telemetry, billing line items, and cross-signals.
- `MEDIUM` ($0.65 \le C < 0.85$): Substantial billing evidence with partial hardware telemetry.
- `LOW` ($0.40 \le C < 0.65$): Plausible hypothesis but missing corroborating metrics.
- `INSUFFICIENT_EVIDENCE` ($C < 0.40$): Sparse or inconsistent data.

### Scoring Deductions
- **Contradictory Telemetry Penalty**: $-0.25$ if cost surged but CPU/network utilization was near zero.
- **Missing Baseline Penalty**: $-0.15$ if prior 7-day spend history is unavailable.
- **Stale Inventory Penalty**: $-0.10$ if resource was deleted or not synced within 48 hours.
- **Unreconciled Line Item Penalty**: $-0.10$ if line items lack resource ID or tags.
