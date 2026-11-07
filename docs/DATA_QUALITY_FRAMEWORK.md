# CloudSage Data Quality & Governance Framework

## 1. Executive Summary

Garbage in, garbage out: FinOps analysis, anomaly detection, and automated waste recommendations require immaculate underlying data quality. 

The CloudSage **Data Quality Framework** scans incoming billing records for structural violations, missing mandatory fields, negative financial amounts, inverted intervals, and missing governance tags.

- **Module**: `backend/app/normalization/quality/`
- **Database Model**: `DataQualityReport` (`data_quality_reports` table)
- **Engine**: `DataQualityEngine`
- **Service**: `DataQualityService`

---

## 2. Severity Classification & Rules Catalog

Findings are partitioned into 5 standardized severity tiers:

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           Data Quality Rules                           │
  ├──────────┬─────────────────┬──────────┬────────────────────────────────┤
  │ Rule ID  │ Rule Name       │ Severity │ Condition Evaluated            │
  ├──────────┼─────────────────┼──────────┼────────────────────────────────┤
  │ DQ-001   │ MissingProvider │ CRITICAL │ Provider field empty or null   │
  │ DQ-002   │ MissingAccountId│ CRITICAL │ Billing account/sub ID null    │
  │ DQ-003   │ MissingTimestamp│ CRITICAL │ Start or end time is null      │
  │ DQ-004   │ InvertedInterval│ CRITICAL │ Start time > End time          │
  │ DQ-005   │ MissingCost     │ CRITICAL │ Unblended cost is null         │
  │ DQ-006   │ NegativeCost    │ CRITICAL │ Cost < 0 without credit type   │
  │ DQ-007   │ InvalidCostFmt  │ CRITICAL │ Cost not parseable as Decimal  │
  │ DQ-008   │ InvalidCurrency │ HIGH     │ Currency not valid ISO 4217    │
  │ DQ-009   │ MissingSvcName  │ HIGH     │ Service product code missing   │
  │ DQ-010   │ UnclassifiedSvc │ HIGH     │ Service mapped to 'OTHER'      │
  │ DQ-011   │ MissingResId    │ MEDIUM   │ Resource ID ARN/URI missing    │
  │ DQ-012   │ MissingOwnerTag │ MEDIUM   │ Lacks owner or team tag        │
  │ DQ-013   │ MissingEnvTag   │ LOW      │ Lacks environment tag          │
  │ DQ-014   │ UnknownUnit     │ LOW      │ Usage unit unmapped or UNKNOWN │
  └──────────┴─────────────────┴──────────┴────────────────────────────────┘
```

---

## 3. Overall Quality Scoring Formula

Every batch of records receives a composite Data Quality Score ($0.00$ to $100.00$):

$$\text{Deduction} = \frac{(N_{\text{CRITICAL}} \times 25.0) + (N_{\text{HIGH}} \times 10.0) + (N_{\text{MEDIUM}} \times 3.0) + (N_{\text{LOW}} \times 1.0)}{\text{Total Records}}$$

$$\text{Overall Score} = \max\left(0.00,\ \min\left(100.00,\ 100.00 - \text{Deduction}\right)\right)$$

### Non-Destructive Tolerance Policy
Valid billing records are **never** rejected solely because optional metadata (such as an environment tag or human-readable name) is absent. Missing optional attributes produce Low/Medium audit findings, allowing billing records to be committed while notifying FinOps administrators.

---

## 4. Persisted Quality Auditing (`DataQualityReport`)

Quality evaluations are stored in PostgreSQL for historical trend tracking and compliance reporting:

```python
from backend.app.normalization.quality.service import DataQualityService

# Run quality assessment and persist report
report = DataQualityService.evaluate_and_persist(
    db=db_session,
    records=billing_records_list,
    provider="AWS"
)
print(f"Overall Quality: {report.overall_score}%")
print(f"Critical Findings: {report.critical_findings}")
```

---

## 5. REST API Usage Example

Retrieve the latest data quality report:
```bash
curl "http://localhost:8000/api/v1/normalization/quality-report"
```

Response:
```json
{
  "report_id": "c1f2b3a4-5e6d-7c8b-9a0f-1e2d3c4b5a6f",
  "provider": "ALL",
  "overall_score": 98.45,
  "total_records_evaluated": 1200,
  "critical_findings": 0,
  "high_findings": 2,
  "medium_findings": 18,
  "low_findings": 24,
  "informational_findings": 0,
  "findings_summary": {
    "provider_scores": {
      "AWS": 98.60,
      "AZURE": 98.20,
      "GCP": 98.55
    }
  },
  "created_at": "2026-11-07T13:00:00Z"
}
```
