# CloudSage Recommendation Correlation and Anti-Double-Counting

## 1. The Challenge of Double-Counting in FinOps

In complex multi-cloud environments, a single inefficient cloud resource can trigger multiple overlapping findings across different detection engines:
- **Example**: An idle development virtual machine (`i-0a1b2c3d`) may be flagged by:
  1. Stage 6 Waste Detection as an `IDLE_VM` (recommending `TERMINATE`, saving \$200/mo).
  2. Stage 6 Waste Detection as `OVERSIZED_COMPUTE` (recommending `RIGHTSIZE`, saving \$100/mo).
  3. Stage 6 Waste Detection as `CONTINUOUS_NON_PROD` (recommending `SCHEDULE_SHUTDOWN`, saving \$140/mo).
  4. Stage 7 Anomaly Detection as a `RESOURCE_SPIKE` due to a sudden logging burst.

If these findings were presented naively as independent recommendations, the dashboard would report total savings of \$440/month on an instance that only costs \$200/month. This represents **destructive double-counting** that undermines executive credibility.

---

## 2. Deterministic Recommendation Keys

To prevent duplicate proposals and ensure idempotent run execution, CloudSage generates a deterministic SHA-256 deduplication key for every candidate:

$$\text{Raw Key} = \text{Provider} \mathbin{\Vert} \text{Account ID} \mathbin{\Vert} \text{Resource ID} \mathbin{\Vert} \text{Action Type} \mathbin{\Vert} \text{Strategy ID}$$
$$\text{recommendation\_key} = \text{"rec\_"} + \text{SHA256}(\text{Raw Key})[0:28]$$

This key guarantees that subsequent recommendation runs update existing open proposals rather than duplicating them.

---

## 3. Action Precedence Hierarchy

When multiple distinct recommendation strategies target the same cloud resource, CloudSage resolves the conflict using a strict **Action Hierarchy Ranking**:

| Action Enum | Hierarchy Rank | Behavior & Precedence Rule |
| :--- | :--- | :--- |
| `TERMINATE` | **100** | **Highest Precedence**: Decommissioning completely eliminates the resource; suppresses rightsizing, scheduling, and tiering. |
| `RELEASE_IP` | **100** | Releasing unattached IP suppresses subordinate networking actions. |
| `CLEANUP_UNATTACHED` | **90** | Volume deletion suppresses volume resizing or snapshotting. |
| `DELETE_SNAPSHOT` | **85** | Deleting snapshot suppresses snapshot archival. |
| `RIGHTSIZE` | **70** | Downsizing instance suppresses business-hour scheduling unless complementary. |
| `PAUSE` | **65** | Pausing non-prod DB clusters takes precedence over scheduling. |
| `SCHEDULE_SHUTDOWN` | **60** | Applied when resource must remain intact but can be scheduled off. |
| `CONVERT_STORAGE_TIER`| **50** | Storage lifecycle rule applied to preserved buckets. |
| `PURCHASE_SAVINGS_PLAN`| **40** | Account/fleet level commitment discount. |
| `RESERVE_CAPACITY` | **40** | Account/fleet level reservation. |
| `INVESTIGATE_ANOMALY` | **30** | Investigation advisory; complements other actions. |

---

## 4. Conflict Resolution & Suppression Pipeline

During run execution in `RecommendationEngine.execute_run()`:
1. All candidates are grouped by `resource_id`.
2. Within each group:
   - Candidates are sorted by `(Action Hierarchy Rank, Priority Score, Monthly Savings)`.
   - The highest-ranking candidate becomes the **Active Recommendation**.
   - Subordinate candidates are marked as **Suppressed**.
3. Suppressed candidates are recorded in the `recommendation_runs.error_details` audit log with clear justification:
   > *"Anti-double-counting: TERMINATE on i-0a1b2c3d supersedes RIGHTSIZE ($100.00/mo savings suppressed)."*
4. Total run savings reflect **only active, non-suppressed recommendations**.
