"""
CloudSage Ingestion Celery Tasks.
Provides background asynchronous processing for large multi-cloud billing files with retry policies.
"""

import os
from typing import Any, Dict, Optional
import uuid
from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.services.ingestion_service import IngestionService

# Celery instance initialization (optional in lightweight test mode)
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


def execute_background_ingestion(
    file_path: str,
    provider_str: str,
    batch_size: int = 500
) -> Dict[str, Any]:
    """
    Synchronous core logic executed either within a Celery worker or synchronously in local tests.
    """
    provider = CloudProvider(provider_str.upper()) if provider_str else None
    session = SyncSessionLocal()
    try:
        result = IngestionService.ingest_file(
            db=session,
            file_path=file_path,
            provider=provider,
            batch_size=batch_size,
        )
        return {
            "status": "success" if result.failed_records == 0 else "partial_success",
            "batch_id": str(result.batch_id),
            "ingested_records": result.ingested_records,
            "duplicate_records": result.skipped_duplicates,
            "failed_records": result.failed_records,
            "total_cost_usd": str(result.total_cost_usd),
        }
    finally:
        session.close()


if HAS_CELERY and celery_app:
    @celery_app.task(
        bind=True,
        name="tasks.ingest_billing_file",
        max_retries=3,
        default_retry_delay=30,
        autoretry_for=(Exception,),
        retry_backoff=True,
        retry_backoff_max=300,
        retry_jitter=True,
    )
    def ingest_billing_file_task(self, file_path: str, provider_str: str, batch_size: int = 500):
        """Asynchronous Celery task for executing large billing file imports."""
        return execute_background_ingestion(file_path, provider_str, batch_size)
