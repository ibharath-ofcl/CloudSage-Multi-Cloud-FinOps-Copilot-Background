"""
CloudSage Alerting & Enterprise Notification Hub REST API Endpoints.
FastAPI router providing comprehensive endpoints for:
1. Alert Rules Management (CRUD, preview, threshold validation, SSRF checks)
2. Materialized Alert Instances (Filtering, stats, lifecycle transitions, history)
3. In-App Notification Center (Listing, unread badge counter, mark read/unread)
4. Outbox & Delivery Management (Monitoring, exponential backoff retries, DLQ, health)
5. User Notification Preferences (Channels, min severity, quiet hours, digests)
Strictly advisory, production-grade, and non-destructive.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, desc
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_sync_db
from backend.app.core.enums import (
    AlertStatus,
    AuditAction,
    NotificationChannel,
    NotificationDeliveryStatus,
    Severity,
    UserRole,
)
from backend.app.models.alert import (
    AlertHistory,
    AlertInstance,
    AlertRule,
    InAppNotification,
    NotificationDeliveryAttempt,
    NotificationOutbox,
    NotificationPreference,
)
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.audit import AuditLog
from backend.app.schemas.alert import (
    AlertActionRequest,
    AlertHistoryResponse,
    AlertInstanceDetailResponse,
    AlertInstanceListResponse,
    AlertInstanceResponse,
    AlertRuleCreate,
    AlertRuleListResponse,
    AlertRulePreviewMatch,
    AlertRulePreviewRequest,
    AlertRulePreviewResponse,
    AlertRuleResponse,
    AlertRuleUpdate,
    AlertStatsResponse,
    InAppNotificationListResponse,
    InAppNotificationResponse,
    NotificationDeliveryAttemptResponse,
    NotificationHealthResponse,
    NotificationOutboxListResponse,
    NotificationOutboxResponse,
    NotificationPreferenceRequest,
    NotificationPreferenceResponse,
    OutboxRetryResponse,
    UnreadCountResponse,
)
from backend.app.alerts.security import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    require_admin_or_finops_role,
    validate_webhook_url,
)
from backend.app.alerts.lifecycle import transition_alert_status
from backend.app.alerts.dispatcher import NotificationDispatcherService

router = APIRouter(tags=["Alerting & Enterprise Notification Hub"])
dispatcher = NotificationDispatcherService()


# ============================================================================
# 1. ALERT RULES MANAGEMENT
# ============================================================================

@router.get("/alert-rules", response_model=AlertRuleListResponse, status_code=status.HTTP_200_OK)
def list_alert_rules(
    provider: Optional[str] = Query(None, description="Cloud provider filter (AWS, AZURE, GCP, ALL)"),
    severity: Optional[str] = Query(None, description="Minimum severity filter"),
    is_active: Optional[bool] = Query(None, description="Filter active/inactive rules"),
    search: Optional[str] = Query(None, description="Search by rule name or description"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
) -> AlertRuleListResponse:
    """Lists configured alert rules with multi-dimensional filtering."""
    query = db.query(AlertRule).filter(AlertRule.is_archived == False)

    if provider and provider.upper() != "ALL":
        query = query.filter(or_(AlertRule.provider == provider.upper(), AlertRule.provider == "ALL"))
    if severity:
        query = query.filter(AlertRule.min_severity == severity.upper())
    if is_active is not None:
        query = query.filter(AlertRule.is_enabled == is_active)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                AlertRule.name.ilike(search_pattern),
                AlertRule.description.ilike(search_pattern),
            )
        )

    total = query.count()
    rules = query.order_by(desc(AlertRule.created_at)).offset(offset).limit(limit).all()
    return AlertRuleListResponse(items=rules, total=total)


@router.post("/alert-rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
def create_alert_rule(
    rule_in: AlertRuleCreate,
    request: Request,
    db: Session = Depends(get_sync_db),
) -> AlertRuleResponse:
    """
    Creates a new multi-cloud alert rule with server-side validation and SSRF defenses.
    Requires ADMIN or FINOPS_ADMIN role.
    """
    principal = get_authenticated_principal(request, db)
    require_admin_or_finops_role(principal)

    # Validate Webhook targets against SSRF
    for r in rule_in.recipients:
        if r.startswith("http://") or r.startswith("https://"):
            validate_webhook_url(r)

    rule = AlertRule(
        id=uuid.uuid4(),
        name=rule_in.name,
        description=rule_in.description,
        alert_type=rule_in.alert_type,
        provider=rule_in.provider.upper(),
        account_id=rule_in.account_id,
        region=rule_in.region,
        service_name=rule_in.service_name,
        environment=rule_in.environment,
        owner=rule_in.owner,
        cost_center=rule_in.cost_center,
        min_severity=rule_in.min_severity.upper(),
        threshold_value=rule_in.threshold_value,
        min_excess_cost=rule_in.min_excess_cost,
        percentage_deviation_threshold=rule_in.percentage_deviation_threshold,
        absolute_deviation_threshold=rule_in.absolute_deviation_threshold,
        anomaly_category=rule_in.anomaly_category,
        channels=rule_in.channels,
        recipients=rule_in.recipients,
        cooldown_minutes=rule_in.cooldown_minutes,
        escalation_policy=rule_in.escalation_policy,
        is_enabled=rule_in.is_enabled,
        created_by=principal.principal_id,
        updated_by=principal.principal_id,
    )
    db.add(rule)

    audit = AuditLog(
        id=uuid.uuid4(),
        action_type=str(AuditAction.ALERT_RULE_CREATE.value),
        resource_type="alert_rules",
        resource_id=str(rule.id),
        user_email=principal.email,
        after_state={
            "name": rule.name,
            "provider": rule.provider,
            "min_severity": rule.min_severity,
            "channels": rule.channels,
        },
        status="SUCCESS",
    )
    db.add(audit)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/alert-rules/{rule_id}", response_model=AlertRuleResponse, status_code=status.HTTP_200_OK)
def get_alert_rule(
    rule_id: UUID,
    db: Session = Depends(get_sync_db),
) -> AlertRuleResponse:
    """Retrieves an alert rule by ID."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id, AlertRule.is_archived == False).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert rule {rule_id} not found.")
    return rule


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleResponse, status_code=status.HTTP_200_OK)
def update_alert_rule(
    rule_id: UUID,
    rule_update: AlertRuleUpdate,
    request: Request,
    db: Session = Depends(get_sync_db),
) -> AlertRuleResponse:
    """Updates an existing alert rule. Requires ADMIN or FINOPS_ADMIN role."""
    principal = get_authenticated_principal(request, db)
    require_admin_or_finops_role(principal)

    rule = db.query(AlertRule).filter(AlertRule.id == rule_id, AlertRule.is_archived == False).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert rule {rule_id} not found.")

    if rule_update.recipients:
        for r in rule_update.recipients:
            if r.startswith("http://") or r.startswith("https://"):
                validate_webhook_url(r)

    update_data = rule_update.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if val is not None:
            if field in ("provider", "min_severity") and isinstance(val, str):
                setattr(rule, field, val.upper())
            else:
                setattr(rule, field, val)

    rule.updated_by = principal.principal_id
    rule.updated_at = datetime.now(timezone.utc)

    audit = AuditLog(
        id=uuid.uuid4(),
        action_type=str(AuditAction.ALERT_RULE_UPDATE.value),
        resource_type="alert_rules",
        resource_id=str(rule.id),
        user_email=principal.email,
        after_state={"updated_fields": list(update_data.keys())},
        status="SUCCESS",
    )
    db.add(audit)
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/alert-rules/{rule_id}/toggle", response_model=AlertRuleResponse, status_code=status.HTTP_200_OK)
def toggle_alert_rule(
    rule_id: UUID,
    request: Request,
    db: Session = Depends(get_sync_db),
) -> AlertRuleResponse:
    """Toggles active/inactive status of an alert rule."""
    principal = get_authenticated_principal(request, db)
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id, AlertRule.is_archived == False).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert rule {rule_id} not found.")

    rule.is_enabled = not rule.is_enabled
    rule.updated_by = principal.principal_id
    rule.updated_at = datetime.now(timezone.utc)

    audit = AuditLog(
        id=uuid.uuid4(),
        action_type=str(AuditAction.ALERT_RULE_UPDATE.value),
        resource_type="alert_rules",
        resource_id=str(rule.id),
        user_email=principal.email,
        after_state={"is_enabled": rule.is_enabled},
        status="SUCCESS",
    )
    db.add(audit)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_200_OK)
def delete_alert_rule(
    rule_id: UUID,
    request: Request,
    db: Session = Depends(get_sync_db),
) -> Dict[str, Any]:
    """Soft deletes an alert rule. Requires ADMIN or FINOPS_ADMIN role."""
    principal = get_authenticated_principal(request, db)
    require_admin_or_finops_role(principal)

    rule = db.query(AlertRule).filter(AlertRule.id == rule_id, AlertRule.is_archived == False).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert rule {rule_id} not found.")

    rule.is_archived = True
    rule.updated_by = principal.principal_id
    rule.updated_at = datetime.now(timezone.utc)

    audit = AuditLog(
        id=uuid.uuid4(),
        action_type=str(AuditAction.ALERT_RULE_DELETE.value),
        resource_type="alert_rules",
        resource_id=str(rule.id),
        user_email=principal.email,
        after_state={"name": rule.name},
        status="SUCCESS",
    )
    db.add(audit)
    db.commit()
    return {"status": "deleted", "rule_id": str(rule_id)}


@router.post("/alert-rules/preview", response_model=AlertRulePreviewResponse, status_code=status.HTTP_200_OK)
def preview_alert_rule(
    preview_in: AlertRulePreviewRequest,
    db: Session = Depends(get_sync_db),
) -> AlertRulePreviewResponse:
    """
    Evaluates rule criteria against historical cost anomalies in dry-run mode without saving.
    """
    query = db.query(CostAnomaly).order_by(desc(CostAnomaly.detected_at)).limit(100)
    anomalies = query.all()

    severity_order = {
        Severity.LOW.value: 1,
        Severity.MEDIUM.value: 2,
        Severity.HIGH.value: 3,
        Severity.CRITICAL.value: 4,
    }
    min_sev_rank = severity_order.get(preview_in.min_severity.upper(), 2)

    matches: List[AlertRulePreviewMatch] = []
    for a in anomalies:
        if preview_in.provider and preview_in.provider.upper() != "ALL":
            if a.provider.upper() != preview_in.provider.upper():
                continue
        if preview_in.account_id and a.account_id != preview_in.account_id:
            continue

        sev_rank = severity_order.get(a.severity.value if hasattr(a.severity, "value") else str(a.severity).upper(), 1)
        if sev_rank < min_sev_rank:
            continue

        excess = Decimal(str(a.estimated_excess_cost or "0.0000"))
        if excess < preview_in.min_excess_cost:
            continue

        pct = Decimal(str(a.spike_percentage or "0.00"))
        if pct < preview_in.percentage_deviation_threshold:
            continue

        matches.append(
            AlertRulePreviewMatch(
                anomaly_id=a.id,
                title=f"{a.provider} {a.service_name} cost anomaly (${excess:,.2f})",
                provider=a.provider,
                account_id=a.account_id,
                service_name=a.service_name,
                excess_cost=excess,
                percentage_deviation=pct,
                severity=a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                detected_at=a.detected_at,
            )
        )

    return AlertRulePreviewResponse(
        matched_count=len(matches),
        total_evaluated=len(anomalies),
        sample_matches=matches[: preview_in.sample_limit],
    )


# ============================================================================
# 2. ALERT INSTANCES & LIFECYCLE MANAGEMENT
# ============================================================================

@router.get("/alerts", response_model=AlertInstanceListResponse, status_code=status.HTTP_200_OK)
def list_alerts(
    status: Optional[str] = Query(None, description="Alert status filter (OPEN, ACKNOWLEDGED, etc.)"),
    severity: Optional[str] = Query(None, description="Severity filter"),
    provider: Optional[str] = Query(None, description="Cloud provider filter"),
    rule_id: Optional[UUID] = Query(None, description="Originating alert rule filter"),
    is_suppressed: Optional[bool] = Query(None, description="Suppression filter"),
    start_date: Optional[datetime] = Query(None, description="Earliest trigger date filter"),
    end_date: Optional[datetime] = Query(None, description="Latest trigger date filter"),
    search: Optional[str] = Query(None, description="Search by title, service or account"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
) -> AlertInstanceListResponse:
    """Lists materialized cost anomaly alert instances with full filtering."""
    query = db.query(AlertInstance)

    if status:
        query = query.filter(AlertInstance.status == status.upper())
    if severity:
        query = query.filter(AlertInstance.severity == severity.upper())
    if provider and provider.upper() != "ALL":
        query = query.filter(AlertInstance.provider == provider.upper())
    if rule_id:
        query = query.filter(AlertInstance.alert_rule_id == rule_id)
    if is_suppressed is True:
        query = query.filter(
            AlertInstance.suppress_until != None,
            AlertInstance.suppress_until > datetime.now(timezone.utc),
        )
    elif is_suppressed is False:
        query = query.filter(
            or_(
                AlertInstance.suppress_until == None,
                AlertInstance.suppress_until <= datetime.now(timezone.utc),
            )
        )
    if start_date:
        query = query.filter(AlertInstance.last_triggered_at >= start_date)
    if end_date:
        query = query.filter(AlertInstance.last_triggered_at <= end_date)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                AlertInstance.title.ilike(pattern),
                AlertInstance.service_name.ilike(pattern),
                AlertInstance.account_id.ilike(pattern),
            )
        )

    total = query.count()
    items = query.order_by(desc(AlertInstance.last_triggered_at)).offset(offset).limit(limit).all()
    return AlertInstanceListResponse(items=items, total=total)


@router.get("/alerts/stats", response_model=AlertStatsResponse, status_code=status.HTTP_200_OK)
def get_alert_statistics(
    db: Session = Depends(get_sync_db),
) -> AlertStatsResponse:
    """Returns aggregated summary metrics across all alert instances."""
    now = datetime.now(timezone.utc)
    total_alerts = db.query(func.count(AlertInstance.id)).scalar() or 0
    active_alerts = (
        db.query(func.count(AlertInstance.id))
        .filter(AlertInstance.status.in_([AlertStatus.OPEN.value, AlertStatus.ACKNOWLEDGED.value, AlertStatus.INVESTIGATING.value]))
        .scalar()
        or 0
    )
    critical_alerts = (
        db.query(func.count(AlertInstance.id))
        .filter(AlertInstance.severity == Severity.CRITICAL.value)
        .scalar()
        or 0
    )
    high_alerts = (
        db.query(func.count(AlertInstance.id))
        .filter(AlertInstance.severity == Severity.HIGH.value)
        .scalar()
        or 0
    )
    unacknowledged = (
        db.query(func.count(AlertInstance.id))
        .filter(AlertInstance.status == AlertStatus.OPEN.value)
        .scalar()
        or 0
    )
    investigating = (
        db.query(func.count(AlertInstance.id))
        .filter(AlertInstance.status == AlertStatus.INVESTIGATING.value)
        .scalar()
        or 0
    )
    resolved = (
        db.query(func.count(AlertInstance.id))
        .filter(AlertInstance.status == AlertStatus.RESOLVED.value)
        .scalar()
        or 0
    )
    suppressed = (
        db.query(func.count(AlertInstance.id))
        .filter(
            or_(
                AlertInstance.status == AlertStatus.SUPPRESSED.value,
                (AlertInstance.suppress_until != None) & (AlertInstance.suppress_until > now),
            )
        )
        .scalar()
        or 0
    )

    day_ago = now - timedelta(hours=24)
    delivery_failures_24h = (
        db.query(func.count(NotificationOutbox.id))
        .filter(
            NotificationOutbox.status.in_([NotificationDeliveryStatus.FAILED.value, NotificationDeliveryStatus.DEAD_LETTERED.value]),
            NotificationOutbox.created_at >= day_ago,
        )
        .scalar()
        or 0
    )

    return AlertStatsResponse(
        total_alerts=total_alerts,
        active_alerts=active_alerts,
        critical_alerts=critical_alerts,
        high_alerts=high_alerts,
        unacknowledged_alerts=unacknowledged,
        investigating_alerts=investigating,
        resolved_alerts=resolved,
        suppressed_alerts=suppressed,
        delivery_failures_24h=delivery_failures_24h,
    )


@router.get("/alerts/{alert_instance_id}", response_model=AlertInstanceDetailResponse, status_code=status.HTTP_200_OK)
def get_alert_detail(
    alert_instance_id: UUID,
    db: Session = Depends(get_sync_db),
) -> AlertInstanceDetailResponse:
    """Retrieves full details for an alert instance including audit history and deliveries."""
    alert = db.query(AlertInstance).filter(AlertInstance.id == alert_instance_id).first()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert instance {alert_instance_id} not found.")

    history = (
        db.query(AlertHistory)
        .filter(AlertHistory.alert_instance_id == alert_instance_id)
        .order_by(desc(AlertHistory.created_at))
        .all()
    )

    deliveries = (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.alert_instance_id == alert_instance_id)
        .order_by(desc(NotificationOutbox.created_at))
        .all()
    )

    anomaly_data = None
    if alert.anomaly:
        a = alert.anomaly
        anomaly_data = {
            "anomaly_id": str(a.id),
            "service_name": a.service_name,
            "provider": a.provider.value if hasattr(a.provider, "value") else str(a.provider),
            "anomaly_category": a.anomaly_category.value if hasattr(a.anomaly_category, "value") else str(a.anomaly_category),
            "expected_cost": str(a.expected_cost),
            "actual_cost": str(a.actual_cost),
            "estimated_excess_cost": str(a.estimated_excess_cost),
            "z_score": str(a.z_score) if a.z_score else None,
            "root_cause_analysis": a.root_cause_analysis,
        }

    base_data = AlertInstanceResponse.model_validate(alert).model_dump()
    return AlertInstanceDetailResponse(
        **base_data,
        history=[AlertHistoryResponse.model_validate(h) for h in history],
        deliveries=[NotificationOutboxResponse.model_validate(d) for d in deliveries],
        anomaly=anomaly_data,
    )


@router.post("/alerts/{alert_instance_id}/action", response_model=AlertInstanceResponse, status_code=status.HTTP_200_OK)
def execute_alert_lifecycle_action(
    alert_instance_id: UUID,
    action_in: AlertActionRequest,
    request: Request,
    db: Session = Depends(get_sync_db),
) -> AlertInstanceResponse:
    """
    Executes a lifecycle state transition (ACKNOWLEDGE, INVESTIGATE, RESOLVE, SUPPRESS, REOPEN, CLOSE).
    Enforces server-side authenticated principal resolution and records audit history.
    """
    principal = get_authenticated_principal(request, db)

    try:
        updated_alert = transition_alert_status(
            db=db,
            alert_instance_id=alert_instance_id,
            action=action_in.action,
            actor=principal.principal_id,
            notes=action_in.notes,
            suppress_hours=action_in.suppress_hours,
            ticket_ref=action_in.ticket_ref,
        )
        return updated_alert
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/alerts/{alert_instance_id}/history", response_model=List[AlertHistoryResponse], status_code=status.HTTP_200_OK)
def get_alert_history(
    alert_instance_id: UUID,
    db: Session = Depends(get_sync_db),
) -> List[AlertHistoryResponse]:
    """Retrieves state transition audit trail for a specific alert instance."""
    return (
        db.query(AlertHistory)
        .filter(AlertHistory.alert_instance_id == alert_instance_id)
        .order_by(desc(AlertHistory.created_at))
        .all()
    )


# ============================================================================
# 3. IN-APP NOTIFICATION CENTER
# ============================================================================

@router.get("/notifications", response_model=InAppNotificationListResponse, status_code=status.HTTP_200_OK)
def list_in_app_notifications(
    unread_only: bool = Query(False, description="Filter only unread notifications"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    request: Request = None,
    db: Session = Depends(get_sync_db),
) -> InAppNotificationListResponse:
    """Lists in-app notifications for the authenticated user and their role."""
    principal = get_authenticated_principal(request, db)

    query = db.query(InAppNotification).filter(
        or_(
            InAppNotification.recipient_user_id == principal.principal_id,
            InAppNotification.recipient_user_id == "all",
            InAppNotification.recipient_user_id == principal.role,
        )
    )

    if unread_only:
        query = query.filter(InAppNotification.is_read == False)

    total = query.count()
    unread_count = (
        db.query(func.count(InAppNotification.id))
        .filter(
            or_(
                InAppNotification.recipient_user_id == principal.principal_id,
                InAppNotification.recipient_user_id == "all",
                InAppNotification.recipient_user_id == principal.role,
            ),
            InAppNotification.is_read == False,
        )
        .scalar()
        or 0
    )

    items = query.order_by(desc(InAppNotification.created_at)).offset(offset).limit(limit).all()
    return InAppNotificationListResponse(items=items, total=total, unread_count=unread_count)


@router.get("/notifications/unread-count", response_model=UnreadCountResponse, status_code=status.HTTP_200_OK)
def get_unread_notification_count(
    request: Request,
    db: Session = Depends(get_sync_db),
) -> UnreadCountResponse:
    """Returns the total number of unread in-app notifications for bell badge counter."""
    principal = get_authenticated_principal(request, db)
    count = (
        db.query(func.count(InAppNotification.id))
        .filter(
            or_(
                InAppNotification.recipient_user_id == principal.principal_id,
                InAppNotification.recipient_user_id == "all",
                InAppNotification.recipient_user_id == principal.role,
            ),
            InAppNotification.is_read == False,
        )
        .scalar()
        or 0
    )
    return UnreadCountResponse(unread_count=count)


@router.post("/notifications/{notification_id}/read", response_model=InAppNotificationResponse, status_code=status.HTTP_200_OK)
def mark_notification_as_read(
    notification_id: UUID,
    request: Request,
    db: Session = Depends(get_sync_db),
) -> InAppNotificationResponse:
    """Marks a single in-app notification as read."""
    principal = get_authenticated_principal(request, db)
    notif = db.query(InAppNotification).filter(InAppNotification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification {notification_id} not found.")

    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notif)
    return notif


@router.post("/notifications/{notification_id}/unread", response_model=InAppNotificationResponse, status_code=status.HTTP_200_OK)
def mark_notification_as_unread(
    notification_id: UUID,
    request: Request,
    db: Session = Depends(get_sync_db),
) -> InAppNotificationResponse:
    """Marks a single in-app notification as unread."""
    principal = get_authenticated_principal(request, db)
    notif = db.query(InAppNotification).filter(InAppNotification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification {notification_id} not found.")

    notif.is_read = False
    notif.read_at = None
    db.commit()
    db.refresh(notif)
    return notif


@router.post("/notifications/mark-all-read", status_code=status.HTTP_200_OK)
def mark_all_notifications_read(
    request: Request,
    db: Session = Depends(get_sync_db),
) -> Dict[str, Any]:
    """Marks all pending in-app notifications as read for current authenticated user."""
    principal = get_authenticated_principal(request, db)
    now = datetime.now(timezone.utc)

    updated = (
        db.query(InAppNotification)
        .filter(
            or_(
                InAppNotification.recipient_user_id == principal.principal_id,
                InAppNotification.recipient_user_id == "all",
                InAppNotification.recipient_user_id == principal.role,
            ),
            InAppNotification.is_read == False,
        )
        .update({"is_read": True, "read_at": now}, synchronize_session=False)
    )
    db.commit()
    return {"status": "ok", "marked_read_count": updated}


# ============================================================================
# 4. NOTIFICATION DELIVERIES & OUTBOX MANAGEMENT
# ============================================================================

@router.get("/notification-deliveries/outbox", response_model=NotificationOutboxListResponse, status_code=status.HTTP_200_OK)
def list_outbox_items(
    status: Optional[str] = Query(None, description="Status filter (PENDING, RETRYING, DEAD_LETTERED, DELIVERED)"),
    channel: Optional[str] = Query(None, description="Channel filter (EMAIL, WEBHOOK, IN_APP, SLACK, TEAMS)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
) -> NotificationOutboxListResponse:
    """Lists queued notifications in the transactional outbox."""
    query = db.query(NotificationOutbox)

    if status:
        query = query.filter(NotificationOutbox.status == status.upper())
    if channel:
        query = query.filter(NotificationOutbox.channel == channel.upper())

    total = query.count()
    items = query.order_by(desc(NotificationOutbox.created_at)).offset(offset).limit(limit).all()
    return NotificationOutboxListResponse(items=items, total=total)


@router.get("/notification-deliveries/outbox/{outbox_id}", response_model=NotificationOutboxResponse, status_code=status.HTTP_200_OK)
def get_outbox_item(
    outbox_id: UUID,
    db: Session = Depends(get_sync_db),
) -> NotificationOutboxResponse:
    """Retrieves an outbox record with its historical delivery attempts."""
    item = db.query(NotificationOutbox).filter(NotificationOutbox.id == outbox_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Outbox record {outbox_id} not found.")
    return item


@router.post("/notification-deliveries/outbox/{outbox_id}/retry", response_model=OutboxRetryResponse, status_code=status.HTTP_200_OK)
def retry_outbox_delivery(
    outbox_id: UUID,
    request: Request,
    db: Session = Depends(get_sync_db),
) -> OutboxRetryResponse:
    """Manually re-queues a DEAD_LETTERED or FAILED notification. Requires ADMIN or FINOPS_ADMIN role."""
    principal = get_authenticated_principal(request, db)
    require_admin_or_finops_role(principal)

    try:
        updated = dispatcher.retry_dead_letter(db, outbox_id)
        return OutboxRetryResponse(
            outbox_id=updated.id,
            previous_status=NotificationDeliveryStatus.DEAD_LETTERED.value,
            new_status=updated.status.value if hasattr(updated.status, "value") else str(updated.status),
            scheduled_attempt=updated.next_attempt_at,
            message="Outbox item re-queued for delivery.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/notification-deliveries/outbox/{outbox_id}/cancel", response_model=NotificationOutboxResponse, status_code=status.HTTP_200_OK)
def cancel_outbox_delivery(
    outbox_id: UUID,
    request: Request,
    db: Session = Depends(get_sync_db),
) -> NotificationOutboxResponse:
    """Cancels a pending or retrying notification. Requires ADMIN or FINOPS_ADMIN role."""
    principal = get_authenticated_principal(request, db)
    require_admin_or_finops_role(principal)

    try:
        updated = dispatcher.cancel_notification(db, outbox_id)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/notification-deliveries/health", response_model=NotificationHealthResponse, status_code=status.HTTP_200_OK)
def get_notification_pipeline_health(
    db: Session = Depends(get_sync_db),
) -> NotificationHealthResponse:
    """Returns the operational health and backlog metrics of the alerting outbox pipeline."""
    pending_count = (
        db.query(func.count(NotificationOutbox.id))
        .filter(NotificationOutbox.status.in_([NotificationDeliveryStatus.PENDING.value, NotificationDeliveryStatus.RETRYING.value]))
        .scalar()
        or 0
    )
    dead_letter_count = (
        db.query(func.count(NotificationOutbox.id))
        .filter(NotificationOutbox.status == NotificationDeliveryStatus.DEAD_LETTERED.value)
        .scalar()
        or 0
    )

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    delivered_24h = (
        db.query(func.count(NotificationOutbox.id))
        .filter(
            NotificationOutbox.status == NotificationDeliveryStatus.DELIVERED.value,
            NotificationOutbox.delivered_at >= cutoff,
        )
        .scalar()
        or 0
    )
    failed_24h = (
        db.query(func.count(NotificationOutbox.id))
        .filter(
            NotificationOutbox.status.in_([NotificationDeliveryStatus.FAILED.value, NotificationDeliveryStatus.DEAD_LETTERED.value]),
            NotificationOutbox.created_at >= cutoff,
        )
        .scalar()
        or 0
    )

    email_mode = "MOCK_LOCAL_CAPTURE" if settings.NOTIFICATION_SAFE_LOCAL_MODE else (
        "LIVE_SMTP" if settings.SMTP_HOST else "DISABLED"
    )

    health_status = "HEALTHY"
    if dead_letter_count > 50 or failed_24h > delivered_24h:
        health_status = "DEGRADED"

    return NotificationHealthResponse(
        status=health_status,
        in_app_operational=True,
        email_mode=email_mode,
        webhook_operational=True,
        pending_outbox_count=pending_count,
        dead_letter_count=dead_letter_count,
        total_delivered_24h=delivered_24h,
        total_failed_24h=failed_24h,
    )


@router.post("/notification-deliveries/dispatch", status_code=status.HTTP_200_OK)
def trigger_outbox_dispatch(
    batch_size: int = Query(50, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_sync_db),
) -> Dict[str, Any]:
    """Manually triggers processing of pending outbox items."""
    principal = get_authenticated_principal(request, db)
    require_admin_or_finops_role(principal)

    results = dispatcher.process_outbox_batch(db, batch_size=batch_size)
    return {
        "status": "completed",
        "processed_count": len(results),
        "delivered": sum(1 for r in results if r.status == NotificationDeliveryStatus.DELIVERED),
        "retrying": sum(1 for r in results if r.status == NotificationDeliveryStatus.RETRYING),
        "dead_lettered": sum(1 for r in results if r.status == NotificationDeliveryStatus.DEAD_LETTERED),
    }


# ============================================================================
# 5. USER NOTIFICATION PREFERENCES
# ============================================================================

@router.get("/notification-preferences/me", response_model=NotificationPreferenceResponse, status_code=status.HTTP_200_OK)
def get_user_notification_preferences(
    request: Request,
    db: Session = Depends(get_sync_db),
) -> NotificationPreferenceResponse:
    """Retrieves alerting and notification preferences for current authenticated principal."""
    principal = get_authenticated_principal(request, db)

    pref = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == principal.principal_id)
        .first()
    )

    if not pref:
        # Create default preference record
        pref = NotificationPreference(
            id=uuid.uuid4(),
            user_id=principal.principal_id,
            user_email=principal.email or f"{principal.principal_id}@cloudsage.internal",
            enabled_channels=[NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value],
            min_severity=Severity.LOW.value,
            receive_digests=True,
            digest_frequency="DAILY",
            quiet_hours_enabled=False,
            quiet_hours_start_utc="22:00",
            quiet_hours_end_utc="08:00",
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)

    return pref


@router.put("/notification-preferences/me", response_model=NotificationPreferenceResponse, status_code=status.HTTP_200_OK)
def update_user_notification_preferences(
    pref_in: NotificationPreferenceRequest,
    request: Request,
    db: Session = Depends(get_sync_db),
) -> NotificationPreferenceResponse:
    """Updates alerting and delivery preferences for current authenticated principal."""
    principal = get_authenticated_principal(request, db)

    pref = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == principal.principal_id)
        .first()
    )

    if not pref:
        pref = NotificationPreference(
            id=uuid.uuid4(),
            user_id=principal.principal_id,
            user_email=principal.email or f"{principal.principal_id}@cloudsage.internal",
        )
        db.add(pref)

    pref.enabled_channels = pref_in.enabled_channels
    pref.min_severity = pref_in.min_severity.upper()
    pref.receive_digests = pref_in.receive_digests
    pref.digest_frequency = pref_in.digest_frequency.upper()
    pref.quiet_hours_enabled = pref_in.quiet_hours_enabled
    pref.quiet_hours_start_utc = pref_in.quiet_hours_start_utc
    pref.quiet_hours_end_utc = pref_in.quiet_hours_end_utc
    pref.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(pref)
    return pref
