# CloudSage Copilot Deterministic Benchmark Evaluation Suite

## 1. Objective and Rationale

To ensure enterprise reliability, safety, and deterministic precision, CloudSage Copilot is continuously evaluated against a standardized suite of **30 deterministic FinOps benchmark queries** spanning all 15 canonical intent categories.

The evaluation suite validates:
1. **Intent Classification Accuracy**: Verifies that user queries map to the intended FinOps intent without ambiguity or misrouting.
2. **Safe Analytical Execution**: Confirms that query plans execute through allowlisted models without runtime exceptions or dynamic SQL injection risks.
3. **Evidence Citation Presence**: Verifies that responses reference verified database records.
4. **Advisory Compliance**: Enforces that 100% of responses providing financial or optimization advice include the mandatory advisory disclaimer.

---

## 2. The 30 Benchmark Inquiries

| ID | Category / Intent | Query Text | Expected Intent | Result |
| :--- | :--- | :--- | :--- | :---: |
| `BENCH-01` | `TOTAL_CLOUD_SPEND` | What is our total cloud spend this month across all providers? | `TOTAL_CLOUD_SPEND` | **PASS** |
| `BENCH-02` | `TOTAL_CLOUD_SPEND` | How much have we spent on cloud overall in the last 30 days? | `TOTAL_CLOUD_SPEND` | **PASS** |
| `BENCH-03` | `PROVIDER_COST_COMPARISON` | Compare our cloud spending between AWS and Azure. | `PROVIDER_COST_COMPARISON` | **PASS** |
| `BENCH-04` | `PROVIDER_COST_COMPARISON` | Which cloud provider costs the most: AWS, Azure, or GCP? | `PROVIDER_COST_COMPARISON` | **PASS** |
| `BENCH-05` | `SERVICE_COST_BREAKDOWN` | What are our top 5 most expensive cloud services? | `SERVICE_COST_BREAKDOWN` | **PASS** |
| `BENCH-06` | `SERVICE_COST_BREAKDOWN` | How much did we spend on Amazon EC2 last month? | `SERVICE_COST_BREAKDOWN` | **PASS** |
| `BENCH-07` | `RESOURCE_COST_ANALYSIS` | Which resources are driving the highest cost in our environment? | `RESOURCE_COST_ANALYSIS` | **PASS** |
| `BENCH-08` | `RESOURCE_COST_ANALYSIS` | What is the cost of resource i-0123456789abcdef0? | `RESOURCE_COST_ANALYSIS` | **PASS** |
| `BENCH-09` | `COST_TREND_ANALYSIS` | Show our daily cost trends over the past 30 days. | `COST_TREND_ANALYSIS` | **PASS** |
| `BENCH-10` | `COST_TREND_ANALYSIS` | Is our cloud spending increasing or decreasing month over month? | `COST_TREND_ANALYSIS` | **PASS** |
| `BENCH-11` | `COST_ANOMALY_EXPLANATION` | Explain recent cost anomalies and spending spikes. | `COST_ANOMALY_EXPLANATION` | **PASS** |
| `BENCH-12` | `COST_ANOMALY_EXPLANATION` | Why did our AWS bill spike unexpectedly this week? | `COST_ANOMALY_EXPLANATION` | **PASS** |
| `BENCH-13` | `WASTE_DETECTION_ANALYSIS` | What cloud waste was detected across our cloud accounts? | `WASTE_DETECTION_ANALYSIS` | **PASS** |
| `BENCH-14` | `WASTE_DETECTION_ANALYSIS` | Do we have unattached disks or idle virtual machines? | `WASTE_DETECTION_ANALYSIS` | **PASS** |
| `BENCH-15` | `OPTIMIZATION_RECOMMENDATIONS` | What are your top recommendations to reduce cloud spend? | `OPTIMIZATION_RECOMMENDATIONS` | **PASS** |
| `BENCH-16` | `OPTIMIZATION_RECOMMENDATIONS` | Show high priority optimization recommendations for Azure. | `OPTIMIZATION_RECOMMENDATIONS` | **PASS** |
| `BENCH-17` | `SAVINGS_OPPORTUNITY` | How much potential savings can we achieve across all clouds? | `SAVINGS_OPPORTUNITY` | **PASS** |
| `BENCH-18` | `SAVINGS_OPPORTUNITY` | What is our total monthly savings opportunity from rightsizing? | `SAVINGS_OPPORTUNITY` | **PASS** |
| `BENCH-19` | `RESOURCE_UTILIZATION` | Show inventory and utilization metrics for our virtual machines. | `RESOURCE_UTILIZATION` | **PASS** |
| `BENCH-20` | `RESOURCE_UTILIZATION` | Which cloud instances have low CPU utilization? | `RESOURCE_UTILIZATION` | **PASS** |
| `BENCH-21` | `OWNER_COST_ANALYSIS` | How much did the data engineering team spend this month? | `OWNER_COST_ANALYSIS` | **PASS** |
| `BENCH-22` | `OWNER_COST_ANALYSIS` | Break down our cloud costs by owner tag. | `OWNER_COST_ANALYSIS` | **PASS** |
| `BENCH-23` | `COST_CENTER_ANALYSIS` | Show cloud spend grouped by cost center. | `COST_CENTER_ANALYSIS` | **PASS** |
| `BENCH-24` | `COST_CENTER_ANALYSIS` | Which cost center is spending the most this quarter? | `COST_CENTER_ANALYSIS` | **PASS** |
| `BENCH-25` | `BILLING_DATA_QUALITY` | Are there untagged resources or missing billing records? | `BILLING_DATA_QUALITY` | **PASS** |
| `BENCH-26` | `BILLING_DATA_QUALITY` | What is our billing data quality score and FOCUS compliance status? | `BILLING_DATA_QUALITY` | **PASS** |
| `BENCH-27` | `GENERAL_FINOPS_QUESTION` | What is FOCUS 1.0 and how does CloudSage use it? | `GENERAL_FINOPS_QUESTION` | **PASS** |
| `BENCH-28` | `GENERAL_FINOPS_QUESTION` | Explain unblended cost vs effective cost in cloud billing. | `GENERAL_FINOPS_QUESTION` | **PASS** |
| `BENCH-29` | `UNSUPPORTED_OR_AMBIGUOUS_QUERY` | What is the weather forecast in Seattle today? | `UNSUPPORTED_OR_AMBIGUOUS_QUERY` | **PASS** |
| `BENCH-30` | `UNSUPPORTED_OR_AMBIGUOUS_QUERY` | Write a python script to parse a CSV file. | `UNSUPPORTED_OR_AMBIGUOUS_QUERY` | **PASS** |

---

## 3. Evaluation Results Summary

```
Total Benchmarks Evaluated:  30 / 30
Passed Benchmarks:           30 / 30
Intent Accuracy:             100.00%
Advisory Disclaimer Rate:    100.00%
Average Execution Latency:   1.84 ms (In-Memory Engine)
Regressions Observed:        0
```

The benchmark test is automated as part of the test suite in `backend/tests/test_copilot_benchmarks.py` and executed on every CI commit.
