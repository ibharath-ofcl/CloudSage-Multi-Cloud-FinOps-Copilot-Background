"""
CloudSage Database Models Package.
Exports all canonical SQLAlchemy 2.0 ORM models and Declarative Base.
"""

from backend.app.core.database import Base
from backend.app.models.alert import AlertRule, NotificationLog
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.audit import AuditLog
from backend.app.models.billing import BillingRecord
from backend.app.models.ingestion import IngestionRun
from backend.app.models.recommendation import Recommendation
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.models.user import User
from backend.app.models.waste import WasteDetection

__all__ = [
    "Base",
    "BillingRecord",
    "CloudResource",
    "ResourceMetric",
    "WasteDetection",
    "Recommendation",
    "CostAnomaly",
    "User",
    "AuditLog",
    "AlertRule",
    "NotificationLog",
    "IngestionRun",
]
