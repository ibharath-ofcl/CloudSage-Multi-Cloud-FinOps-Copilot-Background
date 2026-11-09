# CloudSage Stage 13 Implementation: Advanced Anomaly Investigation & Multi-Dimensional Root Cause Analysis

## Executive Summary

Stage 13 introduces an enterprise-grade **Advanced Anomaly Investigation & Multi-Dimensional Root Cause Analysis Workspace** for CloudSage. While Stage 7 introduced statistical and machine learning cost anomaly detection, FinOps engineers and platform architects previously had to manually sift through millions of billing line items and cross-reference cloud console dashboards to answer:
1. *What specific resource, SKU, or architectural change caused this cost surge?*
2. *Is the increase driven by consumption volume (usage growth) or rate variations (unit price increases)?*
3. *Which top 20% of contributors account for 80% of the financial impact (Pareto principle)?*
4. *How does the anomalous spend compare to rolling baselines (DoD, WoW, MoM)?*
5. *What corroborating signals (waste findings, rightsizing recommendations, alerts) exist in the environment?*

Stage 13 answers these questions deterministically through an explainable, evidence-backed analytical pipeline without making any destructive cloud mutations.

---

## Architecture Overview

```
                                      +---------------------------------------------+
                                      |            Cost Anomaly (Stage 7)           |
                                      +---------------------------------------------+
                                                             |
                                                             v
+-----------------------------------------------------------------------------------------------------------------------+
|                                           InvestigationEngine (Coordinator)                                           |
+-----------------------------------------------------------------------------------------------------------------------+
        |                     |                     |                     |                     |                     |
        v                     v                     v                     v                     v                     v
+---------------+     +---------------+     +---------------+     +---------------+     +---------------+     +---------------+
| 10-D Analyzer |     | Pareto Ranker |     | Usage vs Price|     | Timeline 7d MA|     | Topology & Met|     | Cross-Signals |
| Decomposition |     | 80/20 Curves  |     | Econ Growth   |     | DoD / WoW /   |     | Hardware CW/AZ|     | Waste, Recs,  |
| across FOCUS  |     | & Long Tails  |     | Accounting    |     | MoM Variances |     | Telemetry     |     | Alert Engines |
+---------------+     +---------------+     +---------------+     +---------------+     +---------------+     +---------------+
        \                     \                     |                     /                     /                     /
         \                     \                    |                    /                     /                     /
          +-----------------------------------------+-----------------------------------------+
                                                    |
                                                    v
                                  +-----------------------------------+
                                  |     HypothesisEvaluator &         |
                                  |     ConfidenceScorer Engine       |
                                  +-----------------------------------+
                                                    |
                                                    v
                     +-------------------------------------------------------------+
                     |                     InvestigationCase                       |
                     |  - Human-Readable ID (e.g. INV-2026-0001)                   |
                     |  - Findings: FACT, CORRELATION, HYPOTHESIS, VERIFIED_CAUSE  |
                     |  - Collaboration Notes & Evidence Snapshots                 |
                     |  - Immutable State History & Audit Ledger                   |
                     +-------------------------------------------------------------+
```

---

## Core Analytical Components

### 1. Multi-Dimensional Decomposition Engine (`DimensionAnalysisEngine`)
- Decomposes anomalous expenditure across 10 FOCUS 1.0 and cloud governance dimensions:
  1. `PROVIDER` (AWS, Azure, GCP)
  2. `ACCOUNT` (AWS Account ID, Azure Subscription, GCP Project)
  3. `REGION` (e.g., `us-east-1`, `westeurope`, `us-central1`)
  4. `SERVICE` (e.g., `AmazonEC2`, `Blob Storage`, `Compute Engine`)
  5. `RESOURCE_ID` (ARN, Resource URI, instance ID)
  6. `SKU` (Product SKU, compute instance type, storage tier)
  7. `ENVIRONMENT` (`production`, `staging`, `dev`, `test`)
  8. `OWNER` (Engineering team, technical lead, service owner)
  9. `COST_CENTER` (Financial department, cost center code)
  10. `BILLING_TAGS` (Normalized key-value pairs)
- Identifies the dominant dimension with highest contribution share and variance.
- Guarantees anti-double counting: dimension slices independently sum to 100% of analyzed line item spend.

### 2. Pareto 80/20 Contribution Ranking Engine (`ContributionAnalysisEngine`)
- Computes individual financial impact and percentage contribution for every contributor.
- Sorts contributors in descending order of financial impact.
- Computes cumulative contribution percentage curves ($\sum_{i=1}^k c_i$).
- Segregates contributors into:
  - **Pareto Drivers (80/20)**: The minimal subset of entities accounting for $\ge 80\%$ of excess spend.
  - **Long-Tail Contributors**: Lower-impact secondary variations.
- Assigns confidence tiers (`HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT_EVIDENCE`).

### 3. Usage vs. Price Economic Growth Accounting (`UsagePriceAnalysisEngine`)
Decomposes total cost variance between baseline ($t_0$) and anomaly ($t_1$) periods using economic growth accounting:
$$\Delta \text{Cost} = Q_1 \cdot P_1 - Q_0 \cdot P_0$$
$$\Delta \text{Cost} = \Delta Q \cdot P_0 + \Delta P \cdot Q_0 + \Delta Q \cdot \Delta P$$
Where:
- $\Delta Q \cdot P_0$: **Usage Volume Effect** — expenditure change caused purely by consumption volume changes at fixed baseline unit pricing.
- $\Delta P \cdot Q_0$: **Price Rate Effect** — expenditure change caused by unit price changes (e.g., on-demand vs committed rates, tier shifts) at fixed baseline consumption.
- $\Delta Q \cdot \Delta P$: **Mix / Cross Effect** — interaction effect of simultaneous usage and pricing changes.
- **Net New Resources**: Explicitly identifies newly provisioned infrastructure where $Q_0 = 0$.

### 4. Continuous Timeline & Moving Averages (`TimeSeriesAnalysisEngine`)
- Generates a contiguous daily timeline spanning 14 days prior to the anomaly to 2 days after.
- Fills missing dates with zero spend to guarantee resilient time-series curves.
- Computes 7-day rolling moving averages to eliminate day-of-week seasonality.
- Calculates statistical variances:
  - Day-over-Day (DoD) change percentage.
  - Week-over-Week (WoW) change percentage.
  - Month-over-Month (MoM) baseline change percentage.

### 5. Resource Topology & Telemetry Correlation (`ResourceCorrelationEngine`)
- Traverses infrastructure topology (`ResourceRelationship`) to identify parent/child dependencies (e.g. EC2 instance attached to EBS volumes, VPC NAT Gateways, RDS clusters).
- Queries time-series hardware metrics (`ResourceMetric`) for CPU utilization, network traffic, and disk IOPS during the anomaly period.
- Correlates with cross-stage findings:
  - Waste Detections (`WasteDetection` from Stage 6)
  - Optimization Recommendations (`Recommendation` from Stage 8)
  - Active Alerts (`AlertInstance` from Stage 12)

### 6. Evidence-Grounded Hypothesis & Confidence Evaluator (`HypothesisEvaluator`, `ConfidenceScorer`)
- Strictly separates:
  - `FACT`: Direct mathematical observations grounded in normalized billing data.
  - `CORRELATION`: Statistically corroborated cross-signals without verified causality.
  - `HYPOTHESIS`: Plausible operational explanations generated via rule-based heuristics.
  - `VERIFIED_CAUSE`: Manually or deterministically confirmed root causes.
- Rule-based confidence scoring with penalties for contradictory metrics, missing baselines, or stale inventory.

---

## Database Models & Schema Migration

Alembic revision `011_advanced_anomaly_investigation.py` introduces 5 PostgreSQL tables:
1. `investigation_cases`: Case number (`INV-YYYY-XXXX`), anomaly ID, alert ID, lifecycle status, priority, assignee, excess cost, verified root cause, resolution notes.
2. `investigation_findings`: Structured findings (`FACT`, `CORRELATION`, `HYPOTHESIS`, `VERIFIED_CAUSE`), dimension, financial impact, contribution share, confidence score, evidence reference.
3. `investigation_notes`: Analyst collaboration comments, investigation notes, and diagnostic updates.
4. `investigation_evidence_links`: Immutable links between investigations and external entities (`billing_record`, `cloud_resource`, `waste_detection`, `recommendation`, `alert_instance`).
5. `investigation_history`: Complete audit ledger tracking every state transition, assignment, finding addition, note creation, and closure with actor attribution.

---

## Verification & Test Results

- **Automated Tests**: 55 new Stage 13 tests passed.
- **Total Repository Test Suite**: 439 passed, 0 failures, 0 regressions.
- **End-to-End Demonstration**: 15-step operational verification script (`backend/scripts/demo_stage13_investigation.py`) completed successfully.
- **Advisory Posture**: 100% read-only analysis; zero cloud mutation commands.
- **Strict Zero Float Rule**: All financial amounts use Python `Decimal` and PostgreSQL `Numeric(18, 4)`.
