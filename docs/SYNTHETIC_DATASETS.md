# Synthetic Datasets & Seeded FinOps Scenarios

## 1. Overview & Objective

To enable realistic end-to-end development, testing, and demonstrations without incurring external cloud provider costs or requiring live billing credentials, CloudSage provides a deterministic **Synthetic Billing Dataset Generator** (`backend/app/ingestion/synthetic/`).

The generator constructs 100% syntactically authentic billing files for:
1. **AWS Cost and Usage Report (CUR CSV)**
2. **Microsoft Azure Cost Management Export (CSV)**
3. **Google Cloud Platform BigQuery Billing Export (JSON)**

All generated data conforms strictly to real provider schemas, headers, date formats, and nested structures.

---

## 2. Seeded FinOps Scenarios

The synthetic generator embeds 6 distinct operational scenarios designed to test downstream waste detection, anomaly detection, and recommendation algorithms:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Synthetic Dataset Scenario Mix                       │
├────────────────────────┬───────────┬───────────────────────────────────┤
│ Scenario               │ Weight    │ Seeded FinOps Characteristics     │
├────────────────────────┼───────────┼───────────────────────────────────┤
│ A. Normal Expenditure  │ 40%       │ Standard production instances,    │
│                        │           │ active databases, steady workloads│
│ B. Idle VM Waste       │ 15%       │ Running compute instances with    │
│                        │           │ 24/7 charges but low CPU metrics  │
│ C. Unattached Storage  │ 15%       │ Disks & volumes incurring billing │
│                        │           │ without an attached compute ID    │
│ D. Oversized Compute   │ 10%       │ Large/metal instances operating   │
│                        │           │ with < 10% peak memory/CPU        │
│ E. Cost Spike Anomalies│ 5%        │ 3x - 10x sudden cost jumps on     │
│                        │           │ specific service SKUs             │
│ F. Poorly Tagged Cost  │ 15%       │ Resources with missing or empty   │
│                        │           │ owner, env, and project tags      │
└────────────────────────┴───────────┴───────────────────────────────────┘
```

### Scenario Details

#### Scenario A: Normal Operating Expenditure (40%)
- Baseline compute, storage, and networking costs.
- Fully tagged with `Environment=production`, `Owner=devops@enterprise.com`, and `CostCenter=CC-1001`.
- Clean 30-day continuous usage.

#### Scenario B: Idle Virtual Machines (15%)
- Persistent compute instances (`m5.2xlarge`, `Standard_D8s_v5`, `e2-standard-8`) running continuously (720 hrs/mo).
- Tagged with `Status=idle` or `Workload=dev-test`.
- Designed for downstream idle detection tests.

#### Scenario C: Unattached Storage Disks (15%)
- Detached volumes (`gp3`, `Premium_LRS`, `pd-ssd`) accumulating recurring hourly/monthly costs.
- Identifiers include `vol-orphaned-*`, `disk-unattached-*`.
- Resource tags lack attached instance associations.

#### Scenario D: Oversized Compute Instances (10%)
- High-end instance types (`c5.9xlarge`, `Standard_F32s_v2`, `c2-standard-30`) deployed for light workloads.
- Monthly spend exceeding \$1,000+ per node.
- Designed to trigger rightsizing recommendations.

#### Scenario E: Cost Spike Anomalies (5%)
- Sudden expenditure spikes (e.g., massive BigQuery queries, unexpected NAT gateway egress, unmonitored Lambda invocations).
- Cost multiplier: 3.5x to 10x standard baseline.
- Designed to trigger statistical anomaly detection algorithms.

#### Scenario F: Poorly Tagged / Unowned Resources (15%)
- Resources with completely empty tags `{}` or missing critical keys (`owner`, `environment`, `project`).
- Designed for tagging hygiene analysis and unallocated cost reporting.

---

## 3. Pre-Generated Sample Datasets

The repository includes pre-generated sample datasets under `backend/sample_data/`:

| Provider | File Path | Format | Records | File Size |
| :--- | :--- | :--- | :--- | :--- |
| **AWS** | `backend/sample_data/aws/aws_cur_sample.csv` | CSV | 400 | ~103 KB |
| **Azure** | `backend/sample_data/azure/azure_cost_sample.csv` | CSV | 400 | ~156 KB |
| **GCP** | `backend/sample_data/gcp/gcp_billing_sample.json` | JSON | 400 | ~503 KB |
| **Total**| - | - | **1,200** | **~762 KB** |

---

## 4. How to Generate New Synthetic Data

### Method 1: Via REST API
You can trigger generation of custom dataset sizes via the API:

```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/synthetic/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "record_count": 3000,
    "output_dir": "backend/sample_data",
    "seed": 42
  }'
```

### Method 2: Via Python CLI / Script
```python
from backend.app.ingestion.synthetic.datasets import export_sample_datasets

# Generate 1,500 records (500 per provider) with deterministic seed
file_paths = export_sample_datasets(
    output_dir="backend/sample_data",
    total_records=1500,
    seed=42
)
print("Files generated:", file_paths)
```

---

## 5. Dataset Validation & Verification

All synthetic datasets are verified by automated tests in `backend/tests/test_synthetic_generator.py`:
- Checks volume requirements ($\ge 1,000$ records across all providers).
- Verifies deterministic reproducibility under fixed seeds.
- Asserts that all 6 FinOps scenarios are represented in the generated files.
- Asserts that generated files are successfully parsed and validated by their respective cloud adapters.
