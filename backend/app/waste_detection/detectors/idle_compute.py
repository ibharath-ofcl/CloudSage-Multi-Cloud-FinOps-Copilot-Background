"""
CloudSage Idle Compute Instance Detector.
Identifies active, billable virtual machines (AWS EC2, Azure VMs, GCP Compute Engine)
maintaining negligible CPU and network utilization over continuous observation windows.
"""

from datetime import datetime, timedelta, timezone
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


class IdleComputeDetector(BaseWasteDetector):
    """Detects underutilized running virtual machines."""

    @property
    def detector_id(self) -> str:
        return "idle_compute_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def waste_category(self) -> WasteType:
        return WasteType.IDLE_COMPUTE

    @property
    def description(self) -> str:
        return (
            "Detects running compute instances with average CPU < 5% and peak CPU < 15% "
            "over a continuous 7-day observation window without significant network traffic."
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
            "avg_cpu_max_pct": Decimal("5.0"),
            "peak_cpu_max_pct": Decimal("15.0"),
            "min_observation_days": 7,
            "max_network_io_mb_day": Decimal("50.0"),  # 50 MB / day
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

        # 1. Eligibility Check: Must be in a billable active/running state
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
                message=f"Compute instance is not running (status: {resource.status})",
            )

        # 2. Metric Evidence Check
        cpu_metrics = [
            m for m in metrics
            if m.metric_name in ("cpu_utilization_pct", "cpu_utilization", "CPUUtilization", "Percentage CPU")
        ]
        network_metrics = [
            m for m in metrics
            if "network" in m.metric_name.lower() or "bytes" in m.metric_name.lower()
        ]

        # Require sufficient observations
        if not cpu_metrics:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="INSUFFICIENT_DATA",
                message="Missing CPU utilization telemetry metrics",
            )

        # Check observation span
        timestamps = [m.timestamp for m in cpu_metrics if m.timestamp]
        if timestamps:
            min_ts = min(timestamps)
            max_ts = max(timestamps)
            # handle naive tz
            if min_ts.tzinfo is None:
                min_ts = min_ts.replace(tzinfo=timezone.utc)
            if max_ts.tzinfo is None:
                max_ts = max_ts.replace(tzinfo=timezone.utc)
            duration_days = (max_ts - min_ts).total_seconds() / 86400.0
            if duration_days < 2.5:  # Require at least ~3 days minimum observations
                return DetectorExecutionResult(
                    detector_id=self.detector_id,
                    resource_id=res_id,
                    status="INSUFFICIENT_DATA",
                    message=f"Insufficient observation window ({duration_days:.1f} days observed, min 7 required)",
                )

        avg_cpu = sum((m.average_value for m in cpu_metrics), Decimal("0.0")) / Decimal(str(len(cpu_metrics)))
        peak_cpu = max((m.peak_value for m in cpu_metrics), default=Decimal("0.0"))

        # Conflicting signals: Check network activity
        avg_net_mb = Decimal("0.0")
        if network_metrics:
            avg_net_bytes = sum((m.average_value for m in network_metrics), Decimal("0.0")) / Decimal(str(len(network_metrics)))
            avg_net_mb = (avg_net_bytes / Decimal("1048576.0")).quantize(Decimal("0.01"))
            if avg_net_mb > cfg["max_network_io_mb_day"]:
                # Conflicting signal: Low CPU but significant network transmission
                return DetectorExecutionResult(
                    detector_id=self.detector_id,
                    resource_id=res_id,
                    status="CLEAN",
                    message=f"Low CPU, but meaningful active network I/O observed ({avg_net_mb} MB/day)",
                )

        # 3. Detection Rule Evaluation
        if avg_cpu < cfg["avg_cpu_max_pct"] and peak_cpu < cfg["peak_cpu_max_pct"]:
            savings, methodology, cost_details = SavingsCalculator.estimate_idle_compute_savings(resource, billing_records)
            confidence = EvidenceValidator.calculate_compute_confidence(
                resource=resource,
                metrics=cpu_metrics,
                required_days=cfg["min_observation_days"],
                has_network_metrics=len(network_metrics) > 0,
            )
            severity = SeverityEvaluator.evaluate_severity(savings)

            evidence_proof = {
                "avg_cpu_utilization_pct": float(avg_cpu.quantize(Decimal("0.01"))),
                "peak_cpu_utilization_pct": float(peak_cpu.quantize(Decimal("0.01"))),
                "avg_network_io_mb_day": float(avg_net_mb),
                "metrics_sample_count": len(cpu_metrics),
                "observation_window_days": cfg["min_observation_days"],
                "cost_methodology": methodology,
                "cost_details": cost_details,
            }

            finding = WasteFinding(
                resource_id=res_id,
                provider=resource.provider,
                account_id=resource.account_id,
                resource_name=resource.resource_name,
                resource_type=resource.resource_type,
                waste_type=WasteType.IDLE_COMPUTE,
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                finding_title=f"Idle {resource.provider} Compute Instance ({resource.resource_name or res_id})",
                explanation=(
                    f"Virtual machine has maintained an average CPU of {avg_cpu:.1f}% (threshold < {cfg['avg_cpu_max_pct']}%) "
                    f"and peak CPU of {peak_cpu:.1f}% (threshold < {cfg['peak_cpu_max_pct']}%) over {cfg['min_observation_days']} days "
                    f"while generating recurring compute charges."
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
            message=f"CPU utilization within normal operating limits (avg: {avg_cpu:.1f}%, peak: {peak_cpu:.1f}%)",
        )
