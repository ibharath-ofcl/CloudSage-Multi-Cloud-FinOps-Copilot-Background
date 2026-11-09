"""
CloudSage Multi-Tenant Boundary Enforcement & Query Scoping.
Ensures every query and mutation is strictly confined to the caller's authorized tenant context.
"""

from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Query

from backend.app.security.principals import AuthenticatedPrincipal


class TenantContext:
    """Enforces multi-tenant data boundaries and prevents IDOR attacks."""

    @classmethod
    def verify_tenant_access(
        cls,
        principal: AuthenticatedPrincipal,
        target_tenant_id: Optional[Any],
    ) -> None:
        """
        Validates that the principal is authorized to access the target tenant.
        SUPER_ADMIN possesses global cross-tenant authority.
        All other roles are strictly confined to their own tenant.
        """
        if not principal.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Authentication required for tenant access.",
            )

        if principal.is_super_admin:
            return

        if not target_tenant_id:
            return

        target_str = str(target_tenant_id)
        principal_str = str(principal.tenant_id) if principal.tenant_id else None

        if not principal_str or principal_str != target_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cross-tenant data access is strictly forbidden.",
            )

    @classmethod
    def scope_query(
        cls,
        query: Query,
        model: Any,
        principal: AuthenticatedPrincipal,
    ) -> Query:
        """
        Applies tenant boundary filtering to an active SQLAlchemy query.
        If the model has a tenant_id attribute and caller is not SUPER_ADMIN,
        restricts records to the caller's assigned tenant.
        """
        if not principal.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Authentication required for tenant access.",
            )

        if principal.is_super_admin:
            return query

        if hasattr(model, "tenant_id"):
            if principal.tenant_id:
                try:
                    tenant_uuid = UUID(str(principal.tenant_id))
                    return query.filter(model.tenant_id == tenant_uuid)
                except Exception:
                    return query.filter(model.tenant_id == principal.tenant_id)
            else:
                # User has no assigned tenant; return empty result set safely
                return query.filter(False)

        return query
