# Resource Inventory & Intelligence REST API Reference

The Inventory API provides 13 REST endpoints registered under `/api/v1/inventory`.

## Endpoints Summary

| Method | Endpoint Path | Description | Response Schema |
|:---|:---|:---|:---|
| `POST` | `/api/v1/inventory/import/aws` | Upload and ingest AWS Config/CLI inventory export JSON/CSV | `InventoryImportResponse` |
| `POST` | `/api/v1/inventory/import/azure` | Upload and ingest Azure Resource Graph export JSON/CSV | `InventoryImportResponse` |
| `POST` | `/api/v1/inventory/import/gcp` | Upload and ingest GCP Cloud Asset Inventory export JSON/CSV | `InventoryImportResponse` |
| `POST` | `/api/v1/inventory/sync` | Trigger Mode B read-only live discovery query | `InventoryImportResponse` |
| `GET` | `/api/v1/inventory/resources` | List multi-cloud resources with rich filters & pagination | `CloudResourceListResponse` |
| `GET` | `/api/v1/inventory/resources/{resource_id}` | Detailed asset record with metadata, cost, and topology | `CloudResourceDetailResponse` |
| `GET` | `/api/v1/inventory/resources/{resource_id}/relationships`| Outbound and inbound directional relationships | `List[ResourceRelationshipResponse]` |
| `GET` | `/api/v1/inventory/summary` | Global multi-cloud inventory summary & distribution | `InventorySummaryResponse` |
| `GET` | `/api/v1/inventory/sync-runs` | Audit log of inventory discovery executions | `List[InventorySyncRunResponse]` |
| `GET` | `/api/v1/inventory/sync-runs/{run_id}` | Specific discovery run audit record | `InventorySyncRunResponse` |
| `GET` | `/api/v1/inventory/quality-report` | Latest quality assessment or on-demand fresh audit | `InventoryQualityReportResponse` |
| `GET` | `/api/v1/inventory/coverage` | Ledger cost reconciliation coverage metrics | `InventoryCoverageResponse` |
| `GET` | `/api/v1/inventory/cost-correlation` | Single resource financial correlation and billing ties | `BillingCorrelationResponse` |

---

## Detailed Endpoint Specifications

### 1. File Upload Ingestion
- **Route**: `POST /api/v1/inventory/import/{provider}` (`aws`, `azure`, `gcp`)
- **Headers**: `Content-Type: multipart/form-data`
- **Body**: `file` (max 50 MB, `.json`, `.jsonl`, `.csv`)
- **Example Response**:
```json
{
  "sync_run_id": "03a14484-806e-4296-9057-f08227142bd0",
  "status": "COMPLETED",
  "provider": "AWS",
  "total_discovered": 25,
  "new_resources": 20,
  "updated_resources": 5,
  "stale_resources": 0,
  "relationships_reconciled": 15,
  "quality_score": 92.5,
  "errors": []
}
```

### 2. Live Discovery Synchronization
- **Route**: `POST /api/v1/inventory/sync`
- **Body**:
```json
{
  "provider": "AWS",
  "regions": ["us-east-1", "eu-west-1"],
  "resource_types": ["ec2:instance", "ec2:volume"]
}
```

### 3. Resource Listing & Querying
- **Route**: `GET /api/v1/inventory/resources`
- **Query Parameters**:
  - `provider` (optional): `AWS`, `AZURE`, `GCP`
  - `service_category` (optional): `COMPUTE`, `STORAGE`, `DATABASE`, `NETWORKING`
  - `environment` (optional): `production`, `staging`, `development`
  - `status` (optional): `active`, `stopped`, `terminated`, `deleted`
  - `owner` (optional): partial string match
  - `discovery_status` (optional): `CONFIRMED`, `BILLING_ONLY`, `STALE`
  - `limit`: default `50` (1–1000)
  - `offset`: default `0`

### 4. Cost Correlation
- **Route**: `GET /api/v1/inventory/cost-correlation?resource_id=arn:aws:ec2:us-east-1:123456789012:instance/i-0a1b2c3d`
- **Example Response**:
```json
{
  "resource_id": "arn:aws:ec2:us-east-1:123456789012:instance/i-0a1b2c3d",
  "provider": "AWS",
  "account_id": "123456789012",
  "resource_name": "web-server-prod-01",
  "service_name": "AmazonEC2",
  "resource_type": "aws:ec2:instance",
  "inventory_status": "active",
  "discovery_status": "CONFIRMED",
  "correlation_status": "CONFIRMED_BILLED",
  "total_billed_cost": 138.2400,
  "total_effective_cost": 138.2400,
  "currency": "USD",
  "billing_record_count": 720,
  "earliest_billing_date": "2026-10-01T00:00:00Z",
  "latest_billing_date": "2026-10-31T23:59:59Z"
}
```
