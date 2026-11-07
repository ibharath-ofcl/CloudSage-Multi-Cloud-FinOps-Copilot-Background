# CloudSage: User Roles, Personas, and Permissions Matrix

## 1. Overview

CloudSage employs a strict Role-Based Access Control (RBAC) model augmented with Attribute-Based Access Control (ABAC) scoping. This architecture ensures that sensitive cloud financial data, governance controls, and advisory recommendations are accessed strictly according to the principle of least privilege.

---

## 2. Persona Profiles and Responsibilities

### 2.1 Super Administrator
- **Primary Goal**: Manage system availability, user provisioning, cloud credentials, security configurations, and global governance settings.
- **Key Responsibilities**:
  - Provision and deactivate user accounts and assign RBAC roles.
  - Configure cloud provider connection profiles (IAM roles, service principals, workload identity).
  - Configure global ingestion cadences, threshold parameters, and notification integrations.
  - Review comprehensive system audit trails and security logs.
  - Manage application lifecycle and configuration parameters.

### 2.2 Cloud / FinOps Engineer
- **Primary Goal**: Identify technical waste, investigate cost anomalies, design optimization recommendations, and approve technical remediation plans.
- **Key Responsibilities**:
  - Triage identified cloud waste (idle VMs, unattached disks, orphaned snapshots, idle IPs).
  - Review technical risk classifications and implementation commands for recommendations.
  - Approve or dismiss recommendations from an infrastructure safety perspective.
  - Investigate root causes for spending spikes flagged by the Anomaly Detection Engine.
  - Monitor tagging hygiene compliance and assist teams in establishing tagging standards.
  - Execute test synthetic ingestions to calibrate waste detection heuristics.

### 2.3 Finance Analyst (FP&A)
- **Primary Goal**: Monitor multi-cloud budget adherence, track historical spending trends, forecast cloud expenditures, and report financial metrics to leadership.
- **Key Responsibilities**:
  - Review total expenditure across AWS, Azure, and GCP.
  - Analyze cost allocations by Cost Center, Department, and Business Unit.
  - Monitor budget threshold alerts and variance against quarterly financial forecasts.
  - Endorse recommendations from a financial ROI perspective (e.g., verifying projected savings).
  - Utilize the AI Copilot to run ad-hoc financial comparisons and cost variance reports.
  - Export normalized financial data for corporate ERP/accounting consolidation.

### 2.4 Engineering Manager / Squad Lead
- **Primary Goal**: Maintain visibility over the cloud expenditure, waste, and tagging compliance of their specific team's applications and services.
- **Key Responsibilities**:
  - Review scoped cost dashboards filtered to their team's tags (`owner`, `project`, `application`).
  - Investigate team-level cost anomalies and unattached resources.
  - Review advisory recommendations for their services and submit feedback.
  - Verify that developers shut down non-production environments during off-hours.
  - Ensure all team-provisioned infrastructure adheres to tagging guidelines.

### 2.5 Executive / Chief Technology Officer (CTO)
- **Primary Goal**: High-level strategic oversight of multi-cloud investments, unit economics, overall waste reduction progress, and gross margin optimization.
- **Key Responsibilities**:
  - Review executive KPI summary cards (Total Spend MTD, Run-Rate, Realized Savings, Waste Ratio).
  - Monitor cross-cloud provider distribution and strategic cloud diversification.
  - Track organization-wide FinOps maturity and savings realization velocity.
  - Interrogate the AI FinOps Copilot for executive briefings and board deck preparation.

---

## 3. Granular Permissions Catalog

The CloudSage platform defines explicit, granular permissions:

```
[BILLING]
  billing:view:global       - View global billing data across all providers and accounts
  billing:view:scoped       - View billing data filtered by assigned tags/teams
  billing:ingest:trigger    - Manually trigger or schedule billing data ingestion
  billing:export            - Export raw/normalized billing data to CSV/JSON

[WASTE]
  waste:view:global         - View all detected waste items across the enterprise
  waste:view:scoped         - View waste items filtered by assigned tags/teams
  waste:dismiss             - Dismiss or snooze a waste alert with documented rationale

[ANOMALY]
  anomaly:view:global       - View all cost anomalies and root-cause analyses
  anomaly:view:scoped       - View cost anomalies scoped to assigned tags/teams
  anomaly:resolve           - Acknowledge and mark anomalies as resolved

[RECOMMENDATION]
  recommendation:view       - View optimization recommendations and potential savings
  recommendation:endorse    - Endorse recommendation from a financial feasibility perspective
  recommendation:approve    - Formally approve technical recommendation for execution
  recommendation:dismiss    - Dismiss recommendation with reason code

[COPILOT]
  copilot:query:global      - Query AI Copilot across all enterprise data
  copilot:query:scoped      - Query AI Copilot with automatic scoping filters applied

[ALERTS]
  alerts:view               - View alert notification feed and delivery history
  alerts:configure          - Create, edit, or delete alert rules and webhook destinations

[ADMINISTRATION]
  admin:users:manage        - Create, update, deactivate users and assign roles
  admin:cloud:configure     - Add, edit, or remove cloud provider integration credentials
  admin:audit:view          - Inspect system immutable audit logs
  admin:system:configure    - Modify system-wide thresholds and engine parameters
```

---

## 4. Role-Based Access Control (RBAC) Matrix

| Permission Code | Super Admin | FinOps Engineer | Finance Analyst | Engineering Manager | Executive / CTO |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `billing:view:global` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `billing:view:scoped` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `billing:ingest:trigger`| ✅ | ✅ | ❌ | ❌ | ❌ |
| `billing:export` | ✅ | ✅ | ✅ | ✅ (scoped) | ✅ |
| `waste:view:global` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `waste:view:scoped` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `waste:dismiss` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `anomaly:view:global` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `anomaly:view:scoped` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `anomaly:resolve` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `recommendation:view` | ✅ | ✅ | ✅ | ✅ (scoped) | ✅ |
| `recommendation:endorse`| ✅ | ✅ | ✅ | ❌ | ❌ |
| `recommendation:approve`| ✅ | ✅ | ❌ | ❌ | ❌ |
| `recommendation:dismiss`| ✅ | ✅ | ❌ | ❌ | ❌ |
| `copilot:query:global` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `copilot:query:scoped` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `alerts:view` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `alerts:configure` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `admin:users:manage` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `admin:cloud:configure` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `admin:audit:view` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `admin:system:configure`| ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 5. Attribute-Based Access Control (ABAC) Scoping

To maintain security and data boundaries in large enterprises:
- Users with the **Engineering Manager** role are assigned one or more scoping attributes (e.g., `department = 'Platform'`, `owner_tag IN ('checkout-team', 'payments')`).
- Any API call, dashboard view, or AI Copilot prompt initiated by an Engineering Manager automatically appends SQL filtering clauses:
  ```sql
  AND (tags->>'owner' IN ('checkout-team', 'payments') 
       OR tags->>'department' = 'Platform')
  ```
- This ensures that Engineering Managers cannot view unrelated squad budgets or sensitive infrastructure metrics.

---

## 6. Recommendation Approval Separation of Duties

To protect production stability while fostering financial collaboration:
```
           [Finance Analyst]                [Cloud / FinOps Engineer]
                   │                                     │
                   ▼                                     ▼
        Endorses Financial ROI                Reviews Architectural Risk
      (Verifies Dollar Savings)               (Verifies Downtime & Safety)
                   │                                     │
                   └──────────────────┬──────────────────┘
                                      │
                                      ▼
                           [Formally APPROVED]
                                      │
                                      ▼
                  Ready for Manual Engineering Execution
                   (Via Terraform / Cloud Console)
```
- **Finance Analysts** can flag or endorse high-ROI savings opportunities.
- Only a certified **Cloud / FinOps Engineer** or **Super Admin** possesses the authority to grant formal approval to an advisory recommendation.
