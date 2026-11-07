# CloudSage: Acceptance and Success Criteria

## 1. Overview

This document specifies the objective, measurable success criteria, benchmarking methodology, and verification protocols required to validate the CloudSage Multi-Cloud FinOps platform.

---

## 2. Core Measurable Acceptance Criteria

```
+-----------------------------------------------------------------------------------------+
|                               ACCEPTANCE CRITERIA MATRIX                                |
+----+--------------------------------+-----------------------------+---------------------+
| ID | Acceptance Criterion           | Target Threshold            | Verification Method |
+----+--------------------------------+-----------------------------+---------------------+
| C1 | Seeded Waste Detection Rate    | >= 90.0% of seeded waste    | Synthetic Benchmark |
|    |                                | cases successfully flagged  | Test Suite          |
+----+--------------------------------+-----------------------------+---------------------+
| C2 | Anomaly Detection Latency      | <= 5 minutes from ingestion | End-to-End Pipeline |
|    |                                | completion to alert dispatch| Latency Clock       |
+----+--------------------------------+-----------------------------+---------------------+
| C3 | Multi-Cloud Normalization      | 100% field mapping parity   | Cross-Cloud Schema  |
|    | Parity                         | across AWS, Azure, and GCP  | Conformance Test    |
+----+--------------------------------+-----------------------------+---------------------+
| C4 | Potential Savings Calculation  | 100% mathematical precision | Automated Financial |
|    | Accuracy                       | (Zero floating-point drift) | Reconciliation Test |
+----+--------------------------------+-----------------------------+---------------------+
| C5 | Grounded AI Copilot Responses  | 100% verifiable citations   | Query Execution &   |
|    |                                | (Zero fabricated numbers)   | Row Proof Checker   |
+----+--------------------------------+-----------------------------+---------------------+
| C6 | AI Answer vs DB Calculation    | 100% numerical match with   | Automated AST & SQL |
|    | Consistency                    | underlying SQL aggregation  | Comparative Assert  |
+----+--------------------------------+-----------------------------+---------------------+
| C7 | Non-Destructive Advisory       | 0 automated destructive API | IAM Policy & Cloud  |
|    | Safety Guarantee               | calls; 100% advisory reviews| Audit Log Validator |
+----+--------------------------------+-----------------------------+---------------------+
```

---

## 3. Detailed Verification Methodologies

### 3.1 Criterion 1: Seeded Cloud Waste Detection Benchmark (>= 90%)
- **Benchmark Dataset**: A controlled synthetic dataset containing 100 known cloud infrastructure scenarios:
  - 25 Idle Virtual Machines (AWS EC2, Azure VM, GCP Compute Engine with CPU < 5%, network < 5MB/day).
  - 25 Oversized Virtual Machines (CPU < 15%, memory < 20% over 14 days).
  - 20 Unattached Storage Disks (EBS available, Azure unattached managed disk, GCP unattached PD).
  - 15 Orphaned Snapshots (age > 90 days, deleted parent volume).
  - 15 Idle Static IPs and Zero-Target Load Balancers.
- **Pass Condition**: The Waste Detection Engine must detect at least **90 out of 100 seeded cases** ($\ge 90\%$) with a false positive rate $\le 5\%$.

---

### 3.2 Criterion 2: Anomaly Detection Time-to-Alert (<= 5 Minutes)
- **Benchmark Scenario**: Ingest a billing payload containing an unexpected 300% expenditure spike in an AWS S3 or GCP BigQuery line item compared to the rolling 30-day baseline.
- **Pass Condition**:
  - The Cost Anomaly Detection Engine must identify the anomaly within **180 seconds** of data ingestion completion.
  - An alert payload (complete with root-cause attribution, service name, account ID, and Z-score) must be formatted and dispatched to notification channels in **under 300 seconds (5 minutes)** total elapsed time.

---

### 3.3 Criterion 3: Multi-Cloud Normalization Parity (100%)
- **Benchmark Scenario**: Ingest parallel billing samples from:
  - AWS Cost and Usage Report (CUR) 2.0.
  - Microsoft Azure Cost Management Export.
  - Google Cloud Platform Cloud Billing JSON Export.
- **Pass Condition**:
  - 100% of line items must successfully map into the canonical FOCUS 1.0 schema without unhandled exceptions or data truncation.
  - Dates must align to UTC ISO-8601.
  - Currencies must convert to USD without loss of precision.
  - Tags must normalize to lowercase keys with whitespace trimmed.

---

### 3.4 Criterion 4: Accurate Display of Potential Monthly & Annualized Savings
- **Benchmark Scenario**: Calculate total potential monthly savings across all active recommendations.
- **Pass Condition**:
  - The sum displayed on the Enterprise Dashboard KPI card must match the exact mathematical sum of individual active recommendation savings:
    $$\text{Total Savings}_{\text{monthly}} = \sum_{i=1}^{N} \text{Estimated Monthly Savings}_i$$
  - Calculations must use exact decimal representation (`NUMERIC(18, 4)` / Python `Decimal`) to eliminate floating-point rounding errors.

---

### 3.5 Criterion 5 & 6: Grounded AI Copilot Response & Deterministic Verification
- **Benchmark Scenario**: Submit core FinOps questions to the Copilot:
  1. *"Why did our AWS spending increase this week?"*
  2. *"Which cloud provider costs us the most?"*
  3. *"What are our top five wasteful resources?"*
  4. *"How much money can we potentially save?"*
  5. *"Which resources have no owner?"*
  6. *"Compare Azure and AWS spending."*
  7. *"Show our monthly cloud expenditure."*
- **Pass Condition**:
  - **Zero Fabrication**: The Copilot must not output any numerical cost or savings figure that is not explicitly present in the SQL query result set.
  - **100% Proof Match**: The system returns the exact SQL query executed alongside the natural language explanation.
  - **Automated Verification Harness**: An automated test compares the numbers cited in the generated answer text against the raw database query output to verify an exact numerical match.

---

### 3.6 Criterion 7: Non-Destructive Advisory Safety Guarantee
- **Pass Condition**:
  - **Codebase Audit**: Verification that the backend codebase contains zero SDK calls executing destructive cloud mutations (e.g., `boto3.client('ec2').terminate_instances()`, `compute_client.disks.delete()`).
  - **IAM Least Privilege**: Verification that CloudSage IAM role templates grant strictly read-only permissions (`ReadOnlyAccess`, `BillingAccountViewer`, `MonitoringViewer`).
  - **Audited Workflow**: All recommendation status changes (`PROPOSED` -> `UNDER_REVIEW` -> `APPROVED` -> `IMPLEMENTED`) are persisted in the immutable audit log with user identity and timestamp.
