# Statistical Baselines & Rolling Distributions

## 1. Overview

The **Statistical Baseline Engine** (`backend/app/anomaly_detection/baseline.py`) calculates rolling statistical distributions across dimensional expenditure series.

Because cloud expenditures exhibit both Gaussian behavior (steady-state infrastructure) and heavy-tailed, skewed behavior (variable workloads and serverless batch jobs), CloudSage calculates both **parametric** (mean, standard deviation) and **non-parametric** (median, Median Absolute Deviation, quartiles, IQR) baseline metrics.

---

## 2. Statistical Baseline Metrics

All calculations are implemented in pure `Decimal` in `backend/app/anomaly_detection/statistics.py`:

| Metric | Mathematical Definition | Decimal Formula | Purpose |
| :--- | :--- | :--- | :--- |
| **Mean ($\mu$)** | $\frac{1}{N}\sum_{i=1}^N x_i$ | Arithmetic average daily expenditure | Baseline for parametric Z-score |
| **Sample StdDev ($\sigma$)** | $\sqrt{\frac{1}{N-1}\sum_{i=1}^N (x_i - \mu)^2}$ | Sample variance square root ($ddof=1$) | Standard deviation scale factor |
| **Median ($Q_2$)** | $\text{Sorted}(X)[\lfloor N/2 \rfloor]$ | 50th percentile of expenditure | Outlier-resistant center of distribution |
| **Median Absolute Deviation (MAD)** | $\text{median}(\|x_i - \text{median}(X)\|)$ | Median of absolute deviations from median | Robust non-parametric scale estimator |
| **Quartile 1 ($Q_1$)** | 25th percentile of sorted values | Lower Tukey hinge | Bottom boundary of normal interquartile spread |
| **Quartile 3 ($Q_3$)** | 75th percentile of sorted values | Upper Tukey hinge | Top boundary of normal interquartile spread |
| **Interquartile Range (IQR)** | $Q_3 - Q_1$ | Spread between 75th and 25th percentiles | Non-parametric spread scale factor |
| **Min & Max** | $\min(X), \max(X)$ | Extreme observed bounds | Historical boundary context |

---

## 3. Rolling Lookback Windows

The engine supports multi-horizon rolling lookback windows:

- **7-Day Window**: Detects acute, short-term shifts and weekend/weekday variance.
- **14-Day Window**: Recommended balance for fast-moving environments and bi-weekly release cycles.
- **30-Day Window** *(Default)*: Captures standard monthly billing cycles and regular monthly cron jobs.
- **60-Day & 90-Day Windows**: Provides long-term seasonal baselines for mature workloads.

### Target-Day Exclusion Protocol
When evaluating expenditure on date $T_{\text{target}}$, the baseline window strictly covers $[T_{\text{target}} - W, T_{\text{target}} - 1]$. The target observation date itself is **excluded** from the baseline calculation to prevent contaminating the historical baseline distribution with the current potential anomaly.

---

## 4. Edge Cases and Safeguards

### 1. Insufficient Historical Data (`INSUFFICIENT_HISTORY`)
- If the number of points in the lookback window is $< 7$, the baseline status is flagged as `INSUFFICIENT_HISTORY`.
- Standard statistical anomaly detection is bypassed to eliminate false positives on newly launched infrastructure.
- The `NewSpendPatternDetector` is invoked instead to verify whether this represents a novel service or resource deployment.

### 2. Zero-Variance Safeguard (`ZERO_VARIANCE`)
- Fixed reserved instances, savings plans, or continuous flat-rate provisioned resources often exhibit identical daily costs ($\sigma = 0.0000$ and $\text{MAD} = 0.0000$).
- In standard Z-score formulas, dividing by $\sigma = 0$ causes a fatal `DivisionByZero` exception.
- CloudSage guards both Z-Score and Modified Z-Score:
  $$\sigma = 0 \implies Z = 0.0000$$
  $$\text{MAD} = 0 \implies M = 0.0000$$
- When variance is zero, the engine automatically falls back to absolute dollar deviation ($\|x_{\text{obs}} - \mu\| \ge \text{min\_excess}$) and percentage deviation thresholds.

---

## 5. Database Persistence

Baselines are persisted in the `cost_baselines` PostgreSQL table, indexed by `(dimension_key, window_days)` and `(provider, service_name)`:

```sql
SELECT dimension_key, window_days, mean, stddev, median, mad, q1, q3, iqr
FROM cost_baselines
WHERE dimension_key = 'AWS/111122223333/AmazonDynamoDB' AND window_days = 30;
```
