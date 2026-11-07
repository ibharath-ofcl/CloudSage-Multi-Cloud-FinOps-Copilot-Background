"""
CloudSage Inventory Celery Tasks.
Provides asynchronous background execution for multi-cloud inventory file ingestion
and live discovery synchronization with automated quality scoring.
"""

import os
from typing import Any, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.database import SyncSessionLocal
from backend.app.inventory.service import InventoryService

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


def execute_inventory_file_import(
    file_path: str,
    provider: str,
    source_identifier: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous core logic executed in worker or inline."""
    session = SyncSessionLocal()
    try:
        result = InventoryService.import_inventory_file(
            db=session,
            provider=provider,
            stream_or_path=file_path,
            source_identifier=source_identifier or os.path.basename(file_path),
            evaluate_quality=True,
        )
        return result
    finally:
        session.close()


def execute_live_inventory_sync(
    provider: str,
    regions: Optional[List[str]] = None,
    resource_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Synchronous core logic for live hyperscaler discovery."""
    session = SyncSessionLocal()
    try:
        result = InventoryService.run_live_discovery(
            db=session,
            provider=provider,
            regions=regions,
            resource_types=resource_types,
            evaluate_quality=True,
        )
        return result
    finally:
        session.close()


if HAS_CELERY and celery_app:
    @celery_app.task(name="inventory.import_file", bind=True, max_retries=3)
    def import_inventory_file_task(
        self,
        file_path: str,
        provider: str,
        source_identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            return execute_inventory_file_import(file_path, provider, source_identifier)
        except Exception as exc:
            self.retry(exc=exc, countdown=30)

    @celery_app.task(name="inventory.sync_live", bind=True, max_retries=2)
    def sync_inventory_task(
        self,
        provider: str,
        regions: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        try:
            return execute_live_inventory_sync(provider, regions, resource_types)
        except Exception as exc:
            self.retry(exc=exc, countdown=60)
