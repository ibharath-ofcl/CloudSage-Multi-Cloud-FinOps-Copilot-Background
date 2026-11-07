"""
CloudSage Unused Network Resources Detector.
Identifies unassociated Elastic/Public IPv4 addresses and zero-target load balancers
incurring ongoing cloud provider reservation fees.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from backend.app.core.enums import Severity, WasteType
from backend.app.models.billing import BillingRecord
from backend.app.models.inventory import ResourceRelationship
from backend.app.models.resource import CloudResource, ResourceMetric
from backend.app.waste_detection.base import BaseWasteDetector
from backend.app.waste_detection.models import DetectorExecutionResult, WasteFinding
from backend.app.waste_detection.severity import SeverityEvaluator


class UnusedNetworkResourcesDetector(BaseWasteDetector):
    """Detects unassociated static IPs and zero-target load balancers."""

    @property
    def detector_id(self) -> str:
        return "unused_network_resources_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def waste_category(self) -> WasteType:
        return WasteType.UNUSED_NETWORK

    @property
    def description(self) -> str:
        return (
            "Detects unassociated static/elastic public IP addresses and load balancers "
            "with zero active targets or backend associations generating idle charges."
        )

    @property
    def supported_providers(self) -> List[str]:
        return ["AWS", "AZURE", "GCP"]

    @property
    def supported_resource_types(self) -> List[str]:
        return [
            "ec2:eip",
            "aws:ec2:eip",
            "Microsoft.Network/publicIPAddresses",
            "compute.googleapis.com/Address",
            "elasticloadbalancing:loadbalancer",
            "Microsoft.Network/loadBalancers",
            "compute.googleapis.com/ForwardingRule",
            "NETWORKING",
        ]

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "unattached_grace_days": 1,
        }

    def detect(
        self,
        resource: CloudResource,
        metrics: List[ResourceMetric],
        relationships: List[ResourceRelationship],
        billing_records: List[BillingRecord],
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> DetectorExecutionResult:
        res_id = resource.resource_id
        res_type = resource.resource_type.lower()
        res_cat = resource.service_category.upper()

        is_network = res_cat == "NETWORKING" or any(k in res_type for k in ("ip", "eip", "address", "loadbalancer", "lb"))
        if not is_network:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="CLEAN",
                message="Resource is not a networking asset",
            )

        # 1. Unassociated Static IP Address Check
        is_ip = any(k in res_type for k in ("eip", "address", "publicip")) or "ip" in res_id.lower()
        if is_ip:
            has_association = any(
                r.relationship_type in ("ASSOCIATED_WITH", "ATTACHED_TO")
                for r in relationships
            )
            meta = resource.resource_metadata or {}
            is_unattached_meta = meta.get("association_id") is None and meta.get("instance_id") is None

            if not has_association or is_unattached_meta:
                cost = resource.monthly_cost or Decimal("3.6500")  # Standard ~0.005/hr IPv4 charge
                severity = SeverityEvaluator.evaluate_severity(cost)

                finding = WasteFinding(
                    resource_id=res_id,
                    provider=resource.provider,
                    account_id=resource.account_id,
                    resource_name=resource.resource_name,
                    resource_type=resource.resource_type,
                    waste_type=WasteType.IDLE_IP,
                    detector_id=self.detector_id,
                    detector_version=self.detector_version,
                    finding_title=f"Unassociated {resource.provider} Public IP ({resource.resource_name or res_id})",
                    explanation="Static public IPv4 address is not associated with any running instance or network gateway.",
                    severity=severity,
                    confidence_score=Decimal("0.9500"),
                    estimated_monthly_savings=cost,
                    observation_window_days=7,
                    evidence={
                        "network_resource_type": "PUBLIC_IP",
                        "associated_targets": 0,
                        "monthly_idle_ip_fee_usd": str(cost),
                    },
                )
                return DetectorExecutionResult(
                    detector_id=self.detector_id,
                    resource_id=res_id,
                    status="DETECTED",
                    finding=finding,
                )

        # 2. Zero-Target Load Balancer Check
        is_lb = any(k in res_type for k in ("loadbalancer", "forwardingrule", "lb"))
        if is_lb:
            meta = resource.resource_metadata or {}
            target_count = meta.get("target_count") or meta.get("backend_count")
            has_target_rels = any(r.relationship_type in ("ATTACHED_TO", "MEMBER_OF") for r in relationships)

            if (target_count is not None and target_count == 0) or (target_count is None and not has_target_rels):
                cost = resource.monthly_cost or Decimal("18.0000")
                severity = SeverityEvaluator.evaluate_severity(cost)

                finding = WasteFinding(
                    resource_id=res_id,
                    provider=resource.provider,
                    account_id=resource.account_id,
                    resource_name=resource.resource_name,
                    resource_type=resource.resource_type,
                    waste_type=WasteType.ZERO_TARGET_LB,
                    detector_id=self.detector_id,
                    detector_version=self.detector_version,
                    finding_title=f"Zero-Target {resource.provider} Load Balancer ({resource.resource_name or res_id})",
                    explanation="Load balancer has zero registered healthy targets or compute backend instances.",
                    severity=severity,
                    confidence_score=Decimal("0.9000"),
                    estimated_monthly_savings=cost,
                    observation_window_days=7,
                    evidence={
                        "network_resource_type": "LOAD_BALANCER",
                        "registered_targets": 0,
                        "monthly_base_fee_usd": str(cost),
                    },
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
            message="Networking resource has active associations or targets",
        )
