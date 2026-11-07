"""
CloudSage Waste Detection Celery Tasks.
Asynchronous background execution of comprehensive multi-cloud waste detection heuristics.
"""

from typing import Any, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.waste_detection.engine import WasteDetectionEngine

try:
    from celery import Celery
    celery_app = Celery(
        "cloudsage_tasks",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )
    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
    )
    HAS_CELERY = True
except Exception:
    celery_app = None
    HAS_CELERY = False


def execute_waste_detection_job(
    provider: str = "ALL",
    account_id: Optional[str] = None,
    detectors: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    lookback_days: int = 7,
) -> Dict[str, Any]:
    """Synchronous core logic executed either within a Celery worker or synchronously in tests."""
    session = SyncSessionLocal()
    try:
        run = WasteDetectionEngine.execute_detection_run(
            db=session,
            provider=provider,
            account_id=account_id,
            detectors=detectors,
            categories=categories,
            lookback_days=lookback_days,
        )
        return {
            "run_id": str(run.run_id),
            "status": run.status,
            "provider": run.provider,
            "total_resources_evaluated": run.total_resources_evaluated,
            "findings_created": run.findings_created,
            "findings_updated": run.findings_updated,
            "findings_unchanged": run.findings_unchanged,
            "total_estimated_monthly_savings": str(run.total_estimated_monthly_savings),
            "detector_summary": run.detector_summary,
            "error_details": run.error_details,
        }
    finally:
        session.close()


if HAS_CELERY and celery_app:
    @celery_app.task(name="waste_detection.run", bind=True, max_retries=3)
    def run_waste_detection_task(
        self,
        provider: str = "ALL",
        account_id: Optional[str] = None,
        detectors: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        lookback_days: int = 7,
    ) -> Dict[str, Any]:
        try:
            return execute_waste_detection_job(
                provider=provider,
                account_id=account_id,
                detectors=detectors,
                categories=categories,
                lookback_days=lookback_days,
            )
        except Exception as exc:
            self.retry(exc=exc, countdown=60)
