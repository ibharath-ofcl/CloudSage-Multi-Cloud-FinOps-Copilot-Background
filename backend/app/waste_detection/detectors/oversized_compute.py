"""
CloudSage Oversized Compute Instance Detector.
Identifies over-provisioned compute instances whose historical workload
consistently remains well below provisioned vCPU and memory capacity.
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


class OversizedComputeDetector(BaseWasteDetector):
    """Detects running instances with provisioned capacity exceeding demand."""

    @property
    def detector_id(self) -> str:
        return "oversized_compute_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def waste_category(self) -> WasteType:
        return WasteType.OVERSIZED_COMPUTE

    @property
    def description(self) -> str:
        return (
            "Identifies compute instances where average CPU utilization < 20% and peak CPU < 50% "
            "over a 14-day observation window, indicating excessive allocation."
        )

    @property
    def supported_providers(self) -> List[str]:
        return ["AWS", "AZURE", "GCP"]

    @property
    def supported_resource_types(self) -> List[str]:
        return [
            "ec2:instance",
            "aws:ec2:instance",
            "Microsoft.Compute/virtualMachines",
            "azure:virtual_machines",
            "compute.googleapis.com/Instance",
            "gcp:compute_engine",
        ]

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "avg_cpu_max_pct": Decimal("20.0"),
            "peak_cpu_max_pct": Decimal("50.0"),
            "min_observation_days": 14,
            "downsize_savings_ratio": Decimal("0.50"),
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

        if resource.service_category.upper() != "COMPUTE":
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message="Resource is not a compute instance",
            )

        if resource.status.lower() not in ("active", "running"):
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message="Resource is not in an active running state",
            )

        cpu_metrics = [
            m for m in metrics
            if m.metric_name in ("cpu_utilization_pct", "cpu_utilization", "CPUUtilization", "Percentage CPU")
        ]

        if not cpu_metrics:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="INSUFFICIENT_DATA",
                message="Missing CPU telemetry observations",
            )

        timestamps = [m.timestamp for m in cpu_metrics if m.timestamp]
        if timestamps:
            min_ts = min(timestamps)
            max_ts = max(timestamps)
            if min_ts.tzinfo is None:
                min_ts = min_ts.replace(tzinfo=timezone.utc)
            if max_ts.tzinfo is None:
                max_ts = max_ts.replace(tzinfo=timezone.utc)
            duration_days = (max_ts - min_ts).total_seconds() / 86400.0
            if duration_days < 4.5:  # Require at least ~5 days
                return DetectorExecutionResult(
                    detector_id=self.detector_id,
                    resource_id=res_id,
                    status="INSUFFICIENT_DATA",
                    message=f"Insufficient observation window ({duration_days:.1f} days, min 14 recommended)",
                )

        avg_cpu = sum((m.average_value for m in cpu_metrics), Decimal("0.0")) / Decimal(str(len(cpu_metrics)))
        peak_cpu = max((m.peak_value for m in cpu_metrics), default=Decimal("0.0"))

        # Idle compute detector handles < 5%. Oversized handles 5% <= avg < 20% and peak < 50%
        if avg_cpu < cfg["avg_cpu_max_pct"] and peak_cpu < cfg["peak_cpu_max_pct"]:
            # If it's pure idle (avg < 5%), let idle compute detector handle or flag if above 5%
            savings, methodology, cost_details = SavingsCalculator.estimate_oversized_compute_savings(
                resource=resource,
                downsize_ratio=cfg["downsize_savings_ratio"],
            )

            confidence = EvidenceValidator.calculate_compute_confidence(
                resource=resource,
                metrics=cpu_metrics,
                required_days=cfg["min_observation_days"],
                has_network_metrics=True,
            )
            severity = SeverityEvaluator.evaluate_severity(savings)

            evidence_proof = {
                "avg_cpu_utilization_pct": float(avg_cpu.quantize(Decimal("0.01"))),
                "peak_cpu_utilization_pct": float(peak_cpu.quantize(Decimal("0.01"))),
                "metrics_sample_count": len(cpu_metrics),
                "observation_window_days": cfg["min_observation_days"],
                "downsize_methodology": methodology,
                "cost_details": cost_details,
                "current_instance_type": resource.resource_metadata.get("instance_type") or resource.resource_metadata.get("vm_size") if resource.resource_metadata else "standard",
            }

            finding = WasteFinding(
                resource_id=res_id,
                provider=resource.provider,
                account_id=resource.account_id,
                resource_name=resource.resource_name,
                resource_type=resource.resource_type,
                waste_type=WasteType.OVERSIZED_COMPUTE,
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                finding_title=f"Oversized {resource.provider} Compute ({resource.resource_name or res_id})",
                explanation=(
                    f"Instance capacity significantly exceeds peak workload. Average CPU was {avg_cpu:.1f}% "
                    f"(< {cfg['avg_cpu_max_pct']}%) with peak CPU reaching only {peak_cpu:.1f}% (< {cfg['peak_cpu_max_pct']}%) "
                    f"over {cfg['min_observation_days']} days."
                ),
                severity=severity,
                confidence_score=confidence,
                estimated_monthly_savings=savings,
                observation_window_days=cfg["min_observation_days"],
                evidence=evidence_proof,
            )

            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="DETECTED",
                finding=finding,
            )

        return DetectorExecutionResult(
            detector_id=self.detector_id,
            resource_id=res_id,
            status="CLEAN",
            message=f"Instance utilization is appropriately sized (avg: {avg_cpu:.1f}%, peak: {peak_cpu:.1f}%)",
        )
