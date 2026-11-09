"""
Unit and Integration Tests for Copilot Investigation & Root Cause Natural Language Support.
Verifies intent classification for investigation queries, entity extraction,
and copilot explain integration for investigation cases.
"""

from decimal import Decimal
import uuid
import pytest
from sqlalchemy.orm import Session

from backend.app.core.enums import CopilotIntent, InvestigationPriority, InvestigationStatus
from backend.app.copilot.engine import CopilotEngine
from backend.app.copilot.intent import IntentClassifier
from backend.app.copilot.schemas import CopilotExplainRequest
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.investigation import InvestigationCase


def test_copilot_investigation_intent_classification():
    """Verifies queries about root cause, Pareto drivers, and investigations map to COST_ANOMALY_EXPLANATION."""
    test_queries = [
        "What is the root cause of this anomaly?",
        "Perform a root cause analysis on the EC2 cost surge",
        "Explain the Pareto 80/20 cost drivers for case INV-2026-00001",
        "Investigate the anomaly spike on AWS",
        "Why did this cost surge happen?",
    ]
    for q in test_queries:
        intent = IntentClassifier.classify(q)
        assert intent == CopilotIntent.COST_ANOMALY_EXPLANATION, f"Failed for query: {q}"


def test_copilot_entity_extraction_case_number():
    """Verifies case number pattern matching in natural language queries."""
    entities = IntentClassifier.extract_entities("Show me details for case INV-2026-00042 on AWS")
    assert "INV-2026-00042" in entities.get("case_numbers", [])


def test_copilot_explain_investigation_case(db_session: Session):
    """Verifies CopilotEngine explains an investigation case with findings, drivers, and actions."""
    case = InvestigationCase(
        id=uuid.uuid4(),
        case_number="INV-2026-00099",
        anomaly_id=uuid.uuid4(),
        title="Spike in DynamoDB Provisioned WCU",
        status=InvestigationStatus.ROOT_CAUSE_IDENTIFIED.value,
        priority=InvestigationPriority.HIGH.value,
        assigned_to="lead@cloudsage.com",
        provider="AWS",
        account_id="123456789012",
        service_name="AmazonDynamoDB",
        region="us-east-1",
        excess_cost=Decimal("1500.0000"),
        actual_cost=Decimal("2000.0000"),
        expected_cost=Decimal("500.0000"),
        root_cause_summary="DynamoDB auto-scaling overprovisioned WCU during batch indexing",
        verified_root_cause="Overprovisioned WCU due to disabled target tracking schedule",
        created_by="system@cloudsage.com",
    )
    db_session.add(case)
    db_session.commit()

    engine = CopilotEngine()
    req = CopilotExplainRequest(target_type="investigation", target_id=str(case.id))
    resp = engine.explain_entity(db_session, req)

    assert "INV-2026-00099" in resp.explanation
    assert "Spike in DynamoDB Provisioned WCU" in resp.title or "INV-2026-00099" in resp.title
    assert "1,500.0000" in resp.explanation
    assert "ROOT_CAUSE_IDENTIFIED" in resp.explanation
    assert "Overprovisioned WCU" in resp.explanation
    assert resp.evidence_citations is not None
    assert len(resp.evidence_citations) >= 1


def test_copilot_explain_investigation_by_case_number(db_session: Session):
    """Verifies entity explanation works when referencing case number."""
    case = InvestigationCase(
        id=uuid.uuid4(),
        case_number="INV-2026-00100",
        anomaly_id=uuid.uuid4(),
        title="Azure Cosmos DB RU Surge",
        status=InvestigationStatus.INVESTIGATING.value,
        priority=InvestigationPriority.CRITICAL.value,
        assigned_to="finops@cloudsage.com",
        provider="AZURE",
        account_id="sub-12345",
        service_name="CosmosDB",
        region="eastus",
        excess_cost=Decimal("3200.0000"),
        actual_cost=Decimal("4000.0000"),
        expected_cost=Decimal("800.0000"),
        root_cause_summary="Cross-partition fan-out queries consuming high Request Units",
        created_by="system@cloudsage.com",
    )
    db_session.add(case)
    db_session.commit()

    engine = CopilotEngine()
    req = CopilotExplainRequest(target_type="case", target_id="INV-2026-00100")
    resp = engine.explain_entity(db_session, req)

    assert "INV-2026-00100" in resp.explanation
    assert "Azure Cosmos DB RU Surge" in resp.title or "INV-2026-00100" in resp.title
    assert "3,200.0000" in resp.explanation


def test_copilot_explain_nonexistent_case(db_session: Session):
    """Verifies helpful error response when case is not found."""
    engine = CopilotEngine()
    req = CopilotExplainRequest(target_type="investigation", target_id=str(uuid.uuid4()))
    resp = engine.explain_entity(db_session, req)
    assert "no investigation case record found" in resp.explanation.lower()
