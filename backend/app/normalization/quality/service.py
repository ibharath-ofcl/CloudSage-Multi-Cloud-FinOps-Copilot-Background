"""
CloudSage Data Quality Service.
Manages execution, report generation, and persistence of data quality assessments.
"""

from typing import Any, List, Optional
import uuid
from sqlalchemy.orm import Session
from backend.app.models.normalization import DataQualityReport
from backend.app.normalization.quality.evaluator import DataQualityEngine
from backend.app.normalization.quality.models import QualityAssessmentResult


class DataQualityService:
    """Service orchestrating data quality checks and persisting quality audits."""

    @classmethod
    def evaluate_and_persist(
        cls,
        db: Session,
        records: List[Any],
        provider: Optional[str] = None,
        run_id: Optional[uuid.UUID] = None,
    ) -> DataQualityReport:
        """
        Runs quality evaluation over records and persists report into data_quality_reports.
        """
        assessment: QualityAssessmentResult = DataQualityEngine.evaluate_batch(records)

        summary_payload = {
            "provider_scores": {k: float(v) for k, v in assessment.provider_scores.items()},
            "top_findings": [
                {
                    "rule_id": f.rule_id,
                    "rule_name": f.rule_name,
                    "severity": f.severity.value,
                    "message": f.message,
                    "field": f.field_name,
                }
                for f in assessment.findings[:50]
            ],
        }

        report = DataQualityReport(
            report_id=uuid.uuid4(),
            run_id=run_id,
            provider=provider or "ALL",
            overall_score=assessment.overall_score,
            total_records_evaluated=assessment.total_records,
            critical_findings=assessment.critical_count,
            high_findings=assessment.high_count,
            medium_findings=assessment.medium_count,
            low_findings=assessment.low_count,
            informational_findings=assessment.informational_count,
            findings_summary=summary_payload,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def get_latest_report(cls, db: Session, provider: Optional[str] = None) -> Optional[DataQualityReport]:
        """Fetches latest persisted quality report."""
        query = db.query(DataQualityReport)
        if provider:
            query = query.filter(DataQualityReport.provider == provider.upper())
        return query.order_by(DataQualityReport.created_at.desc()).first()
