"""
CloudSage Database Models Package.
Exports all canonical SQLAlchemy 2.0 ORM models and Declarative Base.
"""

from backend.app.core.database import Base
from backend.app.models.alert import (
    AlertHistory,
    AlertInstance,
    AlertRule,
    InAppNotification,
    NotificationDeliveryAttempt,
    NotificationLog,
    NotificationOutbox,
    NotificationPreference,
)
from backend.app.models.anomaly import AnomalyDetectionRun, CostAnomaly, CostBaseline
from backend.app.models.audit import AuditLog
from backend.app.models.billing import BillingRecord
from backend.app.models.copilot import (
    CopilotConversation,
    CopilotFeedback,
    CopilotMessage,
    CopilotUsageLog,
)
from backend.app.models.ingestion import IngestionRun
from backend.app.models.inventory import (
    InventoryQualityReport,
    InventorySyncRun,
    ResourceRelationship,
)
from backend.app.models.investigation import (
    InvestigationCase,
    InvestigationEvidenceLink,
    InvestigationFinding,
    InvestigationHistory,
    InvestigationNote,
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
    RecommendationSavingsOverride,
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
    "RecommendationSavingsOverride",
    "CostAnomaly",
    "CostBaseline",
    "AnomalyDetectionRun",
    "User",
    "AuditLog",
    "AlertRule",
    "AlertInstance",
    "AlertHistory",
    "InAppNotification",
    "NotificationOutbox",
    "NotificationDeliveryAttempt",
    "NotificationPreference",
    "NotificationLog",
    "IngestionRun",
    "ExchangeRate",
    "SkuCatalogMapping",
    "NormalizationRun",
    "DataQualityReport",
    "ResourceRelationship",
    "InventorySyncRun",
    "InventoryQualityReport",
    "InvestigationCase",
    "InvestigationFinding",
    "InvestigationNote",
    "InvestigationEvidenceLink",
    "InvestigationHistory",
    "CopilotConversation",
    "CopilotMessage",
    "CopilotFeedback",
    "CopilotUsageLog",
]
