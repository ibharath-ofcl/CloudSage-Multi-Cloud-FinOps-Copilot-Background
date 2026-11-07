"""
CloudSage SKU & Service Catalog Normalization Tests.
Verifies service resolution, unknown SKU handling, confidence scoring, and usage unit normalization.
"""

from decimal import Decimal
import pytest
from backend.app.models.normalization import SkuCatalogMapping
from backend.app.normalization.catalog.lookup import CatalogLookupEngine


def test_catalog_known_sku_resolution():
    """Verify exact catalog matches for core AWS, Azure, and GCP services."""
    # AWS EC2
    ec2_entry = CatalogLookupEngine.resolve_service(provider="AWS", service_code="AmazonEC2")
    assert ec2_entry.is_known is True
    assert ec2_entry.canonical_category == "COMPUTE"
    assert ec2_entry.service_family == "Virtual Machine"
    assert ec2_entry.confidence == Decimal("1.0000")
    assert ec2_entry.provenance == "SYSTEM_CATALOG"

    # Azure Storage
    azure_storage = CatalogLookupEngine.resolve_service(provider="AZURE", service_code="Storage")
    assert azure_storage.is_known is True
    assert azure_storage.canonical_category == "STORAGE"
    assert azure_storage.service_family == "Object Storage"

    # GCP BigQuery
    gcp_bq = CatalogLookupEngine.resolve_service(provider="GCP", service_code="BigQuery")
    assert gcp_bq.is_known is True
    assert gcp_bq.canonical_category == "ANALYTICS"
    assert gcp_bq.service_family == "Data Warehouse"


def test_catalog_unknown_sku_handling():
    """
    CRITICAL FINOPS REQUIREMENT:
    Unknown SKUs must be flagged for review (is_known=False, OTHER category), NOT fabricated!
    """
    CatalogLookupEngine.clear_cache()
    unknown = CatalogLookupEngine.resolve_service(
        provider="AWS",
        service_code="CompletelyNewHypotheticalServiceXYZ",
    )
    assert unknown.is_known is False
    assert unknown.canonical_category == "OTHER"
    assert unknown.service_family == "Unclassified"
    assert unknown.confidence == Decimal("0.5000")
    assert unknown.provenance == "UNKNOWN"


def test_catalog_heuristic_fuzzy_matching():
    """Verify that uncataloged services with clear keywords receive heuristic categorization."""
    CatalogLookupEngine.clear_cache()
    fuzzy_compute = CatalogLookupEngine.resolve_service(
        provider="AWS",
        service_code="CustomPrivateComputeNodeFleet",
    )
    assert fuzzy_compute.is_known is True
    assert fuzzy_compute.canonical_category == "COMPUTE"
    assert fuzzy_compute.confidence == Decimal("0.8500")
    assert fuzzy_compute.provenance == "HEURISTIC"


def test_catalog_usage_unit_normalization():
    """Verify raw provider usage units are converted to standardized uppercase tokens."""
    assert CatalogLookupEngine.normalize_unit("hours") == "HOURS"
    assert CatalogLookupEngine.normalize_unit("hrs") == "HOURS"
    assert CatalogLookupEngine.normalize_unit("gb-mo") == "GB_MONTH"
    assert CatalogLookupEngine.normalize_unit("requests") == "REQUESTS"
    assert CatalogLookupEngine.normalize_unit("unknown-metric") == "UNKNOWN_METRIC"
    assert CatalogLookupEngine.normalize_unit(None) == "UNKNOWN"


def test_catalog_database_override(db_session):
    """Verify that custom database catalog entries override static defaults."""
    CatalogLookupEngine.clear_cache()
    # Add a custom DB override mapping
    custom = SkuCatalogMapping(
        provider="AWS",
        service_code="CustomEnterpriseMLService",
        canonical_category="AI_ML",
        service_family="Machine Learning Inference",
        resource_type="aws:sagemaker:endpoint",
        normalized_unit="HOURS",
        confidence=Decimal("1.0000"),
        provenance="USER_OVERRIDE",
    )
    db_session.add(custom)
    db_session.commit()

    entry = CatalogLookupEngine.resolve_service(
        provider="AWS",
        service_code="CustomEnterpriseMLService",
        db=db_session,
    )
    assert entry.canonical_category == "AI_ML"
    assert entry.provenance == "USER_OVERRIDE"
    assert entry.is_known is True
