"""
CloudSage Evidence Validation and Confidence Engine.
Validates metric signal integrity, detects conflicting telemetry, and computes
transparent, mathematically grounded confidence scores (0.0000 to 1.0000).
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource, ResourceMetric


class EvidenceValidator:
    """Evaluates telemetry sample depth, metric conflicts, and inventory certainty."""

    @classmethod
    def calculate_compute_confidence(
        cls,
        resource: CloudResource,
        metrics: List[ResourceMetric],
        required_days: int = 7,
        has_network_metrics: bool = True,
        has_memory_metrics: bool = False,
    ) -> Decimal:
        """
        Computes composite confidence score for compute detection:
        - Sample depth weight: 40%
        - Metric multidimensionality (CPU + Network + Memory): 30%
        - Inventory status certainty: 30%
        """
        if not metrics:
            return Decimal("0.0000")

        # 1. Sample depth (at least required_days * 1 daily aggregation or hourly samples)
        # 7 days of 1-hour samples = 168, or daily samples = 7
        total_samples = sum((m.sample_count if m.sample_count is not None else 1) for m in metrics)
        sample_score = min(Decimal("1.0"), Decimal(str(total_samples)) / Decimal(str(required_days * 24)))
        if sample_score < Decimal("0.3"):
            sample_score = Decimal("0.4")  # Baseline if at least some samples exist

        # 2. Metric multidimensionality
        multidimensionality = Decimal("0.5")  # CPU alone
        if has_network_metrics:
            multidimensionality += Decimal("0.3")
        if has_memory_metrics:
            multidimensionality += Decimal("0.2")

        # 3. Inventory certainty
        inv_score = Decimal("1.0") if resource.discovery_status == "CONFIRMED" else Decimal("0.7")

        confidence = (
            (sample_score * Decimal("0.40"))
            + (multidimensionality * Decimal("0.30"))
            + (inv_score * Decimal("0.30"))
        ).quantize(Decimal("0.0001"))

        return min(Decimal("1.0000"), max(Decimal("0.1000"), confidence))

    @classmethod
    def calculate_storage_confidence(
        cls,
        resource: CloudResource,
        relationships: List[ResourceRelationship],
        unattached_days: int,
    ) -> Decimal:
        """
        Computes storage confidence based on topology verification and age.
        """
        # Base confidence from unattached duration
        duration_factor = min(Decimal("1.0"), Decimal(str(unattached_days)) / Decimal("14"))
        # Inventory verification factor
        inv_factor = Decimal("1.0") if resource.discovery_status == "CONFIRMED" else Decimal("0.75")

        # Relationship completeness: if status is 'available' and 0 incoming ATTACHED_TO relationships
        has_attachments = any(r.relationship_type == "ATTACHED_TO" for r in relationships)
        if has_attachments:
            return Decimal("0.0000")  # Conflicting signal!

        confidence = (
            (Decimal("0.50") * Decimal("1.0"))  # Definitive provider state
            + (Decimal("0.30") * duration_factor)
            + (Decimal("0.20") * inv_factor)
        ).quantize(Decimal("0.0001"))

        return min(Decimal("1.0000"), max(Decimal("0.5000"), confidence))

    @classmethod
    def calculate_snapshot_confidence(
        cls,
        resource: CloudResource,
        snapshot_age_days: int,
        parent_deleted: bool,
        has_retention_tags: bool,
    ) -> Decimal:
        """
        Computes snapshot confidence. If parent volume is confirmed deleted and snapshot > 30 days old.
        """
        if has_retention_tags:
            # Deliberately retained for backup/compliance
            return Decimal("0.3000")

        base = Decimal("0.70")
        if parent_deleted:
            base += Decimal("0.20")
        if snapshot_age_days >= 60:
            base += Decimal("0.10")

        return min(Decimal("1.0000"), base.quantize(Decimal("0.0001")))
