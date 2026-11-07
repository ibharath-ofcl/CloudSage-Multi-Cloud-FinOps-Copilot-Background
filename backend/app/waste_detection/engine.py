"""
CloudSage Waste Detection Engine.
Orchestrates multi-cloud resource evaluation, evidence aggregation, finding deduplication,
lifecycle state transitions, and audit run tracking.
Strictly non-destructive and advisory-only.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.core.enums import WasteStatus, WasteType
from backend.app.models.billing import BillingRecord
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.models.waste import WasteDetection, WasteDetectionRun
from backend.app.waste_detection.base import BaseWasteDetector
from backend.app.waste_detection.models import DetectorExecutionResult, WasteFinding
from backend.app.waste_detection.registry import DetectorRegistry


class WasteDetectionEngine:
    """Core execution engine for evidence-based multi-cloud waste detection."""

    @classmethod
    def execute_detection_run(
        cls,
        db: Session,
        provider: Optional[str] = "ALL",
        account_id: Optional[str] = None,
        detectors: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        lookback_days: int = 7,
    ) -> WasteDetectionRun:
        """
        Executes bounded, transaction-safe detection run across cloud resources.
        Guarantees zero duplicate open findings.
        """
        now = datetime.now(timezone.utc)
        prov_filter = provider.upper() if provider else "ALL"

        run = WasteDetectionRun(
            provider=prov_filter,
            status="RUNNING",
            started_at=now,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # 1. Select Active Detectors
        active_detectors: List[BaseWasteDetector] = []
        if detectors:
            for d_id in detectors:
                try:
                    active_detectors.append(DetectorRegistry.get_detector(d_id))
                except Exception:
                    pass
        else:
            all_dets = DetectorRegistry.list_detectors(provider=None if prov_filter == "ALL" else prov_filter)
            if categories:
                cats_upper = [c.upper() for c in categories]
                all_dets = [d for d in all_dets if d.waste_category.value in cats_upper or d.waste_category.name in cats_upper]
            active_detectors = all_dets

        # 2. Query Eligible Resources
        res_query = db.query(CloudResource)
        if prov_filter != "ALL":
            res_query = res_query.filter(CloudResource.provider == prov_filter)
        if account_id:
            res_query = res_query.filter(CloudResource.account_id == account_id)

        resources: List[CloudResource] = res_query.all()

        findings_created = 0
        findings_updated = 0
        findings_unchanged = 0
        total_savings = Decimal("0.0000")
        detector_stats: Dict[str, Dict[str, int]] = {d.detector_id: {"detected": 0, "clean": 0, "insufficient_data": 0} for d in active_detectors}
        errors: List[Dict[str, Any]] = []

        # 3. Batch Evaluation
        for res in resources:
            res_metrics: List[ResourceMetric] = (
                db.query(ResourceMetric)
                .filter(ResourceMetric.resource_id == res.resource_id)
                .all()
            )

            res_rels: List[ResourceRelationship] = (
                db.query(ResourceRelationship)
                .filter(
                    (ResourceRelationship.source_resource_id == res.resource_id)
                    | (ResourceRelationship.target_resource_id == res.resource_id)
                )
                .all()
            )

            res_bills: List[BillingRecord] = (
                db.query(BillingRecord)
                .filter(BillingRecord.resource_id == res.resource_id)
                .all()
            )

            for det in active_detectors:
                # Check provider compatibility
                if "ALL" not in det.supported_providers and res.provider.upper() not in det.supported_providers:
                    continue

                try:
                    result: DetectorExecutionResult = det.detect(
                        resource=res,
                        metrics=res_metrics,
                        relationships=res_rels,
                        billing_records=res_bills,
                        thresholds={"min_observation_days": lookback_days},
                    )

                    stats = detector_stats.setdefault(det.detector_id, {"detected": 0, "clean": 0, "insufficient_data": 0})

                    if result.status == "DETECTED" and result.finding:
                        stats["detected"] += 1
                        f = result.finding
                        total_savings += f.estimated_monthly_savings

                        # Deduplication and Lifecycle Management
                        existing_finding: Optional[WasteDetection] = (
                            db.query(WasteDetection)
                            .filter(
                                WasteDetection.resource_id == res.resource_id,
                                WasteDetection.waste_type == f.waste_type.value,
                            )
                            .first()
                        )

                        if existing_finding:
                            # If previously resolved and now waste is detected again: REOPEN
                            if existing_finding.status in ("RESOLVED", "DISMISSED"):
                                existing_finding.status = "REOPENED"
                            elif existing_finding.status in ("ACTIVE", "OPEN"):
                                findings_updated += 1
                            else:
                                findings_unchanged += 1

                            existing_finding.detector_id = f.detector_id
                            existing_finding.detector_version = f.detector_version
                            existing_finding.finding_title = f.finding_title
                            existing_finding.explanation = f.explanation
                            existing_finding.severity = f.severity.value
                            existing_finding.confidence_score = f.confidence_score
                            existing_finding.estimated_monthly_waste = f.estimated_monthly_savings
                            existing_finding.last_evaluated_at = now
                            existing_finding.telemetry_proof = f.evidence
                            existing_finding.observation_window_days = f.observation_window_days
                        else:
                            # Create brand new finding
                            new_finding = WasteDetection(
                                resource_id=f.resource_id,
                                provider=f.provider,
                                account_id=f.account_id or res.account_id,
                                resource_type=f.resource_type,
                                detector_id=f.detector_id,
                                detector_version=f.detector_version,
                                waste_type=f.waste_type.value,
                                finding_title=f.finding_title,
                                explanation=f.explanation,
                                severity=f.severity.value,
                                status=WasteStatus.ACTIVE.value,
                                confidence_score=f.confidence_score,
                                estimated_monthly_waste=f.estimated_monthly_savings,
                                currency=f.currency,
                                observation_window_days=f.observation_window_days,
                                data_quality_status=f.data_quality_status,
                                requires_human_review=f.requires_human_review,
                                telemetry_proof=f.evidence,
                                first_detected_at=now,
                                last_evaluated_at=now,
                                detected_at=now,
                            )
                            db.add(new_finding)
                            findings_created += 1

                    elif result.status == "CLEAN":
                        stats["clean"] += 1
                        # If finding previously open, resolve it
                        open_finding = (
                            db.query(WasteDetection)
                            .filter(
                                WasteDetection.resource_id == res.resource_id,
                                WasteDetection.waste_type == det.waste_category.value,
                                WasteDetection.status.in_(["ACTIVE", "OPEN", "REOPENED"]),
                            )
                            .first()
                        )
                        if open_finding:
                            open_finding.status = "RESOLVED"
                            open_finding.last_evaluated_at = now

                    elif result.status == "INSUFFICIENT_DATA":
                        stats["insufficient_data"] += 1

                except Exception as ex:
                    errors.append({
                        "detector_id": det.detector_id,
                        "resource_id": res.resource_id,
                        "error": str(ex),
                    })

        # 4. Finalize Run Record
        run.total_resources_evaluated = len(resources)
        run.findings_created = findings_created
        run.findings_updated = findings_updated
        run.findings_unchanged = findings_unchanged
        run.total_estimated_monthly_savings = total_savings
        run.detector_summary = detector_stats
        run.error_details = errors
        run.completed_at = datetime.now(timezone.utc)
        run.status = "COMPLETED" if not errors else "PARTIAL_SUCCESS"

        db.commit()
        db.refresh(run)
        return run

    @classmethod
    def list_findings(
        cls,
        db: Session,
        provider: Optional[str] = None,
        account_id: Optional[str] = None,
        waste_type: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        min_savings: Optional[Decimal] = None,
        owner: Optional[str] = None,
        environment: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Queries waste findings with multi-attribute filtering and pagination."""
        query = db.query(WasteDetection).join(CloudResource, WasteDetection.resource_id == CloudResource.resource_id)

        if provider and provider.upper() != "ALL":
            query = query.filter(WasteDetection.provider == provider.upper())
        if account_id:
            query = query.filter(WasteDetection.account_id == account_id)
        if waste_type:
            query = query.filter(WasteDetection.waste_type == waste_type.upper())
        if severity:
            query = query.filter(WasteDetection.severity == severity.upper())
        if status:
            query = query.filter(WasteDetection.status == status.upper())
        if min_savings is not None:
            query = query.filter(WasteDetection.estimated_monthly_waste >= min_savings)
        if owner:
            query = query.filter(CloudResource.owner.ilike(f"%{owner}%"))
        if environment:
            query = query.filter(CloudResource.environment == environment.lower())

        total = query.count()
        findings = query.order_by(WasteDetection.estimated_monthly_waste.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "items": findings,
            "limit": limit,
            "offset": offset,
        }

    @classmethod
    def get_summary(cls, db: Session) -> Dict[str, Any]:
        """Calculates executive KPI metrics across open and active waste findings."""
        active_statuses = ["ACTIVE", "OPEN", "REOPENED", "ACKNOWLEDGED"]
        base_query = db.query(WasteDetection).filter(WasteDetection.status.in_(active_statuses))

        total_findings = base_query.count()
        total_savings = base_query.with_entities(func.sum(WasteDetection.estimated_monthly_waste)).scalar() or Decimal("0.0000")

        # Severity breakdown
        sev_rows = (
            base_query.with_entities(WasteDetection.severity, func.count(WasteDetection.id))
            .group_by(WasteDetection.severity)
            .all()
        )
        findings_by_severity = {row[0]: row[1] for row in sev_rows}

        # Category breakdown
        cat_rows = (
            base_query.with_entities(
                WasteDetection.waste_type,
                func.count(WasteDetection.id).label("count"),
                func.sum(WasteDetection.estimated_monthly_waste).label("savings"),
            )
            .group_by(WasteDetection.waste_type)
            .all()
        )
        findings_by_category = {row.waste_type: row.count for row in cat_rows}
        savings_by_category = {row.waste_type: Decimal(str(row.savings or "0.0000")) for row in cat_rows}

        # Provider breakdown
        prov_rows = (
            base_query.with_entities(
                WasteDetection.provider,
                func.count(WasteDetection.id).label("count"),
                func.sum(WasteDetection.estimated_monthly_waste).label("savings"),
            )
            .group_by(WasteDetection.provider)
            .all()
        )
        findings_by_provider = {row.provider: row.count for row in prov_rows}
        savings_by_provider = {row.provider: Decimal(str(row.savings or "0.0000")) for row in prov_rows}

        return {
            "total_open_findings": total_findings,
            "total_estimated_monthly_savings": Decimal(str(total_savings)),
            "findings_by_severity": findings_by_severity,
            "findings_by_category": findings_by_category,
            "findings_by_provider": findings_by_provider,
            "savings_by_category": savings_by_category,
            "savings_by_provider": savings_by_provider,
        }

    @classmethod
    def update_finding_status(
        cls,
        db: Session,
        finding_id: uuid.UUID,
        new_status: str,
        reason: Optional[str] = None,
        user: Optional[str] = None,
        snooze_days: Optional[int] = None,
    ) -> Optional[WasteDetection]:
        """Handles human review state transitions (ACKNOWLEDGED, DISMISSED, RESOLVED, SNOOZED)."""
        finding = db.query(WasteDetection).filter(WasteDetection.id == finding_id).first()
        if not finding:
            return None

        status_upper = new_status.upper().strip()
        finding.status = status_upper
        finding.last_evaluated_at = datetime.now(timezone.utc)

        if reason:
            finding.dismissal_reason = reason
        if user:
            finding.dismissed_by = user

        if status_upper == "SNOOZED" and snooze_days:
            from datetime import timedelta
            finding.snooze_until = datetime.now(timezone.utc) + timedelta(days=snooze_days)

        db.commit()
        db.refresh(finding)
        return finding
