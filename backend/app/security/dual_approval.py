"""
CloudSage Dual Approval & Separation of Duties Service.
Enforces multi-party governance on high-risk administrative mutations.
Rules:
- Requester CANNOT approve their own request.
- Approver must possess independent authorization.
- Requests expire automatically after 24 hours.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.enums import ApprovalStatus
from backend.app.models.security import ApprovalRequest
from backend.app.security.principals import AuthenticatedPrincipal


class DualApprovalService:
    """Manages separation of duties and dual-approval workflows."""

    @classmethod
    def create_request(
        cls,
        db: Session,
        principal: AuthenticatedPrincipal,
        action_type: str,
        resource_type: str,
        resource_id: str,
        requested_payload: Dict[str, Any],
        justification: str,
        expiry_hours: int = 24,
    ) -> ApprovalRequest:
        """Submits a sensitive operation for independent dual approval."""
        if not justification or len(justification.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A detailed justification (minimum 10 characters) is required for sensitive administrative requests.",
            )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=expiry_hours)

        tenant_uuid = UUID(str(principal.tenant_id)) if principal.tenant_id else None
        requester_uuid = UUID(str(principal.user_id)) if principal.user_id else uuid.uuid4()

        approval_req = ApprovalRequest(
            id=uuid.uuid4(),
            tenant_id=tenant_uuid,
            requester_id=requester_uuid,
            requester_email=principal.email,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=str(resource_id),
            requested_payload=requested_payload,
            justification=justification.strip(),
            status=ApprovalStatus.PENDING.value,
            created_at=now,
            expires_at=expires_at,
        )
        db.add(approval_req)
        db.commit()
        db.refresh(approval_req)
        return approval_req

    @classmethod
    def decide_request(
        cls,
        db: Session,
        principal: AuthenticatedPrincipal,
        request_id: UUID,
        approved: bool,
        decision_notes: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Reviews and approves or rejects a pending sensitive request.
        Enforces separation of duties: requester != approver!
        """
        req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval request '{request_id}' not found.",
            )

        # 1. Tenant Boundary Check
        if not principal.is_super_admin and req.tenant_id:
            if str(req.tenant_id) != str(principal.tenant_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cross-tenant approval decision is forbidden.",
                )

        # 2. Status & Expiration Check
        now = datetime.now(timezone.utc)
        exp = req.expires_at.replace(tzinfo=timezone.utc) if req.expires_at.tzinfo is None else req.expires_at
        if req.status != ApprovalStatus.PENDING.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval request is already in state '{req.status}'.",
            )
        if exp < now:
            req.status = ApprovalStatus.EXPIRED.value
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approval request has expired.",
            )

        # 3. Separation of Duties: Requester CANNOT approve their own request!
        if principal.user_id and str(req.requester_id) == str(principal.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Separation of duties violation: The requester cannot approve their own administrative request.",
            )
        if req.requester_email.lower() == principal.email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Separation of duties violation: The requester cannot approve their own administrative request.",
            )

        # 4. Record Decision
        approver_uuid = UUID(str(principal.user_id)) if principal.user_id else None
        req.status = ApprovalStatus.APPROVED.value if approved else ApprovalStatus.REJECTED.value
        req.approver_id = approver_uuid
        req.approver_email = principal.email
        req.decision_notes = decision_notes
        req.decided_at = now
        db.commit()
        db.refresh(req)
        return req

    @classmethod
    def list_requests(
        cls,
        db: Session,
        tenant_id: Optional[UUID] = None,
        status_filter: Optional[str] = None,
    ) -> List[ApprovalRequest]:
        """Lists pending or historical dual-approval requests."""
        query = db.query(ApprovalRequest)
        if tenant_id:
            query = query.filter(ApprovalRequest.tenant_id == tenant_id)
        if status_filter:
            query = query.filter(ApprovalRequest.status == status_filter.upper())
        return query.order_by(ApprovalRequest.created_at.desc()).all()
