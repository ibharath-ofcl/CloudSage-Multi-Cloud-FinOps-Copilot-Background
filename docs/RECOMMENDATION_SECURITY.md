# CloudSage Recommendation Security and Governance

## 1. Zero-Mutation Security Architecture

The foremost operational risk in enterprise cloud cost management is unintended downtime or data loss caused by autonomous tools executing unauthorized infrastructure deletions or resizings.

CloudSage eliminates this failure mode through architectural and permission isolation:
1. **Zero Mutating Permissions**: The cloud service principals and IAM roles assigned to CloudSage do not possess any write, update, delete, stop, or resize actions.
2. **Read-Only Telemetry Ingestion**: Permissions are limited strictly to read-only APIs:
   - AWS: `ce:GetCostAndUsage`, `ec2:DescribeInstances`, `cloudwatch:GetMetricData`
   - Azure: `Microsoft.CostManagement/query`, `Microsoft.Compute/virtualMachines/read`, `Microsoft.Insights/metrics/read`
   - GCP: `bigquery.jobs.create` (for billing exports), `compute.instances.get`, `monitoring.timeSeries.list`
3. **No Direct Execution Engine**: The Recommendation Engine has no code paths, drivers, or SDK calls capable of communicating with cloud control planes for mutation. All remediation guidance is presented as copy-pasteable CLI or Terraform scripts for human operators.

---

## 2. Role-Based Access Control (RBAC)

Access to recommendation lifecycles is governed by CloudSage's RBAC model:

| Role | Permissions & Authority |
| :--- | :--- |
| **FINOPS_ENGINEER** | View all recommendations, trigger execution runs, move to `UNDER_REVIEW`, submit feedback. |
| **FINANCE_ANALYST** | View recommendations, validate ROI, execute `ENDORSED` state transitions. |
| **ENGINEERING_MANAGER** | Formally approve (`APPROVED`), accept (`ACCEPTED`), or dismiss (`DISMISSED` with reason). |
| **SUPER_ADMIN** | Full administrative rights, re-opening dismissed proposals, configuring scoring weights. |
| **EXECUTIVE** | Read-only executive dashboard access (`/summary`, `/financial-impact`, `/priorities`). |

---

## 3. Immutable Audit Trails

Every human interaction, endorsement, approval, rejection, or feedback submission creates an append-only record in the `recommendation_history` and `audit_logs` tables. These records preserve:
- Actor email and identity.
- Pre- and post-transition statuses.
- Timestamps with timezone.
- Justifications and feedback text.
- Verified savings metrics.
