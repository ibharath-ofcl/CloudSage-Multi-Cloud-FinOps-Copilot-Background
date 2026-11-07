"""
CloudSage Cost Anomaly Detection Celery Tasks.
Asynchronous background execution of multi-cloud cost anomaly detection routines.
"""

from typing import Any, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.anomaly_detection.engine import AnomalyDetectionEngine

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


def execute_anomaly_detection_job(
    provider: Optional[str] = None,
    account_id: Optional[str] = None,
    service_name: Optional[str] = None,
    baseline_window_days: int = 30,
    detector_ids: Optional[List[str]] = None,
    scope: str = "FULL",
) -> Dict[str, Any]:
    """Synchronous core logic executed either within a Celery worker or synchronously in tests."""
    session = SyncSessionLocal()
    engine = AnomalyDetectionEngine()
    try:
        run = engine.execute_detection_run(
            db=session,
            provider=provider,
            account_id=account_id,
            service_name=service_name,
            baseline_window_days=baseline_window_days,
            detector_ids=detector_ids,
            scope=scope,
        )
        return {
            "run_id": str(run.run_id),
            "status": run.status,
            "provider": run.provider,
            "total_series_evaluated": run.total_series_evaluated,
            "baselines_generated": run.baselines_generated,
            "anomalies_created": run.anomalies_created,
            "anomalies_updated": run.anomalies_updated,
            "anomalies_unchanged": run.anomalies_unchanged,
            "anomalies_resolved": run.anomalies_resolved,
            "total_excess_cost": str(run.total_excess_cost),
            "detector_summary": run.detector_summary,
            "error_details": run.error_details,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
    finally:
        session.close()


if HAS_CELERY and celery_app:
    @celery_app.task(name="cloudsage.anomaly_detection.run")
    def run_anomaly_detection_task(
        provider: Optional[str] = None,
        account_id: Optional[str] = None,
        service_name: Optional[str] = None,
        baseline_window_days: int = 30,
        detector_ids: Optional[List[str]] = None,
        scope: str = "FULL",
    ) -> Dict[str, Any]:
        """Celery task entry point."""
        return execute_anomaly_detection_job(
            provider=provider,
            account_id=account_id,
            service_name=service_name,
            baseline_window_days=baseline_window_days,
            detector_ids=detector_ids,
            scope=scope,
        )
