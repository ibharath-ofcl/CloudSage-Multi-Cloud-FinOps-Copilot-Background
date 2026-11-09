"""
CloudSage Investigation & Root Cause Analysis Business Logic Service.
Orchestrates investigation lifecycle, persistent case state transitions,
automated finding generation, evidence linking, and immutable audit logging.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
import uuid

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from backend.app.core.enums import (
    AlertStatus,
    AnomalyStatus,
    AuditAction,
    ConfidenceCategory,
    EvidenceSource,
    FindingType,
    InvestigationPriority,
    InvestigationStatus,
)
from backend.app.investigation.engine import InvestigationEngine
from backend.app.investigation.evidence import EvidenceManager
from backend.app.models.alert import AlertInstance
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.audit import AuditLog
from backend.app.models.investigation import (
    InvestigationCase,
    InvestigationEvidenceLink,
    InvestigationFinding,
    InvestigationHistory,
    InvestigationNote,
)
from backend.app.models.resource import CloudResource
from backend.app.schemas.investigation import (
    AnomalyInvestigationSummaryResponse,
    ContributionRankingResponse,
    CrossSignalCorrelationResponse,
    InvestigationCaseCreate,
    InvestigationCaseDetailResponse,
    InvestigationCaseListResponse,
    InvestigationCaseResponse,
    InvestigationCaseUpdate,
    InvestigationEvidenceLinkResponse,
    InvestigationFindingCreate,
    InvestigationFindingResponse,
    InvestigationHistoryResponse,
    InvestigationNoteResponse,
    InvestigationStatsResponse,
    MultiDimensionalAnalysisResponse,
    ResourceInvestigationResponse,
    TimelineAnalysisResponse,
    UsagePriceAnalysisResponse,
)


class InvalidTransitionError(ValueError):
    """Raised when an illegal investigation lifecycle status transition is attempted."""
    pass


class MissingJustificationError(ValueError):
    """Raised when required root cause or resolution justification is missing."""
    pass


VALID_INVESTIGATION_TRANSITIONS = {
    InvestigationStatus.NEW.value: [
        InvestigationStatus.ASSIGNED.value,
        InvestigationStatus.INVESTIGATING.value,
        InvestigationStatus.CLOSED.value,
    ],
    InvestigationStatus.ASSIGNED.value: [
        InvestigationStatus.INVESTIGATING.value,
        InvestigationStatus.ROOT_CAUSE_IDENTIFIED.value,
        InvestigationStatus.RESOLVED.value,
        InvestigationStatus.CLOSED.value,
    ],
    InvestigationStatus.INVESTIGATING.value: [
        InvestigationStatus.ROOT_CAUSE_IDENTIFIED.value,
        InvestigationStatus.ACTION_RECOMMENDED.value,
        InvestigationStatus.RESOLVED.value,
        InvestigationStatus.CLOSED.value,
    ],
    InvestigationStatus.ROOT_CAUSE_IDENTIFIED.value: [
        InvestigationStatus.ACTION_RECOMMENDED.value,
        InvestigationStatus.RESOLVED.value,
        InvestigationStatus.INVESTIGATING.value,
        InvestigationStatus.CLOSED.value,
    ],
    InvestigationStatus.ACTION_RECOMMENDED.value: [
        InvestigationStatus.RESOLVED.value,
        InvestigationStatus.INVESTIGATING.value,
        InvestigationStatus.CLOSED.value,
    ],
    InvestigationStatus.RESOLVED.value: [
        InvestigationStatus.CLOSED.value,
        InvestigationStatus.INVESTIGATING.value,  # Reopen
    ],
    InvestigationStatus.CLOSED.value: [
        InvestigationStatus.INVESTIGATING.value,  # Reopen
        InvestigationStatus.NEW.value,
    ],
}


class InvestigationService:
    """Manages full lifecycle of FinOps investigations and root-cause analysis."""

    def __init__(self, db: Session):
        self.db = db

    def _generate_case_number(self) -> str:
        """Generates sequential investigation case number format INV-YYYY-XXXX."""
        year = datetime.now(timezone.utc).year
        prefix = f"INV-{year}-"
        # Count existing cases this year
        count = (
            self.db.query(func.count(InvestigationCase.id))
            .filter(InvestigationCase.case_number.like(f"{prefix}%"))
            .scalar()
            or 0
        )
        return f"{prefix}{count + 1:04d}"

    def create_case(
        self,
        case_in: InvestigationCaseCreate,
        actor: str,
    ) -> InvestigationCaseDetailResponse:
        """
        Creates a new investigation case for a cost anomaly and runs automated root cause analysis.
        """
        # 1. Fetch anomaly
        anomaly = self.db.query(CostAnomaly).filter(CostAnomaly.id == case_in.anomaly_id).first()
        if not anomaly:
            raise ValueError(f"Cost anomaly {case_in.anomaly_id} not found")

        # Check if an active case already exists for this anomaly
        existing_case = (
            self.db.query(InvestigationCase)
            .filter(
                InvestigationCase.anomaly_id == anomaly.id,
                InvestigationCase.status != InvestigationStatus.CLOSED.value,
            )
            .first()
        )
        if existing_case:
            return self.get_case_detail(existing_case.id)

        # 2. Determine initial status & priority
        initial_status = (
            InvestigationStatus.ASSIGNED.value
            if case_in.assigned_to
            else InvestigationStatus.NEW.value
        )
        priority = case_in.priority or InvestigationPriority.MEDIUM.value
        if anomaly.severity == "CRITICAL":
            priority = InvestigationPriority.CRITICAL.value

        title = case_in.title or (
            f"Investigation: {anomaly.title or f'{anomaly.provider} {anomaly.service_name} Cost Spike'}"
        )

        case_number = self._generate_case_number()
        now = datetime.now(timezone.utc)

        case = InvestigationCase(
            id=uuid.uuid4(),
            case_number=case_number,
            anomaly_id=anomaly.id,
            alert_instance_id=case_in.alert_instance_id,
            title=title,
            status=initial_status,
            priority=priority,
            assigned_to=case_in.assigned_to,
            assigned_at=now if case_in.assigned_to else None,
            provider=anomaly.provider,
            account_id=anomaly.account_id,
            service_name=anomaly.service_name,
            region=anomaly.region,
            resource_id=anomaly.resource_id,
            excess_cost=anomaly.estimated_excess_cost,
            actual_cost=anomaly.actual_cost,
            expected_cost=anomaly.expected_cost,
            root_cause_summary=f"Automated root-cause analysis initiated for {anomaly.service_name} spending spike.",
            created_by=actor,
            updated_by=actor,
            created_at=now,
            updated_at=now,
        )
        self.db.add(case)
        self.db.flush()

        # Update anomaly state to INVESTIGATING
        anomaly.status = AnomalyStatus.INVESTIGATING.value

        # Update alert instance if present
        if case_in.alert_instance_id:
            alert = self.db.query(AlertInstance).filter(AlertInstance.id == case_in.alert_instance_id).first()
            if alert and alert.status in [AlertStatus.OPEN.value, AlertStatus.ACKNOWLEDGED.value]:
                alert.status = AlertStatus.INVESTIGATING.value

        # 3. Run automated root cause analysis
        engine = InvestigationEngine(self.db)
        analysis_result = engine.run_full_analysis(anomaly=anomaly, investigation_id=case.id)

        # Persist synthesized findings
        created_findings = []
        for f_data in analysis_result["findings"]:
            finding = InvestigationFinding(
                id=uuid.uuid4(),
                investigation_id=case.id,
                finding_type=f_data["finding_type"],
                title=f_data["title"],
                explanation=f_data["explanation"],
                dimension=f_data.get("dimension"),
                financial_impact=f_data.get("financial_impact", Decimal("0.0000")),
                contribution_percentage=f_data.get("contribution_percentage", Decimal("0.00")),
                confidence_category=f_data.get("confidence_category", ConfidenceCategory.MEDIUM.value),
                confidence_score=f_data.get("confidence_score", Decimal("1.0000")),
                evidence_source=f_data.get("evidence_source", EvidenceSource.BILLING_RECORD.value),
                evidence_reference=f_data.get("evidence_reference"),
                supporting_observations=f_data.get("supporting_observations", []),
                contradictory_observations=f_data.get("contradictory_observations", []),
                suggested_next_step=f_data.get("suggested_next_step"),
                created_by="system:root_cause_engine",
                created_at=now,
            )
            self.db.add(finding)
            created_findings.append(finding)

        # 4. Link evidence
        EvidenceManager.link_evidence(
            db=self.db,
            investigation_id=case.id,
            entity_type="COST_ANOMALY",
            entity_id=str(anomaly.id),
            relationship_role="PRIMARY_TRIGGER",
            metadata_snapshot={
                "actual_cost": float(anomaly.actual_cost),
                "expected_cost": float(anomaly.expected_cost),
                "excess_cost": float(anomaly.estimated_excess_cost),
                "anomaly_date": str(anomaly.anomaly_date),
            },
        )
        if anomaly.resource_id:
            EvidenceManager.link_evidence(
                db=self.db,
                investigation_id=case.id,
                entity_type="CLOUD_RESOURCE",
                entity_id=anomaly.resource_id,
                relationship_role="PRIMARY_AFFECTED_RESOURCE",
                metadata_snapshot={
                    "provider": anomaly.provider,
                    "service_name": anomaly.service_name,
                    "region": anomaly.region,
                },
            )

        # 5. Add initial note if provided
        if case_in.initial_notes:
            note = InvestigationNote(
                id=uuid.uuid4(),
                investigation_id=case.id,
                author=actor,
                content=case_in.initial_notes,
                is_system_generated=False,
                created_at=now,
            )
            self.db.add(note)

        # 6. Record State History
        history = InvestigationHistory(
            id=uuid.uuid4(),
            investigation_id=case.id,
            from_status=None,
            to_status=initial_status,
            actor=actor,
            action="CASE_CREATED",
            notes=case_in.initial_notes or "Investigation case opened.",
            details={
                "case_number": case.case_number,
                "priority": case.priority,
                "assigned_to": case.assigned_to,
                "findings_generated": len(created_findings),
            },
            created_at=now,
        )
        self.db.add(history)

        # 7. Audit Log
        audit = AuditLog(
            id=uuid.uuid4(),
            timestamp=now,
            user_email=actor,
            action_type=AuditAction.INVESTIGATION_CREATE.value,
            resource_type="investigation_cases",
            resource_id=str(case.id),
            after_state={
                "case_number": case.case_number,
                "anomaly_id": str(anomaly.id),
                "priority": case.priority,
            },
        )
        self.db.add(audit)
        self.db.commit()

        return self.get_case_detail(case.id)

    def assign_case(
        self,
        case_id: UUID,
        assigned_to: str,
        actor: str,
        notes: Optional[str] = None,
    ) -> InvestigationCaseDetailResponse:
        """Assigns an investigation case to a FinOps engineer or team owner."""
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Investigation case {case_id} not found")

        prev_assignee = case.assigned_to
        now = datetime.now(timezone.utc)
        case.assigned_to = assigned_to
        case.assigned_at = now
        case.updated_by = actor
        case.updated_at = now

        # Transition NEW -> ASSIGNED if unassigned
        prev_status = case.status
        if case.status == InvestigationStatus.NEW.value:
            case.status = InvestigationStatus.ASSIGNED.value

        history = InvestigationHistory(
            id=uuid.uuid4(),
            investigation_id=case.id,
            from_status=prev_status,
            to_status=case.status,
            actor=actor,
            action="CASE_ASSIGNED",
            notes=notes or f"Case assigned from '{prev_assignee or 'unassigned'}' to '{assigned_to}'.",
            details={"previous_assignee": prev_assignee, "new_assignee": assigned_to},
            created_at=now,
        )
        self.db.add(history)

        audit = AuditLog(
            id=uuid.uuid4(),
            timestamp=now,
            user_email=actor,
            action_type=AuditAction.INVESTIGATION_ASSIGN.value,
            resource_type="investigation_cases",
            resource_id=str(case.id),
            before_state={"assigned_to": prev_assignee},
            after_state={"assigned_to": assigned_to, "case_number": case.case_number},
        )
        self.db.add(audit)
        self.db.commit()

        return self.get_case_detail(case.id)

    def transition_status(
        self,
        case_id: UUID,
        target_status: str,
        actor: str,
        notes: Optional[str] = None,
        verified_root_cause: Optional[str] = None,
    ) -> InvestigationCaseDetailResponse:
        """Transitions case status enforcing valid lifecycle paths and governance rules."""
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Investigation case {case_id} not found")

        target_status = target_status.upper()
        allowed = VALID_INVESTIGATION_TRANSITIONS.get(case.status, [])
        if target_status not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition investigation from '{case.status}' to '{target_status}'. "
                f"Valid target statuses: {allowed}"
            )

        if target_status in [InvestigationStatus.ROOT_CAUSE_IDENTIFIED.value, InvestigationStatus.RESOLVED.value]:
            if not verified_root_cause and not case.verified_root_cause:
                raise MissingJustificationError(
                    f"Transition to {target_status} requires 'verified_root_cause' explanation."
                )

        now = datetime.now(timezone.utc)
        prev_status = case.status
        case.status = target_status
        case.updated_by = actor
        case.updated_at = now

        if verified_root_cause:
            case.verified_root_cause = verified_root_cause
        if notes:
            if target_status == InvestigationStatus.RESOLVED.value:
                case.resolution_notes = notes

        # If resolved, update linked anomaly
        if target_status == InvestigationStatus.RESOLVED.value:
            anomaly = self.db.query(CostAnomaly).filter(CostAnomaly.id == case.anomaly_id).first()
            if anomaly:
                anomaly.status = AnomalyStatus.RESOLVED.value
                anomaly.resolved_by = actor
                anomaly.resolution_reason = notes or verified_root_cause or "Resolved via investigation."

        if target_status == InvestigationStatus.CLOSED.value:
            case.closed_at = now
            case.closed_by = actor

        history = InvestigationHistory(
            id=uuid.uuid4(),
            investigation_id=case.id,
            from_status=prev_status,
            to_status=target_status,
            actor=actor,
            action=f"TRANSITION_TO_{target_status}",
            notes=notes or f"Status changed from {prev_status} to {target_status}.",
            details={"verified_root_cause": verified_root_cause},
            created_at=now,
        )
        self.db.add(history)

        audit = AuditLog(
            id=uuid.uuid4(),
            timestamp=now,
            user_email=actor,
            action_type=AuditAction.INVESTIGATION_TRANSITION.value,
            resource_type="investigation_cases",
            resource_id=str(case.id),
            before_state={"status": prev_status},
            after_state={"status": target_status, "verified_root_cause": verified_root_cause},
        )
        self.db.add(audit)
        self.db.commit()

        return self.get_case_detail(case.id)

    def add_note(
        self,
        case_id: UUID,
        content: str,
        actor: str,
    ) -> InvestigationNoteResponse:
        """Adds a collaboration or diagnostic note to an investigation."""
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Investigation case {case_id} not found")

        now = datetime.now(timezone.utc)
        note = InvestigationNote(
            id=uuid.uuid4(),
            investigation_id=case.id,
            author=actor,
            content=content,
            is_system_generated=False,
            created_at=now,
        )
        self.db.add(note)
        case.updated_at = now
        case.updated_by = actor

        history = InvestigationHistory(
            id=uuid.uuid4(),
            investigation_id=case.id,
            from_status=case.status,
            to_status=case.status,
            actor=actor,
            action="NOTE_ADDED",
            notes=f"Note added: {content[:80]}...",
            details={"note_id": str(note.id)},
            created_at=now,
        )
        self.db.add(history)
        self.db.commit()

        return InvestigationNoteResponse.model_validate(note)

    def add_finding(
        self,
        case_id: UUID,
        finding_in: InvestigationFindingCreate,
        actor: str,
    ) -> InvestigationFindingResponse:
        """Adds a verified finding or analyst hypothesis to an investigation."""
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Investigation case {case_id} not found")

        now = datetime.now(timezone.utc)
        finding = InvestigationFinding(
            id=uuid.uuid4(),
            investigation_id=case.id,
            finding_type=finding_in.finding_type,
            title=finding_in.title,
            explanation=finding_in.explanation,
            dimension=finding_in.dimension,
            financial_impact=finding_in.financial_impact,
            contribution_percentage=finding_in.contribution_percentage,
            confidence_category=finding_in.confidence_category,
            confidence_score=finding_in.confidence_score,
            evidence_source=finding_in.evidence_source,
            evidence_reference=finding_in.evidence_reference,
            supporting_observations=finding_in.supporting_observations,
            contradictory_observations=finding_in.contradictory_observations,
            suggested_next_step=finding_in.suggested_next_step,
            created_by=actor,
            created_at=now,
        )
        self.db.add(finding)
        case.updated_at = now
        case.updated_by = actor

        history = InvestigationHistory(
            id=uuid.uuid4(),
            investigation_id=case.id,
            from_status=case.status,
            to_status=case.status,
            actor=actor,
            action="FINDING_ADDED",
            notes=f"Finding recorded: [{finding_in.finding_type}] {finding_in.title}",
            details={"finding_type": finding_in.finding_type, "impact": float(finding_in.financial_impact)},
            created_at=now,
        )
        self.db.add(history)
        self.db.commit()

        return InvestigationFindingResponse.model_validate(finding)

    def get_case_detail(self, case_id: UUID) -> InvestigationCaseDetailResponse:
        """Retrieves complete investigation case details with child collections."""
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Investigation case {case_id} not found")

        findings = (
            self.db.query(InvestigationFinding)
            .filter(InvestigationFinding.investigation_id == case.id)
            .order_by(InvestigationFinding.financial_impact.desc(), InvestigationFinding.created_at.asc())
            .all()
        )
        notes = (
            self.db.query(InvestigationNote)
            .filter(InvestigationNote.investigation_id == case.id)
            .order_by(InvestigationNote.created_at.asc())
            .all()
        )
        evidence_links = (
            self.db.query(InvestigationEvidenceLink)
            .filter(InvestigationEvidenceLink.investigation_id == case.id)
            .order_by(InvestigationEvidenceLink.created_at.asc())
            .all()
        )
        history = (
            self.db.query(InvestigationHistory)
            .filter(InvestigationHistory.investigation_id == case.id)
            .order_by(InvestigationHistory.created_at.desc())
            .all()
        )

        anomaly = self.db.query(CostAnomaly).filter(CostAnomaly.id == case.anomaly_id).first()
        anomaly_dict = None
        if anomaly:
            anomaly_dict = {
                "id": str(anomaly.id),
                "title": anomaly.title,
                "anomaly_category": anomaly.anomaly_category,
                "detection_method": anomaly.detection_method,
                "anomaly_date": str(anomaly.anomaly_date),
                "actual_cost": float(anomaly.actual_cost),
                "expected_cost": float(anomaly.expected_cost),
                "estimated_excess_cost": float(anomaly.estimated_excess_cost),
                "severity": anomaly.severity,
                "status": anomaly.status,
            }

        return InvestigationCaseDetailResponse(
            id=case.id,
            case_number=case.case_number,
            anomaly_id=case.anomaly_id,
            alert_instance_id=case.alert_instance_id,
            title=case.title,
            status=case.status,
            priority=case.priority,
            assigned_to=case.assigned_to,
            assigned_at=case.assigned_at,
            provider=case.provider,
            account_id=case.account_id,
            service_name=case.service_name,
            region=case.region,
            resource_id=case.resource_id,
            excess_cost=case.excess_cost,
            actual_cost=case.actual_cost,
            expected_cost=case.expected_cost,
            root_cause_summary=case.root_cause_summary,
            verified_root_cause=case.verified_root_cause,
            suspected_category=case.suspected_category,
            resolution_notes=case.resolution_notes,
            created_by=case.created_by,
            updated_by=case.updated_by,
            created_at=case.created_at,
            updated_at=case.updated_at,
            closed_at=case.closed_at,
            closed_by=case.closed_by,
            findings=[InvestigationFindingResponse.model_validate(f) for f in findings],
            notes=[InvestigationNoteResponse.model_validate(n) for n in notes],
            evidence_links=[InvestigationEvidenceLinkResponse.model_validate(e) for e in evidence_links],
            history=[InvestigationHistoryResponse.model_validate(h) for h in history],
            anomaly_details=anomaly_dict,
        )

    def list_cases(
        self,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None,
        service_name: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> InvestigationCaseListResponse:
        """Queries investigation cases with multi-dimensional filtering and pagination."""
        query = self.db.query(InvestigationCase)

        if provider and provider.upper() != "ALL":
            query = query.filter(InvestigationCase.provider == provider.upper())
        if status:
            query = query.filter(InvestigationCase.status == status.upper())
        if priority:
            query = query.filter(InvestigationCase.priority == priority.upper())
        if assigned_to:
            if assigned_to == "unassigned":
                query = query.filter(InvestigationCase.assigned_to.is_(None))
            else:
                query = query.filter(InvestigationCase.assigned_to == assigned_to)
        if service_name:
            query = query.filter(InvestigationCase.service_name == service_name)
        if search:
            pat = f"%{search}%"
            query = query.filter(
                or_(
                    InvestigationCase.case_number.ilike(pat),
                    InvestigationCase.title.ilike(pat),
                    InvestigationCase.service_name.ilike(pat),
                    InvestigationCase.resource_id.ilike(pat),
                )
            )

        total = query.count()
        items = query.order_by(desc(InvestigationCase.created_at)).offset(offset).limit(limit).all()

        return InvestigationCaseListResponse(
            items=[InvestigationCaseResponse.model_validate(i) for i in items],
            total=total,
        )

    def get_stats(self) -> InvestigationStatsResponse:
        """Calculates global investigation KPI summary metrics."""
        cases = self.db.query(InvestigationCase).all()
        total_count = len(cases)
        open_count = sum(1 for c in cases if c.status not in [InvestigationStatus.RESOLVED.value, InvestigationStatus.CLOSED.value])
        critical_count = sum(1 for c in cases if c.priority == InvestigationPriority.CRITICAL.value and c.status != InvestigationStatus.CLOSED.value)
        unassigned_count = sum(1 for c in cases if not c.assigned_to and c.status != InvestigationStatus.CLOSED.value)
        identified_count = sum(1 for c in cases if c.status == InvestigationStatus.ROOT_CAUSE_IDENTIFIED.value)
        resolved_count = sum(1 for c in cases if c.status == InvestigationStatus.RESOLVED.value)
        total_excess = sum((c.excess_cost for c in cases), Decimal("0.0000"))

        now = datetime.now(timezone.utc)
        open_ages = [
            Decimal(str((now - (c.created_at.replace(tzinfo=timezone.utc) if c.created_at.tzinfo is None else c.created_at)).total_seconds() / 3600.0))
            for c in cases
            if c.status not in [InvestigationStatus.RESOLVED.value, InvestigationStatus.CLOSED.value]
        ]
        avg_age = (sum(open_ages) / Decimal(str(len(open_ages)))) if open_ages else Decimal("0.00")

        return InvestigationStatsResponse(
            total_investigations=total_count,
            open_investigations=open_count,
            critical_investigations=critical_count,
            unassigned_investigations=unassigned_count,
            root_cause_identified_count=identified_count,
            resolved_investigations=resolved_count,
            total_excess_spend_investigated=total_excess.quantize(Decimal("0.0001")),
            average_investigation_age_hours=avg_age.quantize(Decimal("0.01")),
        )

    # --- Analytical Slices ---

    def get_dimensional_analysis(self, case_id: UUID) -> MultiDimensionalAnalysisResponse:
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Investigation case {case_id} not found")
        anomaly = self.db.query(CostAnomaly).filter(CostAnomaly.id == case.anomaly_id).first()
        if not anomaly:
            raise ValueError(f"Cost anomaly {case.anomaly_id} not found")

        engine = InvestigationEngine(self.db)
        res = engine.run_full_analysis(anomaly=anomaly, investigation_id=case.id)
        return res["dimensions"]

    def get_contribution_ranking(self, case_id: UUID) -> ContributionRankingResponse:
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Investigation case {case_id} not found")
        anomaly = self.db.query(CostAnomaly).filter(CostAnomaly.id == case.anomaly_id).first()
        if not anomaly:
            raise ValueError(f"Cost anomaly {case.anomaly_id} not found")

        engine = InvestigationEngine(self.db)
        res = engine.run_full_analysis(anomaly=anomaly, investigation_id=case.id)
        return res["contributions"]

    def get_usage_price_analysis(self, case_id: UUID) -> UsagePriceAnalysisResponse:
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Investigation case {case_id} not found")
        anomaly = self.db.query(CostAnomaly).filter(CostAnomaly.id == case.anomaly_id).first()
        if not anomaly:
            raise ValueError(f"Cost anomaly {case.anomaly_id} not found")

        engine = InvestigationEngine(self.db)
        res = engine.run_full_analysis(anomaly=anomaly, investigation_id=case.id)
        return res["usage_price"]

    def get_timeline_analysis(self, case_id: UUID) -> TimelineAnalysisResponse:
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Investigation case {case_id} not found")
        anomaly = self.db.query(CostAnomaly).filter(CostAnomaly.id == case.anomaly_id).first()
        if not anomaly:
            raise ValueError(f"Cost anomaly {case.anomaly_id} not found")

        engine = InvestigationEngine(self.db)
        res = engine.run_full_analysis(anomaly=anomaly, investigation_id=case.id)
        return res["timeline"]

    def get_resource_investigation(self, case_id: UUID) -> ResourceInvestigationResponse:
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Investigation case {case_id} not found")
        anomaly = self.db.query(CostAnomaly).filter(CostAnomaly.id == case.anomaly_id).first()
        if not anomaly:
            raise ValueError(f"Cost anomaly {case.anomaly_id} not found")

        engine = InvestigationEngine(self.db)
        res = engine.run_full_analysis(anomaly=anomaly, investigation_id=case.id)
        return res["resources"]

    def get_cross_signals(self, case_id: UUID) -> CrossSignalCorrelationResponse:
        case = self.db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
        if not case:
            raise ValueError(f"Investigation case {case_id} not found")
        anomaly = self.db.query(CostAnomaly).filter(CostAnomaly.id == case.anomaly_id).first()
        if not anomaly:
            raise ValueError(f"Cost anomaly {case.anomaly_id} not found")

        engine = InvestigationEngine(self.db)
        res = engine.run_full_analysis(anomaly=anomaly, investigation_id=case.id)
        return res["correlations"]

    def get_anomaly_summary(self, anomaly_id: UUID) -> AnomalyInvestigationSummaryResponse:
        """Retrieves investigation summary status for an anomaly card or detail view."""
        anomaly = self.db.query(CostAnomaly).filter(CostAnomaly.id == anomaly_id).first()
        if not anomaly:
            raise ValueError(f"Cost anomaly {anomaly_id} not found")

        case = (
            self.db.query(InvestigationCase)
            .filter(InvestigationCase.anomaly_id == anomaly.id)
            .order_by(desc(InvestigationCase.created_at))
            .first()
        )

        if not case:
            return AnomalyInvestigationSummaryResponse(
                anomaly_id=anomaly.id,
                has_active_investigation=False,
                investigation_id=None,
                case_number=None,
                status=None,
                assigned_to=None,
                priority=None,
                excess_cost=anomaly.estimated_excess_cost,
                primary_root_cause=None,
                confidence_category=ConfidenceCategory.INSUFFICIENT_EVIDENCE.value,
                finding_count=0,
            )

        finding_count = (
            self.db.query(func.count(InvestigationFinding.id))
            .filter(InvestigationFinding.investigation_id == case.id)
            .scalar()
            or 0
        )

        return AnomalyInvestigationSummaryResponse(
            anomaly_id=anomaly.id,
            has_active_investigation=True,
            investigation_id=case.id,
            case_number=case.case_number,
            status=case.status,
            assigned_to=case.assigned_to,
            priority=case.priority,
            excess_cost=case.excess_cost,
            primary_root_cause=case.verified_root_cause or case.root_cause_summary,
            confidence_category=ConfidenceCategory.HIGH.value if case.verified_root_cause else ConfidenceCategory.MEDIUM.value,
            finding_count=finding_count,
        )
