"""
CloudSage Orphaned Snapshot Detector.
Identifies backup snapshots (AWS EBS snapshots, Azure snapshots, GCP disk snapshots)
whose parent source disk has been deleted or is missing from confirmed inventory for > 30 days.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from backend.app.core.enums import Severity, WasteType
from backend.app.models.billing import BillingRecord
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.waste_detection.base import BaseWasteDetector
from backend.app.waste_detection.evidence import EvidenceValidator
from backend.app.waste_detection.models import DetectorExecutionResult, WasteFinding
from backend.app.waste_detection.savings import SavingsCalculator
from backend.app.waste_detection.severity import SeverityEvaluator


class OrphanedSnapshotsDetector(BaseWasteDetector):
    """Detects snapshots with missing or deleted parent volumes."""

    @property
    def detector_id(self) -> str:
        return "orphaned_snapshots_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def waste_category(self) -> WasteType:
        return WasteType.ORPHANED_SNAPSHOT

    @property
    def description(self) -> str:
        return (
            "Detects storage snapshots older than 30 days whose parent source volume "
            "has been deleted or is absent from confirmed infrastructure inventory."
        )

    @property
    def supported_providers(self) -> List[str]:
        return ["AWS", "AZURE", "GCP"]

    @property
    def supported_resource_types(self) -> List[str]:
        return [
            "ec2:snapshot",
            "aws:ec2:snapshot",
            "Microsoft.Compute/snapshots",
            "azure:managed_disks",
            "compute.googleapis.com/Snapshot",
            "gcp:compute_engine",
        ]

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "min_snapshot_age_days": 30,
        }

    def detect(
        self,
        resource: CloudResource,
        metrics: List[ResourceMetric],
        relationships: List[ResourceRelationship],
        billing_records: List[BillingRecord],
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> DetectorExecutionResult:
        cfg = dict(self.default_thresholds)
        if thresholds:
            cfg.update(thresholds)

        res_id = resource.resource_id

        if "snapshot" not in resource.resource_type.lower() and "snapshot" not in resource.resource_id.lower():
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message="Resource is not a snapshot",
            )

        now = datetime.now(timezone.utc)
        created_at = resource.resource_created_at or resource.first_discovered_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = (now - created_at).total_seconds() / 86400.0

        if age_days < cfg["min_snapshot_age_days"]:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message=f"Snapshot age ({age_days:.1f} days) is within retention grace period (< {cfg['min_snapshot_age_days']} days)",
            )

        # Check compliance / intentional backup tags
        tags = resource.tags or {}
        has_retention_policy = any(
            k in tags for k in ("retention", "compliance", "donotdelete", "archive", "backup_policy")
        )
        if has_retention_policy:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message="Snapshot is governed by intentional retention or compliance tags",
            )

        # Check parent volume relationship (SNAPSHOT_OF where source_resource_id == res_id)
        parent_rel = next(
            (r for r in relationships if r.relationship_type == "SNAPSHOT_OF" and r.source_resource_id == res_id),
            None,
        )

        parent_deleted = False
        source_vol_id = None
        if parent_rel:
            source_vol_id = parent_rel.target_resource_id
            # In synthetic / test environments or real topology, metadata might indicate parent status
            if parent_rel.relationship_metadata and parent_rel.relationship_metadata.get("parent_deleted"):
                parent_deleted = True
        else:
            # No parent volume relationship found in topology graph
            parent_deleted = True

        savings, methodology, cost_details = SavingsCalculator.estimate_orphaned_snapshot_savings(resource, billing_records)
        confidence = EvidenceValidator.calculate_snapshot_confidence(
            resource=resource,
            snapshot_age_days=int(age_days),
            parent_deleted=parent_deleted,
            has_retention_tags=has_retention_policy,
        )
        severity = SeverityEvaluator.evaluate_severity(savings, is_informational_only=has_retention_policy)

        evidence_proof = {
            "snapshot_age_days": round(age_days, 1),
            "source_volume_id": source_vol_id,
            "parent_volume_deleted_or_missing": parent_deleted,
            "has_compliance_retention_tags": has_retention_policy,
            "cost_methodology": methodology,
            "cost_details": cost_details,
        }

        finding = WasteFinding(
            resource_id=res_id,
            provider=resource.provider,
            account_id=resource.account_id,
            resource_name=resource.resource_name,
            resource_type=resource.resource_type,
            waste_type=WasteType.ORPHANED_SNAPSHOT,
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            finding_title=f"Orphaned {resource.provider} Snapshot ({resource.resource_name or res_id})",
            explanation=(
                f"Snapshot is {age_days:.1f} days old and its parent volume "
                f"({source_vol_id or 'unknown'}) is absent from current inventory while incurring ongoing storage costs."
            ),
            severity=severity,
            confidence_score=confidence,
            estimated_monthly_savings=savings,
            observation_window_days=int(age_days),
            evidence=evidence_proof,
        )

        return DetectorExecutionResult(
            detector_id=self.detector_id,
            resource_id=res_id,
            status="DETECTED",
            finding=finding,
        )
