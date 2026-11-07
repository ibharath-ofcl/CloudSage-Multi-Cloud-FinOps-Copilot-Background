# Inventory Quality & Governance Evaluation Framework

## 1. Overview

The `InventoryQualityEvaluator` provides continuous scoring of multi-cloud asset inventories across four essential dimensions:
1. **Attribute Completeness**: Are mandatory operational metadata fields populated?
2. **Tag Governance**: Are ownership, environment, and cost-center tags attached according to enterprise FinOps policies?
3. **Data Freshness**: How recently has the asset been verified in a live or export discovery run?
4. **Composite Confidence**: An overall statistical confidence rating in the inventory's fidelity.

Audit results are permanently stored in `inventory_quality_reports` for executive compliance reporting and historical tracking.

---

## 2. Severity-Tiered Findings Rules

| Rule Code | Severity | Description | Penalty Impact |
|:---|:---|:---|:---|
| `MISSING_OWNER` | **CRITICAL** | Resource lacks an identifiable individual or team owner tag. Prevents cost accountability. | Completeness drop + critical findings counter. |
| `MISSING_ENVIRONMENT` | **HIGH** | Resource environment tag is missing, blank, or set to `'unknown'`. Hinders non-prod shutdown automation. | Completeness drop + high findings counter. |
| `STALE_RESOURCE` | **HIGH** | Resource has not been confirmed in discovery scans for >14 days. Likely an un-inventoried zombie asset. | High findings counter + freshness penalty. |
| `MISSING_COST_ALLOCATION`| **MEDIUM** | Resource lacks both `project` and `cost_center` tags. Impairs chargeback/showback. | Completeness drop + medium findings counter. |
| `MISSING_REGION` | **LOW** | Region is missing or unresolvable. | Low findings counter. |
| `UNKNOWN_STATUS` | **LOW** | Lifecycle state could not be translated by `StateMapper`. | Low findings counter. |

---

## 3. Scoring Formulas

### Attribute Completeness Score ($0.00$ to $100.00$)
Evaluates 5 fundamental attributes across all resources: `owner`, `environment`, `cost_allocation`, `region`, and `status`.
$$\text{Completeness} = \frac{\text{Passed Attribute Checks}}{\text{Total Resources} \times 5} \times 100$$

### Tag Quality Score ($0.00$ to $100.00$)
Derived by averaging individual resource tag governance scores computed by Stage 4's `TagQualityScorer`:
$$\text{Tag Quality} = \frac{1}{N} \sum_{i=1}^{N} \text{tag\_quality\_score}_i$$

### Composite Inventory Confidence ($0.0000$ to $1.0000$)
Combines completeness, tag hygiene, and temporal freshness:
$$\text{Confidence} = \frac{0.40 \times \text{Completeness} + 0.40 \times \text{Tag Quality} + 0.20 \times \text{Freshness}}{100}$$
