"""
CloudSage SKU Catalog Lookup Engine.
Resolves provider service codes and SKUs to canonical FinOps categories with provenance and confidence tracking.
"""

from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.normalization import SkuCatalogMapping
from backend.app.normalization.catalog.cache import SkuCatalogCache
from backend.app.normalization.catalog.mappings import (
    SYSTEM_CATALOG_MAPPINGS,
    USAGE_UNIT_NORMALIZATION,
)
from backend.app.normalization.catalog.models import CatalogEntry


class CatalogLookupEngine:
    """Multi-tiered service & SKU catalog lookup engine."""

    _cache = SkuCatalogCache()

    @classmethod
    def normalize_unit(cls, unit: Optional[str]) -> str:
        """Normalizes raw usage units (e.g. 'Hours', 'hrs', 'GB-Mo')."""
        if not unit:
            return "UNKNOWN"
        cleaned = unit.strip().lower()
        return USAGE_UNIT_NORMALIZATION.get(cleaned, cleaned.upper().replace("-", "_").replace(" ", "_"))

    @classmethod
    def resolve_service(
        cls,
        provider: str,
        service_code: str,
        sku_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> CatalogEntry:
        """
        Resolves a provider service code/SKU into a canonical CatalogEntry.
        Tracks confidence and provenance. Unknown SKUs are flagged without fabrication.
        """
        prov = (provider or "AWS").upper().strip()
        svc = (service_code or "UnknownService").strip()
        sku = sku_id.strip() if sku_id else None

        # 1. Check in-memory cache
        cached = cls._cache.get(prov, svc, sku)
        if cached:
            return cached

        # 2. Check Database mappings
        if db:
            db_entry = (
                db.query(SkuCatalogMapping)
                .filter(
                    SkuCatalogMapping.provider == prov,
                    SkuCatalogMapping.service_code == svc,
                )
                .first()
            )
            if db_entry:
                entry = CatalogEntry(
                    provider=prov,
                    service_code=svc,
                    sku_id=sku,
                    canonical_category=db_entry.canonical_category,
                    service_family=db_entry.service_family,
                    resource_type=db_entry.resource_type,
                    normalized_unit=db_entry.normalized_unit,
                    pricing_model_default=db_entry.pricing_model_default,
                    confidence=Decimal(str(db_entry.confidence)),
                    provenance=db_entry.provenance,
                    is_known=True,
                )
                cls._cache.set(entry)
                return entry

        # 3. Check System Catalog exact match
        sys_key = (prov, svc.lower())
        if sys_key in SYSTEM_CATALOG_MAPPINGS:
            base_entry = SYSTEM_CATALOG_MAPPINGS[sys_key]
            entry = CatalogEntry(
                provider=prov,
                service_code=svc,
                sku_id=sku,
                canonical_category=base_entry.canonical_category,
                service_family=base_entry.service_family,
                resource_type=base_entry.resource_type,
                normalized_unit=base_entry.normalized_unit,
                pricing_model_default=base_entry.pricing_model_default,
                confidence=base_entry.confidence,
                provenance=base_entry.provenance,
                is_known=True,
            )
            cls._cache.set(entry)
            return entry

        # 4. Heuristic Keyword Matching (Fuzzy mapping with lower confidence)
        svc_lower = svc.lower()
        heuristic_category = None
        heuristic_family = "Unclassified"

        if any(term in svc_lower for term in ["compute", "vm", "instance", "ec2", "virtual machine"]):
            heuristic_category = "COMPUTE"
            heuristic_family = "Virtual Machine"
        elif any(term in svc_lower for term in ["storage", "s3", "blob", "disk", "bucket"]):
            heuristic_category = "STORAGE"
            heuristic_family = "Object/Block Storage"
        elif any(term in svc_lower for term in ["sql", "database", "rds", "db", "dynamo"]):
            heuristic_category = "DATABASE"
            heuristic_family = "Database"
        elif any(term in svc_lower for term in ["network", "vpc", "dns", "route53", "cdn", "traffic"]):
            heuristic_category = "NETWORKING"
            heuristic_family = "Networking"
        elif any(term in svc_lower for term in ["analytics", "bigquery", "redshift", "synapse", "emr"]):
            heuristic_category = "ANALYTICS"
            heuristic_family = "Analytics"

        if heuristic_category:
            entry = CatalogEntry(
                provider=prov,
                service_code=svc,
                sku_id=sku,
                canonical_category=heuristic_category,
                service_family=heuristic_family,
                resource_type=f"{prov.lower()}:{svc.lower().replace(' ', '_')}",
                normalized_unit="HOURS",
                pricing_model_default="ON_DEMAND",
                confidence=Decimal("0.8500"),
                provenance="HEURISTIC",
                is_known=True,
            )
            cls._cache.set(entry)
            return entry

        # 5. Unknown SKU Handling (Flagged for Review, Not Fabricated)
        unknown_entry = CatalogEntry(
            provider=prov,
            service_code=svc,
            sku_id=sku,
            canonical_category="OTHER",
            service_family="Unclassified",
            resource_type=f"{prov.lower()}:unknown:{svc.lower().replace(' ', '_')}",
            normalized_unit="COUNT",
            pricing_model_default="ON_DEMAND",
            confidence=Decimal("0.5000"),
            provenance="UNKNOWN",
            is_known=False,
        )
        cls._cache.set(unknown_entry)
        return unknown_entry

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()
