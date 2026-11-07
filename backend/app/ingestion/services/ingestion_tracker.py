"""
CloudSage Ingestion Run Tracker.
Manages persistent state, audit trails, and execution summaries for ingestion jobs.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.core.enums import CloudProvider
from backend.app.models.ingestion import IngestionRun


class IngestionTracker:
    """Manages IngestionRun entity lifecycle and analytics summaries."""

    @staticmethod
    def start_run(
        db: Session,
        provider: CloudProvider,
        source_filename: str,
        checksum: Optional[str] = None
    ) -> IngestionRun:
        """Initializes a new persistent IngestionRun in RUNNING status."""
        run = IngestionRun(
            id=uuid.uuid4(),
            provider=provider.value,
            source_filename=source_filename,
            status="RUNNING",
            total_records=0,
            ingested_records=0,
            duplicate_records=0,
            failed_records=0,
            total_cost=Decimal("0.0000"),
            checksum=checksum,
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def complete_run(
        db: Session,
        run: IngestionRun,
        status: str,
        total_records: int,
        ingested_records: int,
        duplicate_records: int,
        failed_records: int,
        total_cost: Decimal,
        error_summary: Optional[List[Dict[str, Any]]] = None
    ) -> IngestionRun:
        """Finalizes an IngestionRun record with final metrics and execution status."""
        run.status = status
        run.total_records = total_records
        run.ingested_records = ingested_records
        run.duplicate_records = duplicate_records
        run.failed_records = failed_records
        run.total_cost = total_cost
        run.error_summary = error_summary or []
        run.completed_at = datetime.now(timezone.utc)

        db.add(run)
        db.commit()
        db.refresh(run)
        return run

    @staticmethod
    def get_run(db: Session, run_id: uuid.UUID) -> Optional[IngestionRun]:
        """Fetches a specific ingestion run by ID."""
        return db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

    @staticmethod
    def list_runs(
        db: Session,
        limit: int = 50,
        offset: int = 0,
        provider: Optional[str] = None
    ) -> List[IngestionRun]:
        """Lists historical ingestion runs ordered by start timestamp descending."""
        query = db.query(IngestionRun)
        if provider:
            query = query.filter(IngestionRun.provider == provider.upper())
        return query.order_by(IngestionRun.started_at.desc()).offset(offset).limit(limit).all()

    @staticmethod
    def get_summary(db: Session) -> Dict[str, Any]:
        """Calculates aggregated ingestion telemetry across all providers."""
        total_runs = db.query(func.count(IngestionRun.id)).scalar() or 0
        total_records = db.query(func.sum(IngestionRun.ingested_records)).scalar() or 0
        total_cost = db.query(func.sum(IngestionRun.total_cost)).scalar() or Decimal("0.0000")

        # Provider breakdown
        breakdown_rows = (
            db.query(IngestionRun.provider, func.sum(IngestionRun.ingested_records))
            .group_by(IngestionRun.provider)
            .all()
        )
        provider_breakdown = {row[0]: (row[1] or 0) for row in breakdown_rows}

        latest_run = db.query(IngestionRun).order_by(IngestionRun.started_at.desc()).first()

        return {
            "total_runs": total_runs,
            "total_records_ingested": total_records,
            "total_cost_ingested_usd": total_cost,
            "provider_breakdown": provider_breakdown,
            "latest_run": latest_run,
        }
