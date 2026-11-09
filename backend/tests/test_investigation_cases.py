"""
Tests for Investigation Case Lifecycle, Case Management, Notes, Findings, and Governance.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
import pytest

from backend.app.core.enums import (
    ConfidenceCategory,
    FindingType,
    InvestigationPriority,
    InvestigationStatus,
)
from backend.app.investigation.service import (
    InvalidTransitionError,
    InvestigationService,
    MissingJustificationError,
)
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.investigation import (
    InvestigationCase,
    InvestigationEvidenceLink,
    InvestigationFinding,
    InvestigationHistory,
    InvestigationNote,
)
from backend.app.schemas.investigation import (
    InvestigationCaseCreate,
    InvestigationFindingCreate,
)


def _create_sample_anomaly(db_session, service="AmazonEC2", excess=Decimal("1500.5000")):
    anomaly = CostAnomaly(
        id=uuid.uuid4(),
        provider="AWS",
        account_id="123456789012",
        service_category="COMPUTE",
        service_name=service,
        region="us-east-1",
        resource_id="i-0abcdef1234567890",
        anomaly_category="SERVICE_SPIKE",
        title=f"Spike in {service}",
        anomaly_date=date(2026, 3, 15),
        actual_cost=Decimal("2000.0000"),
        expected_cost=Decimal("499.5000"),
        estimated_excess_cost=excess,
        severity="HIGH",
        status="OPEN",
        baseline_metrics={},
        root_cause_analysis={},
        contributing_resources=[],
        source_billing_references=[],
    )
    db_session.add(anomaly)
    db_session.commit()
    return anomaly


def test_create_case_from_anomaly(db_session):
    """Verifies case creation auto-generates case number, initial findings, and updates anomaly status."""
    anomaly = _create_sample_anomaly(db_session)
    service = InvestigationService(db_session)

    case_in = InvestigationCaseCreate(
        anomaly_id=anomaly.id,
        priority="HIGH",
        assigned_to="finops-lead@cloudsage.com",
        initial_notes="Initial triage started.",
    )
    case_detail = service.create_case(case_in, actor="admin@cloudsage.com")

    assert case_detail.case_number.startswith("INV-")
    assert case_detail.anomaly_id == anomaly.id
    assert case_detail.status == InvestigationStatus.ASSIGNED.value
    assert case_detail.priority == InvestigationPriority.HIGH.value
    assert case_detail.assigned_to == "finops-lead@cloudsage.com"
    assert case_detail.excess_cost == Decimal("1500.5000")

    # Verify findings were automatically generated
    assert len(case_detail.findings) > 0
    # Verify notes were recorded
    assert len(case_detail.notes) == 1
    assert case_detail.notes[0].content == "Initial triage started."
    # Verify history recorded
    assert len(case_detail.history) >= 1

    # Verify anomaly status updated
    db_session.refresh(anomaly)
    assert anomaly.status == "INVESTIGATING"


def test_create_case_idempotence(db_session):
    """Creating a second case for an active anomaly returns the existing case."""
    anomaly = _create_sample_anomaly(db_session)
    service = InvestigationService(db_session)

    case_in = InvestigationCaseCreate(anomaly_id=anomaly.id)
    c1 = service.create_case(case_in, actor="user1@cloudsage.com")
    c2 = service.create_case(case_in, actor="user2@cloudsage.com")

    assert c1.id == c2.id
    assert c1.case_number == c2.case_number


def test_assign_case(db_session):
    """Verifies assigning a case updates assigned_to, timestamps, and transitions NEW -> ASSIGNED."""
    anomaly = _create_sample_anomaly(db_session)
    service = InvestigationService(db_session)

    case_in = InvestigationCaseCreate(anomaly_id=anomaly.id)
    c = service.create_case(case_in, actor="system@cloudsage.com")
    assert c.status == InvestigationStatus.NEW.value

    updated = service.assign_case(
        case_id=c.id,
        assigned_to="engineer@cloudsage.com",
        actor="lead@cloudsage.com",
        notes="Assigning to platform engineer",
    )
    assert updated.assigned_to == "engineer@cloudsage.com"
    assert updated.status == InvestigationStatus.ASSIGNED.value
    assert updated.assigned_at is not None


def test_transition_status_valid_lifecycle(db_session):
    """Tests happy path lifecycle: ASSIGNED -> INVESTIGATING -> ROOT_CAUSE_IDENTIFIED -> RESOLVED -> CLOSED."""
    anomaly = _create_sample_anomaly(db_session)
    service = InvestigationService(db_session)

    c = service.create_case(
        InvestigationCaseCreate(anomaly_id=anomaly.id, assigned_to="lead@cloudsage.com"),
        actor="system",
    )

    # 1. ASSIGNED -> INVESTIGATING
    c = service.transition_status(c.id, InvestigationStatus.INVESTIGATING.value, actor="lead@cloudsage.com")
    assert c.status == InvestigationStatus.INVESTIGATING.value

    # 2. INVESTIGATING -> ROOT_CAUSE_IDENTIFIED (requires verified_root_cause)
    c = service.transition_status(
        c.id,
        InvestigationStatus.ROOT_CAUSE_IDENTIFIED.value,
        actor="lead@cloudsage.com",
        verified_root_cause="Autoscaling min_size misconfigured in Terraform.",
    )
    assert c.status == InvestigationStatus.ROOT_CAUSE_IDENTIFIED.value
    assert c.verified_root_cause == "Autoscaling min_size misconfigured in Terraform."

    # 3. ROOT_CAUSE_IDENTIFIED -> RESOLVED
    c = service.transition_status(
        c.id,
        InvestigationStatus.RESOLVED.value,
        actor="lead@cloudsage.com",
        notes="Remediated via PR #104. Scaled down extra instances.",
    )
    assert c.status == InvestigationStatus.RESOLVED.value

    # Linked anomaly should be RESOLVED
    db_session.refresh(anomaly)
    assert anomaly.status == "RESOLVED"

    # 4. RESOLVED -> CLOSED
    c = service.transition_status(c.id, InvestigationStatus.CLOSED.value, actor="lead@cloudsage.com")
    assert c.status == InvestigationStatus.CLOSED.value
    assert c.closed_at is not None
    assert c.closed_by == "lead@cloudsage.com"


def test_transition_status_missing_justification_error(db_session):
    """Transitioning to ROOT_CAUSE_IDENTIFIED or RESOLVED without verified cause raises MissingJustificationError."""
    anomaly = _create_sample_anomaly(db_session)
    service = InvestigationService(db_session)

    c = service.create_case(InvestigationCaseCreate(anomaly_id=anomaly.id), actor="system")
    service.transition_status(c.id, InvestigationStatus.INVESTIGATING.value, actor="user")

    with pytest.raises(MissingJustificationError):
        service.transition_status(
            c.id,
            InvestigationStatus.ROOT_CAUSE_IDENTIFIED.value,
            actor="user",
            verified_root_cause=None,
        )


def test_transition_status_invalid_transition_error(db_session):
    """Illegal transitions (e.g. NEW -> RESOLVED directly) are rejected with InvalidTransitionError."""
    anomaly = _create_sample_anomaly(db_session)
    service = InvestigationService(db_session)

    c = service.create_case(InvestigationCaseCreate(anomaly_id=anomaly.id), actor="system")
    assert c.status == InvestigationStatus.NEW.value

    with pytest.raises(InvalidTransitionError):
        service.transition_status(c.id, InvestigationStatus.RESOLVED.value, actor="user")


def test_reopen_case(db_session):
    """Closed or resolved case can be reopened back to INVESTIGATING."""
    anomaly = _create_sample_anomaly(db_session)
    service = InvestigationService(db_session)

    c = service.create_case(
        InvestigationCaseCreate(anomaly_id=anomaly.id, assigned_to="user@test.com"),
        actor="system",
    )
    service.transition_status(c.id, InvestigationStatus.INVESTIGATING.value, actor="user")
    service.transition_status(
        c.id,
        InvestigationStatus.RESOLVED.value,
        actor="user",
        notes="Done",
        verified_root_cause="Resolved",
    )
    service.transition_status(c.id, InvestigationStatus.CLOSED.value, actor="user")

    reopened = service.transition_status(
        c.id,
        InvestigationStatus.INVESTIGATING.value,
        actor="reviewer@test.com",
        notes="Spike reoccurred; reopening.",
    )
    assert reopened.status == InvestigationStatus.INVESTIGATING.value


def test_add_collaboration_notes(db_session):
    """Adding notes appends to case notes and records history."""
    anomaly = _create_sample_anomaly(db_session)
    service = InvestigationService(db_session)

    c = service.create_case(InvestigationCaseCreate(anomaly_id=anomaly.id), actor="system")
    n1 = service.add_note(c.id, content="Called infrastructure on-call.", actor="analyst1")
    n2 = service.add_note(c.id, content="On-call confirmed batch job runaway.", actor="analyst2")

    detail = service.get_case_detail(c.id)
    assert len(detail.notes) >= 2
    assert detail.notes[-1].content == "On-call confirmed batch job runaway."


def test_add_custom_finding(db_session):
    """Analyst can record custom findings with financial impact and confidence tier."""
    anomaly = _create_sample_anomaly(db_session)
    service = InvestigationService(db_session)

    c = service.create_case(InvestigationCaseCreate(anomaly_id=anomaly.id), actor="system")
    finding_in = InvestigationFindingCreate(
        finding_type=FindingType.VERIFIED_CAUSE.value,
        title="Unterminated Spark cluster on EMR",
        explanation="EMR cluster j-12345 ran for 72 hours idle with 16 core nodes.",
        dimension="RESOURCE",
        financial_impact=Decimal("1200.0000"),
        contribution_percentage=Decimal("80.00"),
        confidence_category=ConfidenceCategory.HIGH.value,
        confidence_score=Decimal("1.0000"),
        evidence_source="RESOURCE_INVENTORY",
        evidence_reference="j-12345",
        supporting_observations=["Cluster idle for 72 hours", "Zero job submissions"],
        contradictory_observations=[],
        suggested_next_step="Terminate cluster immediately.",
    )
    finding = service.add_finding(c.id, finding_in, actor="analyst@cloudsage.com")

    assert finding.id is not None
    assert finding.finding_type == FindingType.VERIFIED_CAUSE.value
    assert finding.financial_impact == Decimal("1200.0000")


def test_list_cases_filtering(db_session):
    """Queries cases with multi-dimensional filtering."""
    a1 = _create_sample_anomaly(db_session, service="AmazonEC2")
    a2 = _create_sample_anomaly(db_session, service="AmazonS3")

    service = InvestigationService(db_session)
    service.create_case(InvestigationCaseCreate(anomaly_id=a1.id, priority="CRITICAL"), actor="system")
    service.create_case(InvestigationCaseCreate(anomaly_id=a2.id, priority="LOW"), actor="system")

    crit_list = service.list_cases(priority="CRITICAL")
    assert crit_list.total >= 1
    assert all(item.priority == "CRITICAL" for item in crit_list.items)

    s3_list = service.list_cases(service_name="AmazonS3")
    assert s3_list.total >= 1
    assert all(item.service_name == "AmazonS3" for item in s3_list.items)


def test_investigation_stats(db_session):
    """Verifies global KPI aggregation for investigations."""
    a1 = _create_sample_anomaly(db_session, service="AmazonEC2", excess=Decimal("1000.0000"))
    a2 = _create_sample_anomaly(db_session, service="AmazonRDS", excess=Decimal("2500.0000"))

    service = InvestigationService(db_session)
    c1 = service.create_case(InvestigationCaseCreate(anomaly_id=a1.id, priority="CRITICAL"), actor="system")
    c2 = service.create_case(InvestigationCaseCreate(anomaly_id=a2.id, priority="MEDIUM"), actor="system")

    stats = service.get_stats()
    assert stats.total_investigations >= 2
    assert stats.critical_investigations >= 1
    assert stats.total_excess_spend_investigated >= Decimal("3500.0000")


def test_anomaly_investigation_summary(db_session):
    """Retrieves quick summary for an anomaly card."""
    anomaly = _create_sample_anomaly(db_session)
    service = InvestigationService(db_session)

    # Before investigation
    summary = service.get_anomaly_summary(anomaly.id)
    assert not summary.has_active_investigation

    # Open case
    c = service.create_case(InvestigationCaseCreate(anomaly_id=anomaly.id), actor="system")
    summary = service.get_anomaly_summary(anomaly.id)
    assert summary.has_active_investigation
    assert summary.case_number == c.case_number
    assert summary.investigation_id == c.id
