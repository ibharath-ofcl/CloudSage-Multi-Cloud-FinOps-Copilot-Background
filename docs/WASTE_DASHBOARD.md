# Cloud Infrastructure Waste Detection Dashboard

## 1. Overview

The Infrastructure Waste Detection Dashboard presents non-destructive, evidence-backed findings of cloud resources generating financial expenditure without delivering operational value.

Powered by Stage 6's multi-cloud waste detection heuristics, this interface tracks idle compute instances, unattached storage volumes, orphaned snapshots, idle public IP addresses, and over-provisioned workloads.

---

## 2. Supported Waste Heuristic Classifications

| Waste Category | Cloud Providers | Detection Logic & Telemetry Evidence | Typical Savings Impact |
|---|---|---|---|
| **IDLE_VM** | AWS, Azure, GCP | Average CPU utilization $< 2.0\%$ and network I/O $< 5\text{MB/day}$ over 14 consecutive days | \$30 – \$500/month per VM |
| **UNATTACHED_STORAGE** | AWS (EBS), Azure (Managed Disks), GCP (Persistent Disk) | Storage volume in `available` / unattached state for $> 7$ days | \$10 – \$250/month per volume |
| **ORPHANED_SNAPSHOT** | AWS (EBS snapshots), Azure (Snapshots), GCP (Disks) | Snapshot whose parent volume no longer exists, older than 90 days, without retention tags | \$5 – \$50/month per snapshot |
| **IDLE_IP** | AWS (Elastic IP), Azure (Public IP), GCP (Static IP) | Reserved public IPv4 address not associated with any active network interface | \$3.60 – \$7.20/month per IP |
| **OVERSIZED_WORKLOAD** | AWS, Azure, GCP | Peak CPU $< 20\%$ and peak RAM $< 30\%$ over 30 days; candidate for 1-tier downsize | 30% – 50% instance cost reduction |

---

## 3. Financial Impact Quantification

For every detected waste finding, CloudSage calculates:

1. **Estimated Monthly Waste ($/mo)**: Current unblended monthly run-rate cost incurred by the idle asset:
   $$\text{Monthly Waste} = \text{Unit Cost} \times \text{Provisioned Capacity} \times 730\text{ hours}$$
2. **Annualized Waste ($/yr)**: Projected annual financial loss if unremediated:
   $$\text{Annualized Waste} = 12 \times \text{Estimated Monthly Waste}$$
3. **Total Waste Percentage of Spend**:
   $$\text{Waste \%} = \left( \frac{\sum \text{Monthly Waste}}{\text{Total Monthly Cloud Spend}} \right) \times 100\%$$

---

## 4. Human Review & Lifecycle Management

In accordance with CloudSage's strict advisory-only governance principle, the dashboard provides review management without invoking cloud deletion APIs:
- **ACTIVE / OPEN**: New or existing unresolved waste finding verified by heuristic telemetry.
- **ACKNOWLEDGED**: Engineering owner has reviewed and agreed with the finding.
- **SNOOZED**: Remediation postponed with an explicit review date (e.g. disaster recovery reserve).
- **DISMISSED**: Marked as deliberate or intentional architecture with documented justification.
- **RESOLVED**: Cloud asset terminated or attached in the hyperscaler; automatically verified on subsequent discovery runs.
