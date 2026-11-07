"""
CloudSage Database Models Package.
Exports all canonical SQLAlchemy 2.0 ORM models and Declarative Base.
"""

from backend.app.core.database import Base
from backend.app.models.alert import AlertRule, NotificationLog
from backend.app.models.anomaly import AnomalyDetectionRun, CostAnomaly, CostBaseline
from backend.app.models.audit import AuditLog
from backend.app.models.billing import BillingRecord
from backend.app.models.ingestion import IngestionRun
from backend.app.models.inventory import (
    InventoryQualityReport,
    InventorySyncRun,
    ResourceRelationship,
)
from backend.app.models.normalization import (
    DataQualityReport,
    ExchangeRate,
    NormalizationRun,
    SkuCatalogMapping,
)
from backend.app.models.recommendation import (
    Recommendation,
    RecommendationEvidence,
    RecommendationHistory,
    RecommendationRun,
)
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.models.user import User
from backend.app.models.waste import WasteDetection, WasteDetectionRun

__all__ = [
    "Base",
    "BillingRecord",
    "CloudResource",
    "ResourceMetric",
    "WasteDetection",
    "WasteDetectionRun",
    "Recommendation",
    "RecommendationEvidence",
    "RecommendationHistory",
    "RecommendationRun",
    "CostAnomaly",
    "CostBaseline",
    "AnomalyDetectionRun",
    "User",
    "AuditLog",
    "AlertRule",
    "NotificationLog",
    "IngestionRun",
    "ExchangeRate",
    "SkuCatalogMapping",
    "NormalizationRun",
    "DataQualityReport",
    "ResourceRelationship",
    "InventorySyncRun",
    "InventoryQualityReport",
]
