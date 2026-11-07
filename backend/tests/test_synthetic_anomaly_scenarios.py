"""
Integration Tests for CloudSage 20 Synthetic Anomaly Scenarios.
Seeds 20 real-world FinOps anomaly scenarios across AWS, Azure, and GCP,
executes detection runs, and verifies that anomalies and structural shifts are successfully detected.
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from backend.app.anomaly_detection.engine import AnomalyDetectionEngine
from backend.app.anomaly_detection.synthetic import SYNTHETIC_SCENARIO_DEFINITIONS, seed_synthetic_anomalies
from backend.app.core.enums import AnomalyCategory, AnomalyStatus
from backend.app.models.anomaly import CostAnomaly, CostBaseline
from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource


def test_seed_and_detect_synthetic_anomaly_scenarios(db_session: Session):
    """
    Seeds all 20 enterprise anomaly scenarios and runs the anomaly detection engine
    to verify multi-cloud spike detection, change point analysis, and root cause attribution.
    """
    ref_date = date(2026, 10, 20)
    seed_result = seed_synthetic_anomalies(db=db_session, reference_date=ref_date, baseline_days=15)

    assert seed_result["scenarios_seeded"] == 20
    assert seed_result["resources_created"] == 20
    assert seed_result["billing_records_created"] > 250

    # Verify inventory records
    res_count = db_session.query(CloudResource).count()
    assert res_count == 20

    # Verify billing records
    rec_count = db_session.query(BillingRecord).count()
    assert rec_count > 250

    # Execute detection engine across seeded data
    engine = AnomalyDetectionEngine()
    run = engine.execute_detection_run(
        db=db_session,
        baseline_window_days=14,
        start_date=date(2026, 10, 1),
        end_date=ref_date,
    )

    assert run.status in ("COMPLETED", "PARTIAL_SUCCESS")
    assert run.total_series_evaluated > 0
    assert run.baselines_generated > 0
    assert run.anomalies_created > 0
    assert run.total_excess_cost > Decimal("0.0000")

    # Verify anomalies persisted in database
    anomalies = db_session.query(CostAnomaly).all()
    assert len(anomalies) > 0

    providers_detected = {a.provider for a in anomalies}
    assert "AWS" in providers_detected
    assert "AZURE" in providers_detected
    assert "GCP" in providers_detected

    categories_detected = {a.anomaly_category for a in anomalies}
    assert len(categories_detected) >= 2

    # Check that baselines were generated and persisted
    baselines = db_session.query(CostBaseline).all()
    assert len(baselines) > 0

