"""
CloudSage Resource Identifier and Type Mapper.
Parses native identifiers (AWS ARNs, Azure ARM URIs, GCP resource paths) and normalizes resource types.
"""

from typing import Optional, Tuple
from backend.app.normalization.catalog.lookup import CatalogLookupEngine


class ResourceMapper:
    """Normalizes provider resource types, names, and service categories."""

    @classmethod
    def extract_name_from_id(cls, provider: str, resource_id: str, raw_name: Optional[str] = None) -> str:
        """Derives a human-readable name from raw name or resource ID path."""
        if raw_name and str(raw_name).strip() != "":
            return str(raw_name).strip()

        rid = str(resource_id).strip()
        prov = provider.upper().strip()

        if prov == "AWS":
            # ARN format: arn:aws:service:region:account:resourcetype/resourceid
            if "/" in rid:
                return rid.split("/")[-1]
            elif ":" in rid:
                return rid.split(":")[-1]
            return rid

        elif prov == "AZURE":
            # ARM format: /subscriptions/.../resourceGroups/.../providers/.../type/name
            if "/" in rid:
                return rid.split("/")[-1]
            return rid

        elif prov == "GCP":
            # GCP format: //compute.googleapis.com/projects/.../zones/.../instances/name
            if "/" in rid:
                return rid.split("/")[-1]
            return rid

        return rid

    @classmethod
    def resolve_classification(
        cls,
        provider: str,
        service_name: str,
        raw_type: str,
    ) -> Tuple[str, str]:
        """
        Resolves canonical (service_category, canonical_resource_type).
        E.g. ('COMPUTE', 'aws:ec2:instance')
        """
        catalog_entry = CatalogLookupEngine.resolve_service(
            provider=provider,
            service_code=service_name,
        )
        canonical_category = catalog_entry.canonical_category
        canonical_type = catalog_entry.resource_type or f"{provider.lower()}:{raw_type.lower().replace(' ', '_')}"

        return canonical_category, canonical_type
