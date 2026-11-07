"""
CloudSage Pydantic Schemas Package.
Exports all canonical request and response schemas.
"""

from backend.app.schemas.alert import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
    NotificationLogCreate,
    NotificationLogResponse,
)
from backend.app.schemas.anomaly import (
    CostAnomalyCreate,
    CostAnomalyResponse,
    CostAnomalyStatusUpdate,
)
from backend.app.schemas.audit import AuditLogCreate, AuditLogResponse
from backend.app.schemas.billing import (
    BillingRecordCreate,
    BillingRecordResponse,
)
from backend.app.schemas.recommendation import (
    RecommendationCreate,
    RecommendationResponse,
    RecommendationStatusUpdate,
)
from backend.app.schemas.resource import (
    CloudResourceCreate,
    CloudResourceResponse,
    ResourceMetricCreate,
    ResourceMetricResponse,
)
from backend.app.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
)
from backend.app.schemas.waste import (
    WasteDetectionCreate,
    WasteDetectionResponse,
    WasteDetectionUpdate,
)

__all__ = [
    "BillingRecordCreate",
    "BillingRecordResponse",
    "CloudResourceCreate",
    "CloudResourceResponse",
    "ResourceMetricCreate",
    "ResourceMetricResponse",
    "WasteDetectionCreate",
    "WasteDetectionResponse",
    "WasteDetectionUpdate",
    "RecommendationCreate",
    "RecommendationResponse",
    "RecommendationStatusUpdate",
    "CostAnomalyCreate",
    "CostAnomalyResponse",
    "CostAnomalyStatusUpdate",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    "AuditLogCreate",
    "AuditLogResponse",
    "AlertRuleCreate",
    "AlertRuleResponse",
    "AlertRuleUpdate",
    "NotificationLogCreate",
    "NotificationLogResponse",
]
