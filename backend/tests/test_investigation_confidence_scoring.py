"""
Tests for Deterministic Rule-Based Root Cause Confidence Scoring Engine.
"""

from decimal import Decimal
import pytest

from backend.app.core.enums import ConfidenceCategory
from backend.app.investigation.confidence import ConfidenceScorer


def test_high_confidence_corroborated():
    """All corroborating signals present results in HIGH confidence."""
    score, category, supp, contra, next_step = ConfidenceScorer.evaluate(
        has_direct_billing=True,
        billing_record_count=10,
        has_inventory_match=True,
        inventory_status="active",
        is_inventory_stale=False,
        has_telemetry_metrics=True,
        telemetry_corroborates_surge=True,
        has_waste_detection_match=True,
        has_recommendation_match=True,
        has_alert_match=True,
        has_valid_baseline=True,
        is_unreconciled=False,
    )

    assert score >= Decimal("0.8000")
    assert category == ConfidenceCategory.HIGH.value
    assert len(supp) >= 4
    assert len(contra) == 0
    assert "Proceed with recommended remediation playbook" in next_step


def test_medium_confidence_partial():
    """Partial corroborating signals result in MEDIUM confidence."""
    score, category, supp, contra, next_step = ConfidenceScorer.evaluate(
        has_direct_billing=True,
        billing_record_count=5,
        has_inventory_match=True,
        inventory_status="active",
        is_inventory_stale=False,
        has_telemetry_metrics=False,
        has_waste_detection_match=False,
        has_recommendation_match=False,
        has_alert_match=False,
        has_valid_baseline=True,
    )

    assert Decimal("0.5000") <= score < Decimal("0.8000")
    assert category == ConfidenceCategory.MEDIUM.value


def test_contradictory_telemetry_penalty():
    """Contradictory telemetry applies a penalty and records a contradictory observation."""
    score_normal, _, _, _, _ = ConfidenceScorer.evaluate(
        has_direct_billing=True,
        has_inventory_match=True,
        has_telemetry_metrics=True,
        telemetry_corroborates_surge=True,
    )

    score_contra, _, _, contra, _ = ConfidenceScorer.evaluate(
        has_direct_billing=True,
        has_inventory_match=True,
        has_telemetry_metrics=True,
        telemetry_corroborates_surge=False,  # Metrics flatlined despite surge
    )

    assert score_contra < score_normal
    assert any("remain near zero or flat" in c for c in contra)


def test_missing_baseline_penalty():
    """Missing baseline data penalizes confidence score."""
    score_with_base, _, _, _, _ = ConfidenceScorer.evaluate(
        has_direct_billing=True,
        has_valid_baseline=True,
    )

    score_no_base, _, _, contra, _ = ConfidenceScorer.evaluate(
        has_direct_billing=True,
        has_valid_baseline=False,
    )

    assert score_no_base < score_with_base
    assert any("baseline" in c for c in contra)


def test_stale_inventory_penalty():
    """Stale inventory record applies penalty."""
    score_fresh, _, _, _, _ = ConfidenceScorer.evaluate(
        has_direct_billing=True,
        has_inventory_match=True,
        is_inventory_stale=False,
    )

    score_stale, _, _, contra, _ = ConfidenceScorer.evaluate(
        has_direct_billing=True,
        has_inventory_match=True,
        is_inventory_stale=True,
    )

    assert score_stale < score_fresh
    assert any("stale" in c for c in contra)


def test_unreconciled_resource_penalty():
    """Unreconciled resource status reduces confidence."""
    score_clean, _, _, _, _ = ConfidenceScorer.evaluate(
        has_direct_billing=True,
        has_inventory_match=True,
        is_unreconciled=False,
    )

    score_unrec, _, _, contra, _ = ConfidenceScorer.evaluate(
        has_direct_billing=True,
        has_inventory_match=True,
        is_unreconciled=True,
    )

    assert score_unrec < score_clean
    assert any("UNRECONCILED" in c for c in contra)


def test_insufficient_evidence():
    """Missing billing, missing inventory, and missing telemetry results in INSUFFICIENT_EVIDENCE."""
    score, category, supp, contra, next_step = ConfidenceScorer.evaluate(
        has_direct_billing=False,
        has_inventory_match=False,
        has_telemetry_metrics=False,
        has_valid_baseline=False,
    )

    assert score < Decimal("0.2000")
    assert category == ConfidenceCategory.INSUFFICIENT_EVIDENCE.value
    assert "insufficient telemetry" in next_step
