"""
CloudSage Unattached Block Storage Detector.
Leverages Stage 5 resource topology graphs to identify unattached EBS volumes,
Azure Managed Disks, and GCP Persistent Disks generating idle storage fees.
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


class UnattachedStorageDetector(BaseWasteDetector):
    """Detects orphaned or unattached block storage volumes."""

    @property
    def detector_id(self) -> str:
        return "unattached_storage_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def waste_category(self) -> WasteType:
        return WasteType.UNATTACHED_STORAGE

    @property
    def description(self) -> str:
        return (
            "Identifies unattached block storage volumes (AWS EBS, Azure Managed Disks, "
            "GCP Persistent Disks) lacking an active attachment to any virtual machine for > 3 days."
        )

    @property
    def supported_providers(self) -> List[str]:
        return ["AWS", "AZURE", "GCP"]

    @property
    def supported_resource_types(self) -> List[str]:
        return [
            "ec2:volume",
            "aws:ec2:volume",
            "Microsoft.Compute/disks",
            "azure:managed_disks",
            "compute.googleapis.com/Disk",
            "gcp:compute_engine",
        ]

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "min_unattached_days": 3,
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

        # 1. Eligibility Check: Must be a storage disk/volume
        is_storage = resource.service_category.upper() == "STORAGE" or "volume" in resource.resource_type.lower() or "disk" in resource.resource_type.lower()
        if not is_storage:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message="Resource is not block storage",
            )

        # Snapshots are handled by orphaned_snapshots detector
        if "snapshot" in resource.resource_type.lower():
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message="Snapshot evaluated by snapshot detector",
            )

        # 2. Topology Check: Look for active inbound ATTACHED_TO relationship
        # relationships where target_resource_id == res_id and type == ATTACHED_TO
        active_attachment = any(
            r.relationship_type == "ATTACHED_TO" and r.target_resource_id == res_id
            for r in relationships
        )

        status_lower = resource.status.lower()
        is_unattached_state = status_lower in ("available", "unattached", "ready")

        if active_attachment:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message="Disk is actively attached to a compute instance",
            )

        # If not explicitly in unattached state and has attachments, clean
        if not is_unattached_state and not ("in-use" not in status_lower and "attached" not in status_lower):
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message=f"Disk status indicates attachment ({resource.status})",
            )

        # 3. Age / Duration Check
        now = datetime.now(timezone.utc)
        created_at = resource.resource_created_at or resource.first_discovered_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = (now - created_at).total_seconds() / 86400.0

        if age_days < cfg["min_unattached_days"]:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message=f"Disk unattached duration ({age_days:.1f} days) is within grace period (< {cfg['min_unattached_days']} days)",
            )

        # 4. Savings & Finding Generation
        savings, methodology, cost_details = SavingsCalculator.estimate_unattached_storage_savings(resource, billing_records)
        confidence = EvidenceValidator.calculate_storage_confidence(
            resource=resource,
            relationships=relationships,
            unattached_days=int(age_days),
        )
        severity = SeverityEvaluator.evaluate_severity(savings)

        disk_size = resource.resource_metadata.get("size_gb") if resource.resource_metadata else None

        evidence_proof = {
            "disk_status": resource.status,
            "size_gb": disk_size,
            "unattached_duration_days": round(age_days, 1),
            "topology_confirmed_unattached": True,
            "cost_methodology": methodology,
            "cost_details": cost_details,
        }

        finding = WasteFinding(
            resource_id=res_id,
            provider=resource.provider,
            account_id=resource.account_id,
            resource_name=resource.resource_name,
            resource_type=resource.resource_type,
            waste_type=WasteType.UNATTACHED_STORAGE,
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            finding_title=f"Unattached {resource.provider} Storage Disk ({resource.resource_name or res_id})",
            explanation=(
                f"Block storage disk has remained unattached for {age_days:.1f} days with zero connected instances "
                f"in the infrastructure topology graph while continuing to accrue storage fees."
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
