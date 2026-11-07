# Multi-Cloud Ingestion API Reference

The CloudSage Ingestion REST API allows clients to upload billing exports, trigger synthetic test data generation, and inspect ingestion runs and processing telemetry.

Base URL: `/api/v1/ingestion`

---

## 1. Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/upload/aws` | Upload and process an AWS CUR CSV billing export |
| `POST` | `/upload/azure` | Upload and process an Azure Cost Management CSV export |
| `POST` | `/upload/gcp` | Upload and process a GCP BigQuery Billing JSON/CSV export |
| `POST` | `/synthetic/generate` | Generate deterministic synthetic billing datasets |
| `GET` | `/runs` | List chronological history of ingestion runs |
| `GET` | `/runs/{run_id}` | Retrieve details and error logs for a specific ingestion run |
| `GET` | `/summary` | Get aggregated ingestion metrics and totals |

---

## 2. Endpoint Details

### 2.1 Upload AWS Billing Export
Uploads and processes an AWS Cost and Usage Report CSV file.

- **URL**: `POST /upload/aws`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: CSV file (required, max 50 MB)
  - `account_id`: Optional AWS account ID override (query param)

#### Example Request (cURL)
```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/upload/aws" \
  -H "Accept: application/json" \
  -F "file=@backend/sample_data/aws/aws_cur_sample.csv"
```

#### Example Response (`200 OK`)
```json
{
  "run_id": "7f9c2d1b-3e4a-4f5b-9c8d-1e2f3a4b5c6d",
  "status": "COMPLETED",
  "total_records": 400,
  "successful_records": 400,
  "failed_records": 0,
  "duplicate_records": 0,
  "total_cost_ingested": 14250.7500,
  "duration_seconds": 0.42,
  "cloud_provider": "AWS"
}
```

---

### 2.2 Upload Azure Billing Export
Uploads and processes an Azure Cost Management CSV file.

- **URL**: `POST /upload/azure`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: CSV file (required, max 50 MB)
  - `account_id`: Optional Azure Subscription ID override (query param)

#### Example Request (cURL)
```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/upload/azure" \
  -H "Accept: application/json" \
  -F "file=@backend/sample_data/azure/azure_cost_sample.csv"
```

#### Example Response (`200 OK`)
```json
{
  "run_id": "8a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
  "status": "COMPLETED",
  "total_records": 400,
  "successful_records": 400,
  "failed_records": 0,
  "duplicate_records": 0,
  "total_cost_ingested": 11840.2000,
  "duration_seconds": 0.38,
  "cloud_provider": "AZURE"
}
```

---

### 2.3 Upload GCP Billing Export
Uploads and processes a GCP BigQuery billing export in JSON or CSV format.

- **URL**: `POST /upload/gcp`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: JSON or CSV file (required, max 50 MB)
  - `account_id`: Optional GCP Project ID override (query param)

#### Example Request (cURL)
```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/upload/gcp" \
  -H "Accept: application/json" \
  -F "file=@backend/sample_data/gcp/gcp_billing_sample.json"
```

#### Example Response (`200 OK`)
```json
{
  "run_id": "9b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e",
  "status": "COMPLETED",
  "total_records": 400,
  "successful_records": 400,
  "failed_records": 0,
  "duplicate_records": 0,
  "total_cost_ingested": 9630.5000,
  "duration_seconds": 0.35,
  "cloud_provider": "GCP"
}
```

---

### 2.4 Generate Synthetic Datasets
Generates deterministic synthetic billing files across AWS, Azure, and GCP.

- **URL**: `POST /synthetic/generate`
- **Content-Type**: `application/json`

#### Request Body
```json
{
  "record_count": 1200,
  "output_dir": "backend/sample_data",
  "seed": 42
}
```

#### Example Response (`200 OK`)
```json
{
  "status": "generated",
  "total_records_generated": 1200,
  "files_created": {
    "AWS": "backend/sample_data/aws/aws_cur_sample.csv",
    "AZURE": "backend/sample_data/azure/azure_cost_sample.csv",
    "GCP": "backend/sample_data/gcp/gcp_billing_sample.json"
  },
  "scenario_distribution": {
    "normal_expenditure": 480,
    "idle_vm_waste": 180,
    "unattached_storage": 180,
    "oversized_compute": 120,
    "cost_spikes": 60,
    "poorly_tagged": 180
  },
  "generation_timestamp": "2026-11-07T12:00:00"
}
```

---

### 2.5 List Ingestion Runs
Lists past ingestion executions ordered by start time descending.

- **URL**: `GET /runs`
- **Query Parameters**:
  - `limit`: Number of records to return (1-200, default 50)
  - `offset`: Pagination offset (default 0)
  - `provider`: Optional filter (`AWS`, `AZURE`, `GCP`)

#### Example Response (`200 OK`)
```json
[
  {
    "id": "7f9c2d1b-3e4a-4f5b-9c8d-1e2f3a4b5c6d",
    "source_file": "aws_cur_sample.csv",
    "cloud_provider": "AWS",
    "status": "COMPLETED",
    "total_records": 400,
    "successful_records": 400,
    "failed_records": 0,
    "duplicate_records": 0,
    "total_cost": 14250.7500,
    "duration_seconds": 0.42,
    "started_at": "2026-11-07T12:30:00Z",
    "completed_at": "2026-11-07T12:30:01Z",
    "error_details": []
  }
]
```

---

### 2.6 Get Ingestion Summary
Returns global ingestion totals across all cloud providers.

- **URL**: `GET /summary`

#### Example Response (`200 OK`)
```json
{
  "total_runs": 3,
  "completed_runs": 3,
  "failed_runs": 0,
  "total_records_ingested": 1200,
  "total_cost_ingested": 35721.4500,
  "provider_breakdown": {
    "AWS": { "records": 400, "cost": 14250.7500 },
    "AZURE": { "records": 400, "cost": 11840.2000 },
    "GCP": { "records": 400, "cost": 9630.5000 }
  }
}
```

---

## 3. Python SDK / Client Example

```python
import requests

BASE_URL = "http://localhost:8000/api/v1/ingestion"

# 1. Ingest an AWS CUR export
with open("backend/sample_data/aws/aws_cur_sample.csv", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/upload/aws",
        files={"file": ("aws_cur_sample.csv", f, "text/csv")}
    )
    result = response.json()
    print(f"Run {result['run_id']}: {result['successful_records']} records ingested.")

# 2. Query ingestion summary
summary = requests.get(f"{BASE_URL}/summary").json()
print(f"Total Cloud Expenditure Ingested: ${summary['total_cost_ingested']:,.2f}")
```

---

## 4. Error Codes & Handling

| HTTP Status | Reason | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | Unsupported file extension | Uploaded file is not `.csv`, `.json`, or `.jsonl` |
| `400 Bad Request` | File size exceeded | Uploaded file exceeds the 50 MB threshold |
| `404 Not Found` | Run not found | Requested `run_id` does not exist |
| `422 Unprocessable Entity`| Ingestion parse failure | Dataset structure could not be parsed by the adapter |
| `500 Internal Error` | Database error | Unhandled database or system exception |
