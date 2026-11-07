"""
CloudSage Catalog Service.
High-level service interface for managing catalog lookups and overrides.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.normalization import SkuCatalogMapping
from backend.app.normalization.catalog.lookup import CatalogLookupEngine
from backend.app.normalization.catalog.models import CatalogEntry


class CatalogService:
    """Service for catalog lookups, registrations, and list operations."""

    @classmethod
    def resolve(
        cls,
        provider: str,
        service_code: str,
        sku_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> CatalogEntry:
        return CatalogLookupEngine.resolve_service(
            provider=provider,
            service_code=service_code,
            sku_id=sku_id,
            db=db,
        )

    @classmethod
    def list_mappings(
        cls,
        db: Session,
        provider: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SkuCatalogMapping]:
        """Lists catalog entries from the database."""
        query = db.query(SkuCatalogMapping)
        if provider:
            query = query.filter(SkuCatalogMapping.provider == provider.upper())
        return query.order_by(SkuCatalogMapping.created_at.desc()).offset(offset).limit(limit).all()
