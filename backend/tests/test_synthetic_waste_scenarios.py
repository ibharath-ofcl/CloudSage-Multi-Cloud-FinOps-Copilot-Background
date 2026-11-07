"""
Tests for Synthetic Waste Scenarios.
Validates that all 14 FinOps edge-case demonstration scenarios are seeded and evaluated
properly by the Waste Detection Engine.
"""

from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from backend.app.core.enums import WasteType
from backend.app.models.waste import WasteDetection
from backend.app.waste_detection.engine import WasteDetectionEngine
from backend.app.waste_detection.synthetic import SyntheticWasteScenarioGenerator


def test_seed_all_scenarios_and_evaluate(db_session: Session):
    """
    Seeds all 14 scenarios and executes a detection run, validating that findings
    and clean/safeguard classifications match FinOps expectations.
    """
    scenario_map = SyntheticWasteScenarioGenerator.seed_all_scenarios(db_session)
    assert len(scenario_map) == 14

    # Execute waste detection run
    run = WasteDetectionEngine.execute_detection_run(
        db=db_session,
        provider="ALL",
        lookback_days=7,
    )

    assert run.status == "COMPLETED"
    assert run.total_resources_evaluated >= 14
    assert run.findings_created >= 6  # Major detectable waste findings created

    # Verify key positive findings
    idle_aws_finding = (
        db_session.query(WasteDetection)
        .filter(WasteDetection.resource_id == scenario_map["scen_01_idle_aws_ec2"])
        .first()
    )
    assert idle_aws_finding is not None
    assert idle_aws_finding.waste_type == WasteType.IDLE_COMPUTE.value
    assert idle_aws_finding.status == "ACTIVE"
    assert idle_aws_finding.estimated_monthly_savings == Decimal("180.0000")

    unattached_storage_finding = (
        db_session.query(WasteDetection)
        .filter(WasteDetection.resource_id == scenario_map["scen_04_unattached_aws_ebs"])
        .first()
    )
    assert unattached_storage_finding is not None
    assert unattached_storage_finding.waste_type == WasteType.UNATTACHED_STORAGE.value

    orphaned_snapshot_finding = (
        db_session.query(WasteDetection)
        .filter(WasteDetection.resource_id == scenario_map["scen_07_orphaned_aws_snapshot"])
        .first()
    )
    assert orphaned_snapshot_finding is not None
    assert orphaned_snapshot_finding.waste_type == WasteType.ORPHANED_SNAPSHOT.value

    # Verify safeguards and clean/insufficient scenarios have ZERO findings
    # Scenario 08: Snapshot with compliance / retention tags
    compliance_finding = (
        db_session.query(WasteDetection)
        .filter(WasteDetection.resource_id == scenario_map["scen_08_compliance_azure_snapshot"])
        .first()
    )
    assert compliance_finding is None

    # Scenario 13: Conflicting network traffic (proxy/gateway node) - must have ZERO idle compute findings
    idle_conflicting_finding = (
        db_session.query(WasteDetection)
        .filter(
            WasteDetection.resource_id == scenario_map["scen_13_conflicting_signals"],
            WasteDetection.waste_type == WasteType.IDLE_COMPUTE.value,
        )
        .first()
    )
    assert idle_conflicting_finding is None
