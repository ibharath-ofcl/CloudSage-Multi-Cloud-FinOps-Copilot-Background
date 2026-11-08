# Stage 11 Security, Governance & Risk Architecture

**Project:** CloudSage – Multi-Cloud FinOps Copilot  
**Stage:** Stage 11 – Enterprise Recommendation & Waste Management Workspace  
**Status:** Implemented & Verified  

---

## 1. Executive Summary

Stage 11 establishes a robust enterprise governance boundary that allows organizations to operationalize cost recommendations and waste triage safely.

CloudSage operates on the foundational principle of **Advisory-Only Cloud Operations**: under no circumstances does CloudSage possess write, mutate, terminate, or delete permissions in customer cloud environments. All actions resulting in infrastructure changes are handed off to human operators or external CI/CD pipelines via generated playbooks.

---

## 2. Advisory-Only Architecture & Non-Mutating Boundary

```
┌────────────────────────────────────────────────────────┐
│                   CloudSage Platform                   │
│                                                        │
│  - Cost Analytics & Ingestion (Read-Only)              │
│  - Anomaly & Waste Detection (Read-Only)               │
│  - Advisory Recommendations (Read-Only)                │
│  - Playbook Code Generator (Static Synthesis)          │
└───────────────────────────┬────────────────────────────┘
                            │
               [ AIR-GAPPED BOUNDARY ]
        NO WRITE/MUTATE CREDENTIALS TO CLOUD
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│            Human Operator / GitOps Pipeline            │
│  1. Reviews Playbook (.tf, .sh, .bicep)                │
│  2. Validates in Staging Environment                   │
│  3. Submits Pull Request / Applies via IAM credentials │
└────────────────────────────────────────────────────────┘
```

### Absolute Constraints:
- **No Direct Cloud Mutation:** CloudSage has zero cloud provider mutating SDK calls (`boto3.client('ec2').terminate_instances()` is banned from the application runtime).
- **No Cloud Write Credentials:** The ingestion and discovery engines operate with strictly read-only IAM policies (e.g., `arn:aws:iam::aws:policy/ReadOnlyAccess`).
- **Zero Autonomous Execution:** No scheduled cron, background worker, or copilot agent can trigger infrastructure actions without human intervention.

---

## 3. Parameter Sanitization & Injection Defense

Generated CLI scripts and IaC templates accept user-controlled and provider-sourced identifiers (such as instance IDs, volume ARNs, resource names).

To eliminate shell command injection and template breakout risks:
1. All identifiers are passed through `sanitize_identifier`:
   ```python
   def sanitize_identifier(identifier: str) -> str:
       # Strips shell metacharacters (; & | ` $ < > ( ) \ etc.)
       return re.sub(r"[^a-zA-Z0-9_\-\.:/]", "", str(identifier))
   ```
2. Generated Bash scripts enforce strict shell flags: `set -euo pipefail`.
3. Parameter values in Terraform are output as typed string literals without string interpolation formatting.

---

## 4. Financial Integrity & Zero Float Rule

Financial miscalculations erode trust in FinOps tooling. Stage 11 strictly enforces:
- **Python `Decimal` Everywhere:** No `float` types for currency or cost calculations.
- **Database `Numeric(18, 4)`:** Four decimal places of precision maintained across all monetary tables (`recommendations`, `waste_detections`, `recommendation_savings_overrides`).
- **Mathematical Immutability:** Overrides preserve the original calculated savings for audit traceability.

---

## 5. Anti-Double-Counting Taxonomy

CloudSage maintains four mathematically disjoint financial categories:

| Category | Definition | Channel Isolation |
|---|---|---|
| **Baseline Spend** | Actual incurred cloud billing cost. | Reconciled from normalized billing line items. |
| **Avoidable Waste** | Unutilized or orphaned asset expenditure. | Independent waste detection rules. |
| **Potential Savings** | Realistic forward-looking reductions. | Algorithmic & human-approved recommendations. |
| **Realized Savings** | Measured post-remediation expenditure delta. | Validated via historical billing comparison. |

These values are never blended, added together, or conflated in executive or operational reporting.
