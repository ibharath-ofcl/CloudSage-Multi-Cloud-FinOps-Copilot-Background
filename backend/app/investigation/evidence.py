"""
CloudSage Evidence Linking & Provenance Engine.
Creates and maintains immutable evidence links between an investigation case
and underlying billing line items, inventory resources, telemetry metrics,
waste findings, and alerts.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
import uuid

from sqlalchemy.orm import Session

from backend.app.models.investigation import InvestigationEvidenceLink


class EvidenceManager:
    """Manages association and point-in-time snapshotting of evidence."""

    @staticmethod
    def link_evidence(
        db: Session,
        investigation_id: UUID,
        entity_type: str,
        entity_id: str,
        relationship_role: str,
        metadata_snapshot: Optional[Dict[str, Any]] = None,
    ) -> InvestigationEvidenceLink:
        """
        Creates or updates an immutable evidence link record.
        """
        # Check if already linked
        existing = (
            db.query(InvestigationEvidenceLink)
            .filter(
                InvestigationEvidenceLink.investigation_id == investigation_id,
                InvestigationEvidenceLink.entity_type == entity_type,
                InvestigationEvidenceLink.entity_id == str(entity_id),
            )
            .first()
        )
        if existing:
            if metadata_snapshot:
                existing.metadata_snapshot = metadata_snapshot
                db.flush()
            return existing

        link = InvestigationEvidenceLink(
            id=uuid.uuid4(),
            investigation_id=investigation_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            relationship_role=relationship_role,
            metadata_snapshot=metadata_snapshot or {},
            created_at=datetime.now(timezone.utc),
        )
        db.add(link)
        db.flush()
        return link

    @staticmethod
    def get_links_for_investigation(
        db: Session,
        investigation_id: UUID,
    ) -> List[InvestigationEvidenceLink]:
        """Returns all evidence links tied to an investigation case."""
        return (
            db.query(InvestigationEvidenceLink)
            .filter(InvestigationEvidenceLink.investigation_id == investigation_id)
            .order_by(InvestigationEvidenceLink.created_at.asc())
            .all()
        )
