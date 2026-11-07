"""
CloudSage Data Quality Engine.
Evaluates multi-cloud billing records against comprehensive FinOps data quality rules.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from backend.app.normalization.quality.models import (
    QualityAssessmentResult,
    QualityFinding,
    QualitySeverity,
)


class DataQualityEngine:
    """Evaluates data completeness, accuracy, consistency, and compliance."""

    SEVERITY_DEDUCTIONS = {
        QualitySeverity.CRITICAL: Decimal("25.0"),
        QualitySeverity.HIGH: Decimal("10.0"),
        QualitySeverity.MEDIUM: Decimal("3.0"),
        QualitySeverity.LOW: Decimal("1.0"),
        QualitySeverity.INFORMATIONAL: Decimal("0.0"),
    }

    VALID_CURRENCIES = {"USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD", "CHF", "BRL", "SGD", "SEK", "NZD", "ZAR"}

    @classmethod
    def evaluate_record(cls, record: Any) -> List[QualityFinding]:
        """
        Evaluates a single BillingRecord or dictionary against all data quality rules.
        """
        findings: List[QualityFinding] = []

        # Extract fields safely whether record is ORM model or dict
        if isinstance(record, dict):
            provider = record.get("provider") or record.get("cloud_provider")
            account_id = record.get("billing_account_id") or record.get("account_id")
            res_id = record.get("resource_id")
            svc_name = record.get("service_name")
            svc_cat = record.get("service_category")
            cost = record.get("unblended_cost") or record.get("cost_amount")
            currency = record.get("currency")
            start_time = record.get("usage_start_time")
            end_time = record.get("usage_end_time")
            unit = record.get("usage_unit")
            tags = record.get("tags") or {}
        else:
            provider = getattr(record, "provider", None)
            account_id = getattr(record, "billing_account_id", None)
            res_id = getattr(record, "resource_id", None)
            svc_name = getattr(record, "service_name", None)
            svc_cat = getattr(record, "service_category", None)
            cost = getattr(record, "unblended_cost", None)
            currency = getattr(record, "currency", None)
            start_time = getattr(record, "usage_start_time", None)
            end_time = getattr(record, "usage_end_time", None)
            unit = getattr(record, "usage_unit", None)
            tags = getattr(record, "tags", {}) or {}

        rec_id_str = str(res_id or account_id or "unknown-record")

        # Rule DQ-001: Missing Mandatory Provider
        if not provider or str(provider).strip() == "":
            findings.append(QualityFinding(
                rule_id="DQ-001",
                rule_name="MissingProvider",
                severity=QualitySeverity.CRITICAL,
                field_name="provider",
                record_identifier=rec_id_str,
                message="Cloud provider is missing or blank",
                suggested_remediation="Ensure source file adapter supplies valid CloudProvider identifier",
            ))

        # Rule DQ-002: Missing Account Identifier
        if not account_id or str(account_id).strip() == "":
            findings.append(QualityFinding(
                rule_id="DQ-002",
                rule_name="MissingAccountId",
                severity=QualitySeverity.CRITICAL,
                field_name="billing_account_id",
                record_identifier=rec_id_str,
                message="Billing account ID or subscription ID is missing",
                suggested_remediation="Verify account ID mapping in provider CUR/export parser",
            ))

        # Rule DQ-003: Missing or Invalid Timestamps
        if not start_time or not end_time:
            findings.append(QualityFinding(
                rule_id="DQ-003",
                rule_name="MissingTimestamp",
                severity=QualitySeverity.CRITICAL,
                field_name="usage_start_time",
                record_identifier=rec_id_str,
                message="Usage start or end time is null",
                suggested_remediation="Ensure date/time columns are populated in source feed",
            ))
        elif start_time > end_time:
            findings.append(QualityFinding(
                rule_id="DQ-004",
                rule_name="InvertedInterval",
                severity=QualitySeverity.CRITICAL,
                field_name="usage_start_time",
                record_identifier=rec_id_str,
                message=f"Usage start time ({start_time}) is after end time ({end_time})",
                suggested_remediation="Inspect date parser for month/day inversion issues",
            ))

        # Rule DQ-005: Negative Financial Cost
        if cost is None:
            findings.append(QualityFinding(
                rule_id="DQ-005",
                rule_name="MissingCost",
                severity=QualitySeverity.CRITICAL,
                field_name="unblended_cost",
                record_identifier=rec_id_str,
                message="Unblended cost is null",
                suggested_remediation="Ensure cost column is extracted as Decimal",
            ))
        else:
            try:
                dec_cost = Decimal(str(cost))
                if dec_cost < 0:
                    findings.append(QualityFinding(
                        rule_id="DQ-006",
                        rule_name="NegativeCost",
                        severity=QualitySeverity.CRITICAL,
                        field_name="unblended_cost",
                        record_identifier=rec_id_str,
                        message=f"Cost amount {dec_cost} is negative without credit categorization",
                        suggested_remediation="Map negative adjustment line items to Credit ChargeCategory",
                    ))
            except Exception:
                findings.append(QualityFinding(
                    rule_id="DQ-007",
                    rule_name="InvalidCostFormat",
                    severity=QualitySeverity.CRITICAL,
                    field_name="unblended_cost",
                    record_identifier=rec_id_str,
                    message=f"Cost value '{cost}' cannot be parsed as Decimal",
                ))

        # Rule DQ-008: Invalid Currency Code
        if not currency or str(currency).upper().strip() not in cls.VALID_CURRENCIES:
            findings.append(QualityFinding(
                rule_id="DQ-008",
                rule_name="InvalidCurrencyCode",
                severity=QualitySeverity.HIGH,
                field_name="currency",
                record_identifier=rec_id_str,
                message=f"Currency '{currency}' is invalid or unsupported ISO 4217 code",
                suggested_remediation="Verify currency mapping rules",
            ))

        # Rule DQ-009: Unknown Service or Category
        if not svc_name or str(svc_name).strip() == "":
            findings.append(QualityFinding(
                rule_id="DQ-009",
                rule_name="MissingServiceName",
                severity=QualitySeverity.HIGH,
                field_name="service_name",
                record_identifier=rec_id_str,
                message="Service name is missing",
            ))
        elif svc_cat == "OTHER":
            findings.append(QualityFinding(
                rule_id="DQ-010",
                rule_name="UnclassifiedService",
                severity=QualitySeverity.HIGH,
                field_name="service_category",
                record_identifier=rec_id_str,
                message=f"Service '{svc_name}' mapped to unclassified 'OTHER' category",
                suggested_remediation="Register SKU mapping entry in SkuCatalogMapping",
            ))

        # Rule DQ-011: Missing Resource Identifier
        if not res_id or str(res_id).strip() == "":
            findings.append(QualityFinding(
                rule_id="DQ-011",
                rule_name="MissingResourceId",
                severity=QualitySeverity.MEDIUM,
                field_name="resource_id",
                record_identifier=rec_id_str,
                message="Resource identifier is missing; line item cannot be attributed to specific infrastructure",
            ))

        # Rule DQ-012: Missing Ownership Governance Tags
        if not tags or not any(k.lower() in ["owner", "creator", "team"] for k in tags.keys()):
            findings.append(QualityFinding(
                rule_id="DQ-012",
                rule_name="MissingOwnerTag",
                severity=QualitySeverity.MEDIUM,
                field_name="tags",
                record_identifier=rec_id_str,
                message="Resource lacks an 'owner' or 'team' governance tag",
                suggested_remediation="Apply owner tag according to cloud tagging policy",
            ))

        # Rule DQ-013: Missing Environment Tag
        if not tags or not any(k.lower() in ["environment", "env", "stage"] for k in tags.keys()):
            findings.append(QualityFinding(
                rule_id="DQ-013",
                rule_name="MissingEnvironmentTag",
                severity=QualitySeverity.LOW,
                field_name="tags",
                record_identifier=rec_id_str,
                message="Resource lacks an 'environment' governance tag",
            ))

        # Rule DQ-014: Unknown Usage Unit
        if not unit or unit == "UNKNOWN":
            findings.append(QualityFinding(
                rule_id="DQ-014",
                rule_name="UnknownUsageUnit",
                severity=QualitySeverity.LOW,
                field_name="usage_unit",
                record_identifier=rec_id_str,
                message=f"Usage unit is undefined or unmapped: '{unit}'",
            ))

        return findings

    @classmethod
    def evaluate_batch(cls, records: List[Any]) -> QualityAssessmentResult:
        """
        Evaluates a batch of billing records and computes overall quality score and findings.
        """
        all_findings: List[QualityFinding] = []
        provider_counts: Dict[str, int] = {}
        provider_deductions: Dict[str, Decimal] = {}

        for rec in records:
            p = getattr(rec, "provider", None) or (rec.get("provider") if isinstance(rec, dict) else "UNKNOWN")
            p_str = str(p or "UNKNOWN").upper()
            provider_counts[p_str] = provider_counts.get(p_str, 0) + 1

            rec_findings = cls.evaluate_record(rec)
            all_findings.extend(rec_findings)

            for f in rec_findings:
                deduction = cls.SEVERITY_DEDUCTIONS.get(f.severity, Decimal("0.0"))
                provider_deductions[p_str] = provider_deductions.get(p_str, Decimal("0.0")) + deduction

        total_recs = len(records)
        critical_cnt = sum(1 for f in all_findings if f.severity == QualitySeverity.CRITICAL)
        high_cnt = sum(1 for f in all_findings if f.severity == QualitySeverity.HIGH)
        med_cnt = sum(1 for f in all_findings if f.severity == QualitySeverity.MEDIUM)
        low_cnt = sum(1 for f in all_findings if f.severity == QualitySeverity.LOW)
        info_cnt = sum(1 for f in all_findings if f.severity == QualitySeverity.INFORMATIONAL)

        # Base score 100 with per-record normalized deductions
        if total_recs == 0:
            overall_score = Decimal("100.00")
        else:
            total_deduction = (
                (critical_cnt * cls.SEVERITY_DEDUCTIONS[QualitySeverity.CRITICAL])
                + (high_cnt * cls.SEVERITY_DEDUCTIONS[QualitySeverity.HIGH])
                + (med_cnt * cls.SEVERITY_DEDUCTIONS[QualitySeverity.MEDIUM])
                + (low_cnt * cls.SEVERITY_DEDUCTIONS[QualitySeverity.LOW])
            )
            normalized_deduction = total_deduction / Decimal(str(total_recs))
            raw_score = Decimal("100.00") - normalized_deduction
            overall_score = max(Decimal("0.00"), min(Decimal("100.00"), raw_score)).quantize(Decimal("0.01"))

        # Provider score breakdown
        provider_scores: Dict[str, Decimal] = {}
        for prov, cnt in provider_counts.items():
            if cnt > 0:
                p_ded = provider_deductions.get(prov, Decimal("0.0")) / Decimal(str(cnt))
                p_score = max(Decimal("0.00"), min(Decimal("100.00"), Decimal("100.00") - p_ded)).quantize(Decimal("0.01"))
                provider_scores[prov] = p_score

        return QualityAssessmentResult(
            total_records=total_recs,
            overall_score=overall_score,
            critical_count=critical_cnt,
            high_count=high_cnt,
            medium_count=med_cnt,
            low_count=low_cnt,
            informational_count=info_cnt,
            findings=all_findings,
            provider_scores=provider_scores,
        )
