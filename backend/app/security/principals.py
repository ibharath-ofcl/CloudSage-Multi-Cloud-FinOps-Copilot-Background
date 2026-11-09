"""
CloudSage Enterprise Authenticated Principal Model.
Represents a server-verified user identity with assigned roles,
tenant boundaries, and fine-grained permissions.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set
from uuid import UUID


@dataclass
class AuthenticatedPrincipal:
    """Server-verified identity context for an authenticated request."""
    email: str
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    role: str = "VIEWER"
    roles: List[str] = field(default_factory=list)
    permissions: Set[str] = field(default_factory=set)
    full_name: str = ""
    department: Optional[str] = None
    session_id: Optional[str] = None
    token_jti: Optional[str] = None
    is_authenticated: bool = True
    is_super_admin: bool = False

    def __post_init__(self):
        if not self.roles and self.role:
            self.roles = [self.role]
        if self.role == "SUPER_ADMIN" or "SUPER_ADMIN" in self.roles:
            self.is_super_admin = True

    def has_permission(self, permission: str) -> bool:
        """Checks if principal has a specific permission or wildcard authority."""
        if self.is_super_admin:
            return True
        if "*" in self.permissions:
            return True
        if permission in self.permissions:
            return True
        # Check resource wildcard (e.g. "billing:*" covers "billing:read")
        resource = permission.split(":")[0] if ":" in permission else permission
        if f"{resource}:*" in self.permissions:
            return True
        return False

    def has_role(self, *role_names: str) -> bool:
        """Checks if principal possesses any of the specified roles."""
        if self.is_super_admin:
            return True
        upper_roles = {r.upper() for r in self.roles}
        target_roles = {r.upper() for r in role_names}
        return bool(upper_roles.intersection(target_roles))

    def can_access_tenant(self, target_tenant_id: Optional[str]) -> bool:
        """Enforces tenant boundary isolation."""
        if self.is_super_admin:
            return True
        if not target_tenant_id:
            return True
        return str(self.tenant_id) == str(target_tenant_id)

