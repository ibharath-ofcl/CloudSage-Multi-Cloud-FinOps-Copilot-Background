# CloudSage Recommendation Prioritization and Scoring Methodology

## 1. Prioritization Philosophy

In an enterprise environment with thousands of cloud resources, generating an unfiltered list of optimization suggestions causes notification fatigue. CloudSage solves this by applying an objective, transparent, multi-factor scoring algorithm that balances:
1. **Financial Opportunity**: Potential dollar reduction.
2. **Evidence Confidence**: Statistical and telemetry certainty.
3. **Operational Feasibility**: Engineering effort required to implement.
4. **Operational Risk**: Likelihood of performance degradation or downtime.
5. **Urgency**: Active cost surges, anomalies, or high-severity waste.

---

## 2. Multi-Factor Scoring Formula

Every recommendation candidate receives a normalized **Composite Priority Score** ($P_{\text{score}} \in [0.0000, 1.0000]$):

$$P_{\text{score}} = \text{clamp}\Big( w_s S_{\text{norm}} + w_c C_{\text{score}} + w_e E_{\text{score}} + w_r (1 - R_{\text{score}}) + U_{\text{bonus}}, \; 0.0000, \; 1.0000 \Big)$$

Where:
- $w_s = 0.35$ (Financial Savings Weight)
- $w_c = 0.25$ (Evidence Confidence Weight)
- $w_e = 0.20$ (Implementation Effort Weight)
- $w_r = 0.20$ (Risk Mitigation Weight, using inverse risk $1 - R_{\text{score}}$)
- $U_{\text{bonus}} = 0.05$ (Urgency Bonus applied if finding originates from an active high-severity anomaly or critical waste item)

---

## 3. Factor Normalization Rules

### A. Normalized Financial Impact ($S_{\text{norm}}$)
Financial savings scale linearly up to an enterprise milestone of \$1,000/month:
$$S_{\text{norm}} = \min\left(1.0000, \; \frac{\text{Estimated Monthly Savings}}{\$1,000.00}\right)$$

### B. Implementation Feasibility Score ($E_{\text{score}}$)
Effort is scored based on the complexity of testing and execution:
| Implementation Effort | Enum Value | $E_{\text{score}}$ | Description |
| :--- | :--- | :--- | :--- |
| **Quick Win** | `QUICK_WIN` | `1.0000` | Zero risk, instantaneous (e.g. deleting unattached IP, orphaned snapshot). |
| **Low** | `LOW` | `0.8000` | Single command, non-disruptive (e.g. scheduling dev VM, buying Savings Plan). |
| **Medium** | `MEDIUM` | `0.5000` | Requires brief maintenance window (e.g. compute or DB instance downsize). |
| **High** | `HIGH` | `0.3000` | Architectural adjustment (e.g. storage tiering, multi-service rightsizing). |
| **Complex** | `COMPLEX` | `0.1000` | Multi-team cross-service migration or refactoring. |

### C. Operational Risk Score ($R_{\text{score}}$)
Risk reflects the potential for service disruption:
| Risk Level | Enum Value | $R_{\text{score}}$ | $1 - R_{\text{score}}$ (Mitigation Component) |
| :--- | :--- | :--- | :--- |
| **None** | `NONE` | `0.0500` | `0.9500` |
| **Low** | `LOW` | `0.2000` | `0.8000` |
| **Medium** | `MEDIUM` | `0.5000` | `0.5000` |
| **High** | `HIGH` | `0.8000` | `0.2000` |
| **Critical** | `CRITICAL` | `1.0000` | `0.0000` |

---

## 4. Priority Classification Tiers

The composite score maps directly to standardized priority classifications:

| Composite Score ($P_{\text{score}}$) | Priority Tier | Operational SLA / Target Turnaround |
| :--- | :--- | :--- |
| **$\ge 0.7500$** | **P1 (Critical / High Value)** | Review within 24 hours. High savings, low risk, or active surge. |
| **$0.5000 \le P < 0.7500$** | **P2 (High Priority)** | Review within current sprint (7 days). Substantial savings. |
| **$0.2500 \le P < 0.5000$** | **P3 (Medium Priority)** | Review within quarterly FinOps backlog. Moderate savings. |
| **$< 0.2500$** | **P4 (Low Priority)** | Opportunistic cleanup during maintenance intervals. |

---

## 5. Auditability and Transparency

Every recommendation stores a structured `ScoringBreakdown` payload in `evidence_summary` explaining the exact numerical contribution of each factor. This transparency builds engineer trust in CloudSage recommendations.
