"""
CloudSage Fine-Grained Permissions & Role Mapping Architecture.
Implements the resource:action permission taxonomy and canonical role definitions.
"""

from typing import Dict, List, Set
from backend.app.core.enums import UserRole


class Permissions:
    """Canonical fine-grained permission codes."""
    ALL = "*"

    # Dashboard & Reports
    DASHBOARD_READ = "dashboard:read"
    DASHBOARD_EXPORT = "dashboard:export"

    # Billing & Cost Analytics
    BILLING_READ = "billing:read"
    BILLING_EXPORT = "billing:export"

    # Cloud Resources & Inventory
    RESOURCES_READ = "resources:read"
    RESOURCES_SYNC = "resources:sync"

    # Cloud Waste Detections
    WASTE_READ = "waste:read"
    WASTE_UPDATE = "waste:update"
    WASTE_DISMISS = "waste:dismiss"

    # Advisory Recommendations
    RECOMMENDATIONS_READ = "recommendations:read"
    RECOMMENDATIONS_UPDATE = "recommendations:update"
    RECOMMENDATIONS_APPROVE = "recommendations:approve"
    RECOMMENDATIONS_DISMISS = "recommendations:dismiss"
    RECOMMENDATIONS_OVERRIDE = "recommendations:override"

    # Cost Anomalies
    ANOMALIES_READ = "anomalies:read"
    ANOMALIES_DISMISS = "anomalies:dismiss"

    # Anomaly Investigations & RCA
    INVESTIGATIONS_CREATE = "investigations:create"
    INVESTIGATIONS_READ = "investigations:read"
    INVESTIGATIONS_UPDATE = "investigations:update"
    INVESTIGATIONS_ASSIGN = "investigations:assign"
    INVESTIGATIONS_RESOLVE = "investigations:resolve"
    INVESTIGATIONS_CLOSE = "investigations:close"
    INVESTIGATIONS_REOPEN = "investigations:reopen"

    # Alerts & Rules
    ALERTS_READ = "alerts:read"
    ALERTS_MANAGE = "alerts:manage"
    ALERTS_ACKNOWLEDGE = "alerts:acknowledge"
    ALERTS_RESOLVE = "alerts:resolve"

    # Notifications
    NOTIFICATIONS_READ = "notifications:read"
    NOTIFICATION_RULES_MANAGE = "notification_rules:manage"

    # AI Copilot
    COPILOT_QUERY = "copilot:query"

    # User & Identity Administration
    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    SESSIONS_REVOKE = "sessions:revoke"

    # Role & Permission Administration
    ROLES_READ = "roles:read"
    ROLES_MANAGE = "roles:manage"

    # Security & Audit
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    AUDIT_VERIFY = "audit:verify"
    SECURITY_READ = "security:read"
    SECURITY_MANAGE = "security:manage"

    # Multi-Tenant Organization Management
    TENANT_READ = "tenant:read"
    TENANT_MANAGE = "tenant:manage"
    APPROVALS_REQUEST = "approvals:request"
    APPROVALS_DECIDE = "approvals:decide"


ALL_PERMISSIONS: List[str] = [
    getattr(Permissions, attr)
    for attr in dir(Permissions)
    if not attr.startswith("_") and isinstance(getattr(Permissions, attr), str)
]


ROLE_PERMISSIONS_MAP: Dict[str, Set[str]] = {
    # 1. SUPER_ADMIN: Global system superuser with wildcard authority
    UserRole.SUPER_ADMIN.value: {"*"},

    # 2. ORGANIZATION_ADMIN: Complete control within assigned tenant
    UserRole.ORGANIZATION_ADMIN.value: {
        Permissions.DASHBOARD_READ,
        Permissions.DASHBOARD_EXPORT,
        Permissions.BILLING_READ,
        Permissions.BILLING_EXPORT,
        Permissions.RESOURCES_READ,
        Permissions.RESOURCES_SYNC,
        Permissions.WASTE_READ,
        Permissions.WASTE_UPDATE,
        Permissions.WASTE_DISMISS,
        Permissions.RECOMMENDATIONS_READ,
        Permissions.RECOMMENDATIONS_UPDATE,
        Permissions.RECOMMENDATIONS_APPROVE,
        Permissions.RECOMMENDATIONS_DISMISS,
        Permissions.RECOMMENDATIONS_OVERRIDE,
        Permissions.ANOMALIES_READ,
        Permissions.ANOMALIES_DISMISS,
        Permissions.INVESTIGATIONS_CREATE,
        Permissions.INVESTIGATIONS_READ,
        Permissions.INVESTIGATIONS_UPDATE,
        Permissions.INVESTIGATIONS_ASSIGN,
        Permissions.INVESTIGATIONS_RESOLVE,
        Permissions.INVESTIGATIONS_CLOSE,
        Permissions.INVESTIGATIONS_REOPEN,
        Permissions.ALERTS_READ,
        Permissions.ALERTS_MANAGE,
        Permissions.ALERTS_ACKNOWLEDGE,
        Permissions.ALERTS_RESOLVE,
        Permissions.NOTIFICATIONS_READ,
        Permissions.NOTIFICATION_RULES_MANAGE,
        Permissions.COPILOT_QUERY,
        Permissions.USERS_READ,
        Permissions.USERS_MANAGE,
        Permissions.SESSIONS_REVOKE,
        Permissions.ROLES_READ,
        Permissions.ROLES_MANAGE,
        Permissions.AUDIT_READ,
        Permissions.AUDIT_EXPORT,
        Permissions.AUDIT_VERIFY,
        Permissions.SECURITY_READ,
        Permissions.SECURITY_MANAGE,
        Permissions.TENANT_READ,
        Permissions.APPROVALS_REQUEST,
        Permissions.APPROVALS_DECIDE,
    },

    # 3. FINOPS_MANAGER: Cost management, recommendation approvals, investigation lead
    UserRole.FINOPS_MANAGER.value: {
        Permissions.DASHBOARD_READ,
        Permissions.DASHBOARD_EXPORT,
        Permissions.BILLING_READ,
        Permissions.BILLING_EXPORT,
        Permissions.RESOURCES_READ,
        Permissions.WASTE_READ,
        Permissions.WASTE_UPDATE,
        Permissions.WASTE_DISMISS,
        Permissions.RECOMMENDATIONS_READ,
        Permissions.RECOMMENDATIONS_UPDATE,
        Permissions.RECOMMENDATIONS_APPROVE,
        Permissions.RECOMMENDATIONS_DISMISS,
        Permissions.RECOMMENDATIONS_OVERRIDE,
        Permissions.ANOMALIES_READ,
        Permissions.ANOMALIES_DISMISS,
        Permissions.INVESTIGATIONS_CREATE,
        Permissions.INVESTIGATIONS_READ,
        Permissions.INVESTIGATIONS_UPDATE,
        Permissions.INVESTIGATIONS_ASSIGN,
        Permissions.INVESTIGATIONS_RESOLVE,
        Permissions.INVESTIGATIONS_CLOSE,
        Permissions.INVESTIGATIONS_REOPEN,
        Permissions.ALERTS_READ,
        Permissions.ALERTS_MANAGE,
        Permissions.ALERTS_ACKNOWLEDGE,
        Permissions.ALERTS_RESOLVE,
        Permissions.NOTIFICATIONS_READ,
        Permissions.NOTIFICATION_RULES_MANAGE,
        Permissions.COPILOT_QUERY,
        Permissions.USERS_READ,
        Permissions.AUDIT_READ,
        Permissions.APPROVALS_REQUEST,
    },

    # Backward compatibility: FINOPS_ENGINEER maps to FINOPS_MANAGER
    UserRole.FINOPS_ENGINEER.value: {
        Permissions.DASHBOARD_READ,
        Permissions.DASHBOARD_EXPORT,
        Permissions.BILLING_READ,
        Permissions.BILLING_EXPORT,
        Permissions.RESOURCES_READ,
        Permissions.WASTE_READ,
        Permissions.WASTE_UPDATE,
        Permissions.WASTE_DISMISS,
        Permissions.RECOMMENDATIONS_READ,
        Permissions.RECOMMENDATIONS_UPDATE,
        Permissions.RECOMMENDATIONS_APPROVE,
        Permissions.RECOMMENDATIONS_DISMISS,
        Permissions.ANOMALIES_READ,
        Permissions.ANOMALIES_DISMISS,
        Permissions.INVESTIGATIONS_CREATE,
        Permissions.INVESTIGATIONS_READ,
        Permissions.INVESTIGATIONS_UPDATE,
        Permissions.INVESTIGATIONS_ASSIGN,
        Permissions.INVESTIGATIONS_RESOLVE,
        Permissions.INVESTIGATIONS_CLOSE,
        Permissions.INVESTIGATIONS_REOPEN,
        Permissions.ALERTS_READ,
        Permissions.ALERTS_MANAGE,
        Permissions.ALERTS_ACKNOWLEDGE,
        Permissions.ALERTS_RESOLVE,
        Permissions.NOTIFICATIONS_READ,
        Permissions.NOTIFICATION_RULES_MANAGE,
        Permissions.COPILOT_QUERY,
        Permissions.AUDIT_READ,
        Permissions.APPROVALS_REQUEST,
    },

    # 4. FINOPS_ANALYST: Financial analysis, anomaly triage, investigation contributor
    UserRole.FINOPS_ANALYST.value: {
        Permissions.DASHBOARD_READ,
        Permissions.DASHBOARD_EXPORT,
        Permissions.BILLING_READ,
        Permissions.RESOURCES_READ,
        Permissions.WASTE_READ,
        Permissions.RECOMMENDATIONS_READ,
        Permissions.ANOMALIES_READ,
        Permissions.INVESTIGATIONS_CREATE,
        Permissions.INVESTIGATIONS_READ,
        Permissions.INVESTIGATIONS_UPDATE,
        Permissions.ALERTS_READ,
        Permissions.ALERTS_ACKNOWLEDGE,
        Permissions.NOTIFICATIONS_READ,
        Permissions.COPILOT_QUERY,
        Permissions.APPROVALS_REQUEST,
    },
    UserRole.FINANCE_ANALYST.value: {
        Permissions.DASHBOARD_READ,
        Permissions.DASHBOARD_EXPORT,
        Permissions.BILLING_READ,
        Permissions.RESOURCES_READ,
        Permissions.WASTE_READ,
        Permissions.RECOMMENDATIONS_READ,
        Permissions.ANOMALIES_READ,
        Permissions.INVESTIGATIONS_CREATE,
        Permissions.INVESTIGATIONS_READ,
        Permissions.INVESTIGATIONS_UPDATE,
        Permissions.ALERTS_READ,
        Permissions.ALERTS_ACKNOWLEDGE,
        Permissions.NOTIFICATIONS_READ,
        Permissions.COPILOT_QUERY,
        Permissions.APPROVALS_REQUEST,
    },

    # 5. CLOUD_ENGINEER: Technical resource review, investigation findings
    UserRole.CLOUD_ENGINEER.value: {
        Permissions.DASHBOARD_READ,
        Permissions.RESOURCES_READ,
        Permissions.WASTE_READ,
        Permissions.RECOMMENDATIONS_READ,
        Permissions.ANOMALIES_READ,
        Permissions.INVESTIGATIONS_READ,
        Permissions.INVESTIGATIONS_UPDATE,
        Permissions.ALERTS_READ,
        Permissions.NOTIFICATIONS_READ,
        Permissions.COPILOT_QUERY,
    },
    UserRole.ENGINEERING_MANAGER.value: {
        Permissions.DASHBOARD_READ,
        Permissions.BILLING_READ,
        Permissions.RESOURCES_READ,
        Permissions.WASTE_READ,
        Permissions.RECOMMENDATIONS_READ,
        Permissions.ANOMALIES_READ,
        Permissions.INVESTIGATIONS_READ,
        Permissions.INVESTIGATIONS_UPDATE,
        Permissions.ALERTS_READ,
        Permissions.NOTIFICATIONS_READ,
        Permissions.COPILOT_QUERY,
        Permissions.APPROVALS_REQUEST,
    },

    # 6. SECURITY_AUDITOR: Read-only audit ledgers, security monitoring, compliance reports
    UserRole.SECURITY_AUDITOR.value: {
        Permissions.DASHBOARD_READ,
        Permissions.AUDIT_READ,
        Permissions.AUDIT_EXPORT,
        Permissions.AUDIT_VERIFY,
        Permissions.SECURITY_READ,
        Permissions.USERS_READ,
        Permissions.ROLES_READ,
        Permissions.TENANT_READ,
        Permissions.NOTIFICATIONS_READ,
    },

    # 7. VIEWER / EXECUTIVE: Read-only dashboard view
    UserRole.VIEWER.value: {
        Permissions.DASHBOARD_READ,
        Permissions.BILLING_READ,
        Permissions.NOTIFICATIONS_READ,
    },
    UserRole.EXECUTIVE.value: {
        Permissions.DASHBOARD_READ,
        Permissions.DASHBOARD_EXPORT,
        Permissions.BILLING_READ,
        Permissions.RECOMMENDATIONS_READ,
        Permissions.ANOMALIES_READ,
        Permissions.INVESTIGATIONS_READ,
        Permissions.NOTIFICATIONS_READ,
        Permissions.COPILOT_QUERY,
    },
}


def get_permissions_for_role(role_name: str) -> Set[str]:
    """Retrieves all permissions granted to a given role name."""
    return ROLE_PERMISSIONS_MAP.get(role_name.upper(), set())


def get_permissions_for_roles(roles: List[str]) -> Set[str]:
    """Retrieves the unified set of permissions across multiple assigned roles."""
    perms = set()
    for r in roles:
        role_perms = get_permissions_for_role(r)
        if "*" in role_perms:
            return {"*"}
        perms.update(role_perms)
    return perms


def has_permission(granted_permissions: Set[str], required_permission: str) -> bool:
    """
    Evaluates whether granted permissions satisfy the required capability.
    Supports:
    - Wildcard superadmin authority '*'
    - Exact permission matching (e.g. 'recommendations:approve')
    - Domain wildcards (e.g. 'users:*')
    """
    if Permissions.ALL in granted_permissions or "*" in granted_permissions:
        return True
    if required_permission in granted_permissions:
        return True
    if ":" in required_permission:
        domain = required_permission.split(":", 1)[0]
        if f"{domain}:*" in granted_permissions:
            return True
    return False
