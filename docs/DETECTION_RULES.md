# CloudSage Multi-Cloud Waste Detection Rules & Heuristics Catalog

This document details the complete heuristic catalog for all 7 specialized detectors implemented in CloudSage Stage 6.

---

## 1. Detector Heuristic Matrix

| Detector ID | Waste Category | Target Resources | Observation Window | Core Thresholds | Primary Safeguards |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `idle_compute_detector` | `IDLE_COMPUTE` | AWS EC2, Azure VMs, GCP Compute Engine | 7 Days continuous | Avg CPU < 5%, Peak CPU < 15% | High Network I/O (>50MB/day) indicates proxy/gateway $\rightarrow$ CLEAN |
| `oversized_compute_detector` | `OVERSIZED_COMPUTE` | AWS EC2, Azure VMs, GCP Compute Engine | 14 Days continuous | Avg CPU < 20%, Peak CPU < 50% | Conservative single-tier downsize (50% savings); Memory burst checks |
| `unattached_storage_detector` | `UNATTACHED_STORAGE` | AWS EBS, Azure Managed Disks, GCP Persistent Disks | 3 Days post-unattachment | Status == available/unattached & 0 `ATTACHED_TO` edges | Grace period (<3 days) $\rightarrow$ CLEAN |
| `orphaned_snapshots_detector` | `ORPHANED_SNAPSHOT` | AWS EBS Snapshots, Azure Disk Snapshots, GCP Snapshots | 30 Days minimum age | Age > 30 days & parent volume deleted/missing | Retention/compliance tags (`compliance`, `retention`, `donotdelete`) $\rightarrow$ CLEAN |
| `underutilized_database_detector` | `UNDERUTILIZED_DATABASE` | AWS RDS, Azure SQL, GCP Cloud SQL | 7 Days continuous | Avg connections < 2 & CPU < 10% | Mandatory connection telemetry; never flag on low CPU alone |
| `unused_network_resources_detector` | `UNUSED_NETWORK` / `IDLE_IP` / `ZERO_TARGET_LB` | Elastic IPs, Azure Public IPs, Cloud NAT, ALBs, NLBs | 7 Days / 1 Day grace | Unassociated IP or LB target count == 0 | Gateway/VPN associations verified before flagging |
| `billing_based_waste_detector` | `BILLING_BASED_WASTE` | Any Cloud Resource | 14 Days stale / 24x7 non-prod | Ongoing charges on stale resource; 24x7 running dev/test | Prod environment tag exemption for 24x7 scheduling |

---

## 2. In-Depth Detector Specifications

### 2.1 Idle Compute Instance Detector (`idle_compute_detector`)
- **Objective**: Pinpoint virtual machines that are running and generating hourly compute billing, yet performing negligible processing.
- **Provider Resource Types**:
  - AWS: `ec2:instance`, `AWS::EC2::Instance`
  - Azure: `Microsoft.Compute/virtualMachines`, `azure:virtual_machines`
  - GCP: `compute.googleapis.com/Instance`, `gcp:compute_engine`
- **Evaluation Criteria**:
  $$\text{Average CPU} < 5.0\% \quad \text{AND} \quad \text{Peak CPU} < 15.0\% \quad \text{over} \ge 7 \text{ days}$$
- **Conflicting Signals Safeguard**:
  If $\text{Average Network I/O} > 50.0\text{ MB/day}$, the instance is recognized as an active ingress controller, NAT proxy, or network bridge, and the detector yields `CLEAN`.
- **Insufficient Data Safeguard**:
  If the telemetry span is $< 2.5$ days or CPU metrics are entirely absent, the detector yields `INSUFFICIENT_DATA`.

---

### 2.2 Oversized Compute Instance Detector (`oversized_compute_detector`)
- **Objective**: Flag instances whose capacity significantly exceeds actual operational demands over a 14-day observation window.
- **Evaluation Criteria**:
  $$\text{Average CPU} < 20.0\% \quad \text{AND} \quad \text{Peak CPU} < 50.0\% \quad \text{over} \ge 14 \text{ days}$$
- **Savings Methodology**:
  Conservative 50% single-tier downsize ratio ($0.50 \times \text{monthly\_cost}$). Never speculates multi-tier jumps without full workload benchmarking.

---

### 2.3 Unattached Block Storage Detector (`unattached_storage_detector`)
- **Objective**: Reclaim unattached persistent volumes orphaned following VM terminations or migrations.
- **Provider Resource Types**:
  - AWS: `ec2:volume`, `aws:ec2:volume`
  - Azure: `Microsoft.Compute/disks`, `azure:managed_disks`
  - GCP: `compute.googleapis.com/Disk`, `gcp:compute_engine`
- **Evaluation Criteria**:
  - Resource status in `['available', 'unattached', 'ready']`.
  - Zero incoming `ATTACHED_TO` edges in the Stage 5 topological relationship graph.
  - Resource age or unattached duration $> 3$ days.
- **Savings Methodology**:
  100% of the provisioned volume expenditure ($1.00 \times \text{monthly\_cost}$ or $0.08 \times \text{size\_gb}$).

---

### 2.4 Orphaned Snapshot Detector (`orphaned_snapshots_detector`)
- **Objective**: Stop persistent storage accumulation from forgotten manual or legacy automated backups.
- **Evaluation Criteria**:
  - Age $> 30$ days.
  - Parent source volume relationship (`SNAPSHOT_OF`) is missing or confirmed deleted in inventory.
- **Compliance Safeguard**:
  If tags contain `compliance`, `retention`, `donotdelete`, `archive`, or `backup_policy`, the snapshot is deemed an intentional regulatory archival copy and yields `CLEAN`.

---

### 2.5 Underutilized Managed Database Detector (`underutilized_database_detector`)
- **Objective**: Identify expensive idle relational database instances (AWS RDS, Azure SQL, GCP Cloud SQL).
- **Evaluation Criteria**:
  $$\text{Average Active Connections} < 2.0 \quad \text{AND} \quad \text{Average CPU} < 10.0\% \quad \text{over} \ge 7 \text{ days}$$
- **Connection Metric Mandate**:
  Low CPU alone must **NEVER** trigger an underutilized database finding. If client connection telemetry is unavailable, the detector strictly outputs `INSUFFICIENT_DATA`.

---

### 2.6 Unused Network Resources Detector (`unused_network_resources_detector`)
- **Objective**: Identify public IP addresses and empty load balancers incurring hourly surcharges.
- **Public IPs**:
  - Evaluates static IPv4 addresses lacking association with an active network interface or instance (`monthly_cost` $\approx \$3.65/\text{month}$).
- **Load Balancers**:
  - Identifies ALBs/NLBs with 0 registered targets or 0 healthy backend pool members (`monthly_cost` $\approx \$18.00-\$25.00/\text{month}$).

---

### 2.7 Billing-Based Waste Detector (`billing_based_waste_detector`)
- **Objective**: Catch residual spending on untracked or stale assets and 24x7 running development infrastructure.
- **Stale Asset Heuristic**:
  Resources generating ongoing billing records whose inventory record has not been confirmed for $> 14$ days (`last_seen_at` $> 14$ days ago).
- **24x7 Non-Production Compute Heuristic**:
  Compute instances tagged with `environment: dev`, `staging`, or `test` running continuously 24x7 without scheduled overnight or weekend shutoff policies.
