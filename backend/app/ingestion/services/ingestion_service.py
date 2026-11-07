"""
CloudSage Ingestion Service.
High-level service API for executing file imports, stream uploads, and summary reporting.
"""

import io
import os
from typing import Any, Dict, List, Optional, Union
import uuid
from sqlalchemy.orm import Session
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.base import BaseIngestionAdapter, IngestionResult
from backend.app.ingestion.services.ingestion_tracker import IngestionTracker
from backend.app.models.ingestion import IngestionRun


class IngestionService:
    """Entry point for all billing data ingestion workflows."""

    @classmethod
    def ingest_file(
        cls,
        db: Session,
        file_path: str,
        provider: Optional[CloudProvider] = None,
        batch_size: int = 500
    ) -> IngestionResult:
        """Ingests a local billing file on disk."""
        from backend.app.ingestion.pipeline import IngestionPipeline

        filename = os.path.basename(file_path)
        checksum = BaseIngestionAdapter.calculate_file_checksum(file_path)
        pipeline = IngestionPipeline(db)
        return pipeline.execute(
            stream_or_path=file_path,
            source_name=filename,
            provider=provider,
            checksum=checksum,
            batch_size=batch_size
        )

    @classmethod
    def ingest_stream(
        cls,
        db: Session,
        stream: io.TextIOBase,
        filename: str,
        provider: Optional[CloudProvider] = None,
        checksum: Optional[str] = None,
        batch_size: int = 500
    ) -> IngestionResult:
        """Ingests an in-memory or uploaded text stream."""
        from backend.app.ingestion.pipeline import IngestionPipeline

        pipeline = IngestionPipeline(db)
        return pipeline.execute(
            stream_or_path=stream,
            source_name=filename,
            provider=provider,
            checksum=checksum,
            batch_size=batch_size
        )

    @classmethod
    def get_runs(
        cls,
        db: Session,
        limit: int = 50,
        offset: int = 0,
        provider: Optional[str] = None
    ) -> List[IngestionRun]:
        """Lists historical ingestion runs."""
        return IngestionTracker.list_runs(db, limit, offset, provider)

    @classmethod
    def get_run(cls, db: Session, run_id: uuid.UUID) -> Optional[IngestionRun]:
        """Fetches a specific ingestion run."""
        return IngestionTracker.get_run(db, run_id)

    @classmethod
    def get_summary(cls, db: Session) -> Dict[str, Any]:
        """Fetches aggregate ingestion statistics."""
        return IngestionTracker.get_summary(db)
