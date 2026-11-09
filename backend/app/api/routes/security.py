"""
CloudSage Security Monitoring, Dual Approval & Audit Integrity API Router.
Endpoints:
- Security Monitoring & Threat Telemetry (/admin/security/stats, /admin/security/events)
- Dual Approval & Separation of Duties (/admin/security/approvals)
- Cryptographic Audit Hash Verification (/admin/security/audit-integrity)
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_sync_db
from backend.app.schemas.security import (
    ApprovalDecisionRequest,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
    AuditVerificationResponse,
    SecurityEventResponse,
    SecurityStatsResponse,
)
from backend.app.security.audit_integrity import AuditIntegrityService
from backend.app.security.authorization import require_permission
from backend.app.security.dual_approval import DualApprovalService
from backend.app.security.permissions import Permissions
from backend.app.security.principals import AuthenticatedPrincipal
from backend.app.security.tenant_context import TenantContext
from backend.app.security.threat_detection import ThreatDetectionService

router = APIRouter(prefix="/admin/security", tags=["Security Monitoring & Governance"])


# --- Security Monitoring & Threat Detection ---

@router.get("/stats", response_model=SecurityStatsResponse)
def get_security_stats(
    tenant_id: Optional[UUID] = None,
    days: int = Query(7, ge=1, le=90),
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.SECURITY_READ)),
    db: Session = Depends(get_sync_db),
):
    """Retrieves security telemetry indicators and threat detection statistics."""
    target_tenant = tenant_id or (UUID(str(principal.tenant_id)) if principal.tenant_id else None)
    TenantContext.verify_tenant_access(principal, target_tenant)

    stats = ThreatDetectionService.get_security_stats(
        db=db,
        tenant_id=target_tenant if not principal.is_super_admin else tenant_id,
        days=days,
    )
    return SecurityStatsResponse(**stats)


@router.get("/events", response_model=List[SecurityEventResponse])
def list_security_events(
    tenant_id: Optional[UUID] = None,
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.SECURITY_READ)),
    db: Session = Depends(get_sync_db),
):
    """Lists auditable security events (brute force, privilege escalation, cross-tenant probing)."""
    target_tenant = tenant_id or (UUID(str(principal.tenant_id)) if principal.tenant_id else None)
    TenantContext.verify_tenant_access(principal, target_tenant)

    events = ThreatDetectionService.list_events(
        db=db,
        tenant_id=target_tenant if not principal.is_super_admin else tenant_id,
        severity=severity,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    return [SecurityEventResponse.model_validate(e) for e in events]


# --- Dual Approval & Separation of Duties ---

@router.get("/approvals", response_model=List[ApprovalRequestResponse])
def list_approval_requests(
    tenant_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.APPROVALS_REQUEST)),
    db: Session = Depends(get_sync_db),
):
    """Lists pending or decided dual-approval requests."""
    target_tenant = tenant_id or (UUID(str(principal.tenant_id)) if principal.tenant_id else None)
    TenantContext.verify_tenant_access(principal, target_tenant)

    requests = DualApprovalService.list_requests(
        db=db,
        tenant_id=target_tenant if not principal.is_super_admin else tenant_id,
        status_filter=status_filter,
    )
    return [ApprovalRequestResponse.model_validate(r) for r in requests]


@router.post("/approvals", response_model=ApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
def create_approval_request(
    request: Request,
    req_in: ApprovalRequestCreate,
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.APPROVALS_REQUEST)),
    db: Session = Depends(get_sync_db),
):
    """Submits a sensitive administrative action for independent dual approval."""
    client_ip = request.client.host if request.client else "unknown"

    approval_req = DualApprovalService.create_request(
        db=db,
        principal=principal,
        action_type=req_in.action_type,
        resource_type=req_in.resource_type,
        resource_id=req_in.resource_id,
        requested_payload=req_in.requested_payload,
        justification=req_in.justification,
    )

    AuditIntegrityService.record_audit(
        db=db,
        user_id=UUID(principal.user_id) if principal.user_id else None,
        user_email=principal.email,
        action_type="APPROVAL_REQUEST",
        resource_type="approval_requests",
        resource_id=str(approval_req.id),
        before_state=None,
        after_state={"action_type": approval_req.action_type, "resource_id": approval_req.resource_id},
        tenant_id=approval_req.tenant_id,
        client_ip=client_ip,
        status="SUCCESS",
    )

    return ApprovalRequestResponse.model_validate(approval_req)


@router.post("/approvals/{request_id}/decide", response_model=ApprovalRequestResponse)
def decide_approval_request(
    request: Request,
    request_id: UUID,
    decision_in: ApprovalDecisionRequest,
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.APPROVALS_DECIDE)),
    db: Session = Depends(get_sync_db),
):
    """
    Decides (approves or rejects) a pending dual-approval request.
    Strictly enforces separation of duties: requester CANNOT approve their own request!
    """
    client_ip = request.client.host if request.client else "unknown"

    decided_req = DualApprovalService.decide_request(
        db=db,
        principal=principal,
        request_id=request_id,
        approved=decision_in.approved,
        decision_notes=decision_in.decision_notes,
    )

    action_label = "APPROVAL_GRANTED" if decision_in.approved else "APPROVAL_REJECTED"
    AuditIntegrityService.record_audit(
        db=db,
        user_id=UUID(principal.user_id) if principal.user_id else None,
        user_email=principal.email,
        action_type=action_label,
        resource_type="approval_requests",
        resource_id=str(decided_req.id),
        before_state={"status": "PENDING"},
        after_state={"status": decided_req.status, "approver": principal.email},
        tenant_id=decided_req.tenant_id,
        client_ip=client_ip,
        status="SUCCESS",
    )

    return ApprovalRequestResponse.model_validate(decided_req)


# --- Cryptographic Audit Hash Integrity ---

@router.get("/audit-integrity", response_model=AuditVerificationResponse)
def verify_audit_integrity(
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.AUDIT_VERIFY)),
    db: Session = Depends(get_sync_db),
):
    """
    Validates SHA-256 cryptographic chain continuity across the audit ledger.
    Detects any unauthorized record modifications, deletions, or insertions.
    """
    is_valid, count, err_msg = AuditIntegrityService.verify_chain(db)
    now = datetime.now(timezone.utc)

    if not is_valid:
        ThreatDetectionService.record_event(
            db=db,
            event_type="AUDIT_INTEGRITY_FAILED",
            severity="CRITICAL",
            user_email=principal.email,
            user_id=UUID(principal.user_id) if principal.user_id else None,
            tenant_id=UUID(principal.tenant_id) if principal.tenant_id else None,
            details={"error": err_msg, "records_verified": count},
        )

    return AuditVerificationResponse(
        is_valid=is_valid,
        records_verified=count,
        error_message=err_msg,
        verified_at=now,
    )


@router.post("/audit-checkpoints")
def create_audit_checkpoint(
    principal: AuthenticatedPrincipal = Depends(require_permission(Permissions.AUDIT_VERIFY)),
    db: Session = Depends(get_sync_db),
):
    """Generates an immutable cryptographic checkpoint of the current audit ledger chain."""
    tenant_uuid = UUID(principal.tenant_id) if principal.tenant_id else None
    checkpoint = AuditIntegrityService.create_checkpoint(
        db=db,
        tenant_id=tenant_uuid,
        verified_by=principal.email,
    )
    return {
        "checkpoint_id": str(checkpoint.id),
        "cumulative_hash": checkpoint.cumulative_hash,
        "records_verified": checkpoint.record_count,
        "is_valid": checkpoint.is_valid,
        "verified_at": checkpoint.verified_at,
    }
