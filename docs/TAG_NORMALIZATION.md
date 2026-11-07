# Advanced Resource Tag Normalization & Hygiene Governance

## 1. Executive Summary

Resource tags and labels form the backbone of FinOps cost allocation, showback, and organizational accountability. However, real-world multi-cloud tagging is rife with casing inconsistencies, inconsistent prefixes, and missing ownership metadata.

The CloudSage **Tag Normalization Engine** cleans raw tags, extracts core governance dimensions using regex pattern matching, and computes an automated **Tag Hygiene Score** (0 - 100%) for every cloud resource.

- **Module**: `backend/app/normalization/tags/`
- **Sanitizer**: `TagSanitizer`
- **Extractor**: `TagExtractor`
- **Quality Scorer**: `TagQualityScorer`

---

## 2. Tag Sanitization Pipeline (`TagSanitizer`)

Raw tags from AWS (`resourceTags/user:Name`), Azure (`tag:Owner`), and GCP (`labels/env`) undergo automated cleaning:

1. **Prefix Elimination**: Strips provider tags such as `resourceTags/user:`, `resourcetags/aws:`, `user:`, `tag:`, `labels/`.
2. **Whitespace Trimming**: Strips leading and trailing whitespace from both keys and values.
3. **Key Normalization**: Converts all keys to lowercase `snake_case` (e.g. `Cost-Center ID` $\to$ `cost_center_id`).
4. **Invalid Character Detection**: Scans keys for invalid symbols outside `[a-zA-Z0-9_\-\.\:\/]`.
5. **Original Preservation**: The original provider tags are preserved in `raw_metadata` for auditing.

---

## 3. Configurable Regex Metadata Extraction (`TagExtractor`)

CloudSage extracts 5 primary governance attributes regardless of naming discrepancies:

| FinOps Dimension | Configurable Regex Patterns | Standardized Interpretation Example |
| :--- | :--- | :--- |
| **Owner** | `^(owner\|creator\|created_by\|team\|author\|contact)$` | `alice@company.com` |
| **Environment** | `^(environment\|env\|stage\|tier)$` | Standardized canonical string (see below) |
| **Cost Center** | `^(cost_center\|costcenter\|cc\|billing_code\|cost_code)$` | `CC-1004` |
| **Project** | `^(project\|project_name\|app\|application\|workload)$` | `CloudSage-Core` |
| **Department** | `^(department\|dept\|org\|business_unit\|bu)$` | `Data Platform Engineering` |

### Environment Token Standardization
Varied abbreviations across teams are mapped to canonical tokens:
- `prod`, `prd` $\longrightarrow$ `"production"`
- `dev`, `development` $\longrightarrow$ `"development"`
- `stg`, `stage`, `staging` $\longrightarrow$ `"staging"`
- `qa`, `uat`, `test` $\longrightarrow$ `"testing"`
- `sbx`, `sandbox` $\longrightarrow$ `"sandbox"`

---

## 4. Tag Hygiene Scoring Framework (`TagQualityScorer`)

Every resource receives a deterministic **Tag Hygiene Score** ($0.00$ to $100.00$) calculated from the coverage of critical FinOps governance tags:

$$\text{Hygiene Score} = \text{Owner (30 pts)} + \text{Environment (30 pts)} + \text{Project (20 pts)} + \text{Cost Center (20 pts)}$$

### Hygiene Rating Classification

| Hygiene Score Range | Rating Classification | Operational Action |
| :---: | :---: | :--- |
| **$90 - 100\%$** | `EXCELLENT` | Resource fully compliant with corporate governance policies |
| **$70 - 89\%$** | `GOOD` | Acceptable; minor metadata omission (e.g. missing Cost Center) |
| **$1 - 69\%$** | `POOR` | Non-compliant; flagged for remediation by engineering owners |
| **$0\%$** | `UNTAGGED` | Severe violation; resource unowned and unallocated |

---

## 5. REST API Usage Example

Inspect tag quality scores across resources:
```bash
curl "http://localhost:8000/api/v1/normalization/tag-quality?limit=5"
```

Response:
```json
[
  {
    "resource_id": "arn:aws:ec2:us-east-1:12345:instance/i-0123",
    "raw_tags_count": 4,
    "normalized_tags_count": 4,
    "extracted_owner": "devops@company.com",
    "extracted_environment": "production",
    "extracted_cost_center": "CC-101",
    "extracted_project": "PaymentGateway",
    "missing_mandatory_tags": [],
    "quality_score": 100.0,
    "hygiene_rating": "EXCELLENT"
  }
]
```
