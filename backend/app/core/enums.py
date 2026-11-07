"""
CloudSage Core Domain Enumerations.
Standardized string-based enumerations for multi-cloud classification,
waste types, recommendation lifecycle, and RBAC roles.
"""

from enum import Enum


class StrEnum(str, Enum):
    """Base string enumeration for clean JSON serialization."""
    def __str__(self) -> str:
        return self.value


class CloudProvider(StrEnum):
    AWS = "AWS"
    AZURE = "AZURE"
    GCP = "GCP"


class ServiceCategory(StrEnum):
    COMPUTE = "COMPUTE"
    STORAGE = "STORAGE"
    DATABASE = "DATABASE"
    NETWORKING = "NETWORKING"
    AI_ML = "AI_ML"
    ANALYTICS = "ANALYTICS"
    MANAGEMENT = "MANAGEMENT"
    SECURITY = "SECURITY"
    OTHER = "OTHER"


class PricingModel(StrEnum):
    ON_DEMAND = "ON_DEMAND"
    RESERVED = "RESERVED"
    SPOT = "SPOT"
    SAVINGS_PLAN = "SAVINGS_PLAN"
    OTHER = "OTHER"


class WasteType(StrEnum):
    IDLE_VM = "IDLE_VM"
    OVERSIZED_COMPUTE = "OVERSIZED_COMPUTE"
    UNATTACHED_DISK = "UNATTACHED_DISK"
    ORPHANED_SNAPSHOT = "ORPHANED_SNAPSHOT"
    IDLE_IP = "IDLE_IP"
    ZERO_TARGET_LB = "ZERO_TARGET_LB"
    CONTINUOUS_NON_PROD = "CONTINUOUS_NON_PROD"


class Severity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class WasteStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SNOOZED = "SNOOZED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class RecommendationAction(StrEnum):
    TERMINATE = "TERMINATE"
    RIGHTSIZE = "RIGHTSIZE"
    SCHEDULE_SHUTDOWN = "SCHEDULE_SHUTDOWN"
    DELETE_SNAPSHOT = "DELETE_SNAPSHOT"
    RELEASE_IP = "RELEASE_IP"
    CONVERT_STORAGE_TIER = "CONVERT_STORAGE_TIER"


class Priority(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class RiskLevel(StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RecommendationStatus(StrEnum):
    PROPOSED = "PROPOSED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ENDORSED = "ENDORSED"
    APPROVED = "APPROVED"
    DISMISSED = "DISMISSED"
    IMPLEMENTED = "IMPLEMENTED"


class ImplementationEffort(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AnomalyStatus(StrEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class UserRole(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    FINOPS_ENGINEER = "FINOPS_ENGINEER"
    FINANCE_ANALYST = "FINANCE_ANALYST"
    ENGINEERING_MANAGER = "ENGINEERING_MANAGER"
    EXECUTIVE = "EXECUTIVE"


class AlertType(StrEnum):
    BUDGET_THRESHOLD = "BUDGET_THRESHOLD"
    ANOMALY_ZSCORE = "ANOMALY_ZSCORE"
    HIGH_VALUE_WASTE = "HIGH_VALUE_WASTE"


class NotificationChannel(StrEnum):
    SLACK = "SLACK"
    TEAMS = "TEAMS"
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"


class AuditAction(StrEnum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    RECOMMENDATION_APPROVE = "RECOMMENDATION_APPROVE"
    RECOMMENDATION_DISMISS = "RECOMMENDATION_DISMISS"
    RECOMMENDATION_ENDORSE = "RECOMMENDATION_ENDORSE"
    WASTE_DISMISS = "WASTE_DISMISS"
    COPILOT_QUERY = "COPILOT_QUERY"
    INGEST_TRIGGER = "INGEST_TRIGGER"
    USER_CREATE = "USER_CREATE"
    USER_UPDATE = "USER_UPDATE"
