"""
CloudSage Recommendation Evidence Traceability and Verification.
Validates and links multi-cloud evidence items (telemetry metrics, waste detections, cost anomalies, billing records).
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from backend.app.recommendations.models import EvidenceLink, RecommendationCandidate


def validate_candidate_evidence(candidate: RecommendationCandidate) -> bool:
    """
    Ensures recommendation has traceable, substantiated evidence.
    Returns True if at least one evidence link exists or cross-stage finding is present.
    """
    if candidate.waste_detection_id is not None:
        return True
    if candidate.anomaly_id is not None:
        return True
    if len(candidate.evidence_items) > 0:
        return True
    return False


def create_waste_evidence_link(
    waste_id: UUID,
    waste_type: str,
    telemetry: Dict[str, Any],
    monthly_waste: Decimal,
    confidence_score: Decimal = Decimal("1.0000"),
    resource_id: Optional[str] = None,
) -> EvidenceLink:
    """Creates an EvidenceLink originating from a Stage 6 waste detection finding."""
    desc = f"Identified as {waste_type} with estimated monthly waste of ${monthly_waste:.2f} USD."
    return EvidenceLink(
        evidence_type="WASTE_DETECTION",
        waste_detection_id=waste_id,
        resource_id=resource_id,
        description=desc,
        telemetry_data=telemetry,
        confidence_score=confidence_score,
    )


def create_anomaly_evidence_link(
    anomaly_id: UUID,
    category: str,
    actual_cost: Decimal,
    expected_cost: Decimal,
    spike_pct: Decimal,
    confidence_score: Decimal = Decimal("1.0000"),
    resource_id: Optional[str] = None,
    billing_record_ids: Optional[List[str]] = None,
) -> EvidenceLink:
    """Creates an EvidenceLink originating from a Stage 7 cost anomaly finding."""
    desc = (
        f"Correlated cost anomaly ({category}): observed daily cost ${actual_cost:.2f} "
        f"vs expected baseline ${expected_cost:.2f} (+{spike_pct:.1f}% surge)."
    )
    return EvidenceLink(
        evidence_type="COST_ANOMALY",
        anomaly_id=anomaly_id,
        resource_id=resource_id,
        description=desc,
        telemetry_data={
            "actual_cost": str(actual_cost),
            "expected_cost": str(expected_cost),
            "spike_percentage": str(spike_pct),
        },
        billing_record_ids=billing_record_ids or [],
        confidence_score=confidence_score,
    )


def create_metric_evidence_link(
    resource_id: str,
    metric_name: str,
    avg_value: Decimal,
    max_value: Decimal,
    unit: str,
    observation_days: int = 14,
) -> EvidenceLink:
    """Creates an EvidenceLink based on observed resource utilization telemetry."""
    desc = (
        f"Observed {metric_name} averaged {avg_value:.2f}{unit} (peak {max_value:.2f}{unit}) "
        f"over trailing {observation_days} days."
    )
    return EvidenceLink(
        evidence_type="METRIC_SERIES",
        resource_id=resource_id,
        description=desc,
        telemetry_data={
            "metric_name": metric_name,
            "average": str(avg_value),
            "maximum": str(max_value),
            "unit": unit,
            "observation_window_days": observation_days,
        },
        confidence_score=Decimal("0.9500"),
    )
