# Investigation Workspace: User Guide & FinOps Workflows

## Overview

The CloudSage **Investigation Workspace** provides a collaborative, evidence-grounded command center for diagnosing unexpected cloud spending spikes across AWS, Microsoft Azure, and Google Cloud Platform.

Located at `/investigations` in the CloudSage web interface, the workspace bridges the gap between raw statistical cost anomaly alerts (Stage 7 & Stage 12) and actionable engineering remediation (Stage 8 & Stage 11).

---

## Workspace Navigation & Views

### 1. Investigations Overview (`/investigations`)
The overview screen aggregates all active, triaged, and resolved investigation cases across cloud providers.

#### KPI Summary Header
- **Total Investigations**: Aggregate case volume across historical telemetry.
- **Open Cases**: Number of active investigations requiring engineering triage.
- **Critical Severity**: High-impact cases with substantial excess expenditure.
- **Unassigned Queue**: Cases awaiting ownership attribution.
- **Root Cause Identified**: Cases where the exact technical cause has been isolated and confirmed.
- **Investigated Excess Spend**: Cumulative financial sum of analyzed cost anomalies (in USD).
- **Average Case Age**: Mean time from anomaly detection to triage and resolution (in hours).

#### Multi-Dimensional Case Filtering
- **Cloud Provider**: Filter across AWS, Azure, GCP, or All Providers.
- **Lifecycle Status**: Filter by `NEW`, `ASSIGNED`, `INVESTIGATING`, `ROOT_CAUSE_IDENTIFIED`, `ACTION_RECOMMENDED`, `RESOLVED`, `CLOSED`.
- **Priority Tier**: Filter by `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
- **Assignee**: Filter by specific team member or view the `unassigned` queue.
- **Search Bar**: Substring match across Case Number (`INV-2026-0001`), Title, Service, or Resource ID.

---

### 2. Deep-Dive Investigation Detail (`/investigations/:investigationId`)

Clicking on any case opens the full interactive investigation cockpit, organized into four specialized analytical tabs:

#### Tab 1: Overview & Findings
- **Executive Summary Card**: Financial variance overview (Actual vs. Expected spend, Estimated Excess Cost, Cloud Provider, Account, Service, and Region).
- **Auto-Generated Evidence Findings**:
  - `[FACT]`: Direct empirical observations from normalized billing records (e.g., "$2,584.00 excess spend in us-east-1").
  - `[CORRELATION]`: Statistically linked cross-stage events (e.g., "Correlated with active Waste Detection: oversized_compute_detector").
  - `[HYPOTHESIS]`: Algorithmic explanations (e.g., "Hypothesis: Consumption Volume Increase driving 71.8% of excess").
  - `[VERIFIED_CAUSE]`: Analyst-confirmed root causes.
- **Confidence Badges**: Clear visual badges (`HIGH`, `MEDIUM`, `LOW`) indicating evidence strength.
- **Custom Finding Drawer**: Allows analysts to add verified technical causes with evidence references, financial impact, and recommended next steps.

#### Tab 2: Multi-Dimensional Breakdown & Pareto Drivers
- **10-Dimensional Decomposition Selector**: Switch between `PROVIDER`, `ACCOUNT`, `REGION`, `SERVICE`, `RESOURCE_ID`, `SKU`, `ENVIRONMENT`, `OWNER`, `COST_CENTER`, `BILLING_TAGS`.
- **Dominant Dimension Badge**: Highlights the dimension with highest concentration of unexpected spend.
- **Pareto 80/20 Table**:
  - Ranks contributors in descending order of financial impact.
  - Visual indicator separating primary 80% cost drivers from long-tail variations.
  - Cumulative contribution progress bar.
- **Usage vs. Price Growth Accounting**:
  - Three-way decomposition breakdown ($\Delta Q \cdot P_0$ vs $\Delta P \cdot Q_0$ vs $\Delta Q \cdot \Delta P$).
  - Explanatory callouts distinguishing volume surges from pricing/tier shifts.

#### Tab 3: Timeline & Resource Topology
- **Continuous 17-Day Spend Timeline**:
  - Actual daily spend vs. 7-day rolling moving average.
  - Highlighted anomaly period marker.
  - DoD, WoW, and MoM variance metrics.
- **Resource Topology Map**:
  - Primary impacted resource details and discovery status.
  - Parent/child connected infrastructure (e.g., EC2 instance -> attached EBS gp3 volumes -> VPC NAT Gateway).
  - CloudWatch / Azure Monitor / GCP Cloud Monitoring utilization graphs (CPU %, Network bytes, Disk IOPS).
- **Correlated Cross-Stage Signals**:
  - Direct links to associated Stage 6 Waste Detections.
  - Direct links to Stage 8 Advisory Recommendations.
  - Triggering Stage 12 Alert Instances.

#### Tab 4: Collaboration Notes & Audit History
- **Analyst Collaboration Feed**: Chronological log of team diagnostic notes and architectural insights.
- **Add Diagnostic Note**: Fast comment editor for team synchronization during active incident triage.
- **Immutable State Machine Ledger**:
  - Full audit trail of every status transition (`NEW` $\to$ `INVESTIGATING` $\to$ `ROOT_CAUSE_IDENTIFIED` $\to$ `RESOLVED`).
  - Actor identity, timestamp, previous status, new status, and justification notes.

---

## Case Lifecycle Workflows

```
   [ NEW ]
      |
      v
 [ ASSIGNED ]  <--------------------------+
      |                                   |
      v                                   |
[ INVESTIGATING ]                         |
      |                                   |  Reopen
      v                                   |
[ ROOT_CAUSE_IDENTIFIED ]                 |
      |                                   |
      v                                   |
[ ACTION_RECOMMENDED ]                    |
      |                                   |
      v                                   |
  [ RESOLVED ] ---------------------------+
      |
      v
   [ CLOSED ]
```

### Transition Governance Rules
1. **Assignment**: Assigning an unassigned case automatically transitions its status from `NEW` to `ASSIGNED`.
2. **Mandatory Root Cause Justification**: Transitioning to `ROOT_CAUSE_IDENTIFIED` or `RESOLVED` requires a verified root cause explanation string.
3. **Audit Ledger Logging**: Every lifecycle modification generates an immutable `AuditLog` entry and `InvestigationHistory` record with server-side authenticated identity derivation.
4. **Advisory Remediation Hand-off**: Reaching `ACTION_RECOMMENDED` generates links to CloudSage Recommendation Workspace playbooks. CloudSage never executes destructive changes automatically.
