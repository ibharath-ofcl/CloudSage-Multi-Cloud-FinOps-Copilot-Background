# Advisory Optimization Recommendation Dashboard

## 1. Overview

The Recommendation Dashboard bridges the gap between waste identification and engineering execution. It surfaces prioritized, actionable optimization advisories scored by potential financial yield, implementation effort, and operational risk.

CloudSage adheres strictly to the **human-in-the-loop review model**: recommendations are non-destructive advisories that generate step-by-step remediation plans, CLI scripts, and Terraform guidance without executing blind mutations against production infrastructure.

---

## 2. Multi-Factor Scoring Architecture

Recommendations are ordered using CloudSage's composite multi-factor scoring formula:

$$\text{Score} = w_s \cdot S_{\text{savings}} + w_e \cdot (1 - E_{\text{effort}}) + w_r \cdot (1 - R_{\text{risk}}) + w_u \cdot U_{\text{urgency}}$$

Where:
- $S_{\text{savings}}$: Normalized monetary savings yield ($0.0 - 1.0$).
- $E_{\text{effort}}$: Implementation complexity ($0.2$ for Quick Win, $0.4$ for Low, $0.6$ for Medium, $0.9$ for Complex).
- $R_{\text{risk}}$: Risk of service disruption or performance degradation ($0.1$ for Low, $0.5$ for Medium, $0.9$ for Critical).
- $U_{\text{urgency}}$: Waste duration or active anomaly linkage ($0.0 - 1.0$).

---

## 3. Priority Tiers & Effort Breakdown

| Priority Tier | Target Criteria | Effort Tier | Typical Actions |
|---|---|---|---|
| **P1 – Critical** | High monthly savings ($>\$100/\text{mo}$), Quick Win / Low effort, Low risk | QUICK_WIN, LOW | Delete unattached EBS volume, release idle Elastic IP, delete 90-day orphaned snapshot |
| **P2 – High** | Moderate-to-high savings ($>\$50/\text{mo}$), Low-to-Medium effort | LOW, MEDIUM | Downsize over-provisioned EC2 instance, adjust storage tier from Standard to Coldline/Archive |
| **P3 – Medium** | Moderate savings ($<\$50/\text{mo}$), Medium effort | MEDIUM | Consolidate under-utilized database clusters, migrate to Graviton/ARM architectures |
| **P4 – Low** | Low savings ($<\$10/\text{mo}$) or Complex architectural effort | COMPLEX | Multi-region architectural redesign, reserved instance commitment rebalancing |

---

## 4. Remediation Guidance & Governance Workflow

Every recommendation in the dashboard provides an expandable review drawer containing:
1. **Action Headline**: Clean, concise operational instruction (e.g. "Downsize instance from m5.2xlarge to m5.large").
2. **Financial Breakdown**: Current monthly cost, projected monthly cost, and estimated annual savings.
3. **Evidence Telemetry**: 14-day CPU, memory, and network utilization charts justifying the change.
4. **Remediation Script**: Auto-generated CLI snippet (AWS CLI, Azure CLI, gcloud) or Terraform block.
5. **Rollback Plan**: Clear instructions on how to revert changes if unexpected application bottlenecks occur.
6. **Governance Actions**: Buttons to **Endorse**, **Approve**, or **Dismiss** with review comments.
