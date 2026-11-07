"""
CloudSage Recommendation Engine Background Tasks.
Provides asynchronous execution of recommendation generation runs via Celery or synchronous fallback.
"""

from typing import Any, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.recommendations.engine import RecommendationEngine

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


def execute_recommendation_job(
    provider: str = "ALL",
    strategies: Optional[List[str]] = None,
    account_id: Optional[str] = None,
    service_name: Optional[str] = None,
    scope: str = "FULL",
) -> Dict[str, Any]:
    """Synchronous core logic executed either within a Celery worker or synchronously."""
    session = SyncSessionLocal()
    try:
        engine = RecommendationEngine()
        run = engine.execute_run(
            db=session,
            provider=provider,
            strategies=strategies,
            account_id=account_id,
            service_name=service_name,
            scope=scope,
        )
        return {
            "run_id": str(run.run_id),
            "status": run.status,
            "provider": run.provider,
            "total_evaluated": run.total_evaluated,
            "recommendations_created": run.recommendations_created,
            "recommendations_updated": run.recommendations_updated,
            "recommendations_unchanged": run.recommendations_unchanged,
            "recommendations_suppressed": run.recommendations_suppressed,
            "total_monthly_savings": str(run.total_monthly_savings),
            "total_annual_savings": str(run.total_annual_savings),
            "strategy_summary": run.strategy_summary,
            "error_details": run.error_details,
        }
    finally:
        session.close()


if HAS_CELERY and celery_app:
    @celery_app.task(name="recommendations.run", bind=True, max_retries=3)
    def run_recommendation_generation_task(
        self,
        provider: str = "ALL",
        strategies: Optional[List[str]] = None,
        account_id: Optional[str] = None,
        service_name: Optional[str] = None,
        scope: str = "FULL",
    ) -> Dict[str, Any]:
        try:
            return execute_recommendation_job(
                provider=provider,
                strategies=strategies,
                account_id=account_id,
                service_name=service_name,
                scope=scope,
            )
        except Exception as exc:
            self.retry(exc=exc, countdown=60)
