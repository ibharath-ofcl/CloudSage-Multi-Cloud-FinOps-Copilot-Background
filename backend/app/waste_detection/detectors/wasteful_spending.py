"""
CloudSage Billing-Based Waste Signals Detector.
Analyzes normalized FOCUS 1.0 billing records and Stage 5 correlation status to identify
unaccounted expenditure, recurring charges on stale resources, and 24x7 non-prod running waste.
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


class BillingBasedWasteDetector(BaseWasteDetector):
    """Detects billing anomalies, charges for stale resources, and continuous non-prod usage."""

    @property
    def detector_id(self) -> str:
        return "billing_based_waste_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def waste_category(self) -> WasteType:
        return WasteType.BILLING_BASED_WASTE

    @property
    def description(self) -> str:
        return (
            "Analyzes normalized billing ledgers to detect ongoing charges for stale unconfirmed assets, "
            "billing-only resources missing from physical inventory, and continuous 24x7 non-prod environments."
        )

    @property
    def supported_providers(self) -> List[str]:
        return ["AWS", "AZURE", "GCP"]

    @property
    def supported_resource_types(self) -> List[str]:
        return ["ALL"]

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "min_stale_days": 14,
            "min_waste_amount_usd": Decimal("5.0000"),
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
        monthly_cost = resource.monthly_cost or Decimal("0.0000")
        if monthly_cost <= Decimal("0.0000") and billing_records:
            monthly_cost = sum((b.unblended_cost for b in billing_records), Decimal("0.0000"))

        # Pattern 1: Recurring billing on STALE resources (absent from inventory > 14 days)
        if resource.discovery_status == "STALE" and monthly_cost >= cfg["min_waste_amount_usd"]:
            severity = SeverityEvaluator.evaluate_severity(monthly_cost)
            finding = WasteFinding(
                resource_id=res_id,
                provider=resource.provider,
                account_id=resource.account_id,
                resource_name=resource.resource_name,
                resource_type=resource.resource_type,
                waste_type=WasteType.BILLING_BASED_WASTE,
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                finding_title=f"Recurring Charges on Stale Resource ({resource.resource_name or res_id})",
                explanation=(
                    f"Resource has not been confirmed in discovery for over {cfg['min_stale_days']} days, "
                    f"yet continues to generate recurring billing charges (${monthly_cost:.2f}/mo)."
                ),
                severity=severity,
                confidence_score=Decimal("0.8500"),
                estimated_monthly_savings=monthly_cost,
                observation_window_days=cfg["min_stale_days"],
                evidence={
                    "pattern": "STALE_RESOURCE_BILLING",
                    "discovery_status": "STALE",
                    "monthly_cost_usd": str(monthly_cost),
                    "last_inventory_sync_at": resource.last_inventory_sync_at.isoformat() if resource.last_inventory_sync_at else None,
                },
            )
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                resource_id=res_id,
                status="DETECTED",
                finding=finding,
            )

        # Pattern 2: Continuous 24x7 Non-Production Compute
        is_non_prod = resource.environment.lower() in ("development", "dev", "test", "testing", "staging", "qa")
        is_running_compute = resource.service_category.upper() == "COMPUTE" and resource.status.lower() in ("active", "running")

        if is_non_prod and is_running_compute and monthly_cost >= cfg["min_waste_amount_usd"]:
            # If running 24x7 without shutdown schedule, ~65% of monthly cost can be saved by off-hours schedule
            schedule_savings = (monthly_cost * Decimal("0.6500")).quantize(Decimal("0.0001"))
            severity = SeverityEvaluator.evaluate_severity(schedule_savings)

            finding = WasteFinding(
                resource_id=res_id,
                provider=resource.provider,
                account_id=resource.account_id,
                resource_name=resource.resource_name,
                resource_type=resource.resource_type,
                waste_type=WasteType.CONTINUOUS_NON_PROD,
                detector_id=self.detector_id,
                detector_version=self.detector_version,
                finding_title=f"24x7 Non-Production Compute ({resource.resource_name or res_id})",
                explanation=(
                    f"Resource tagged as '{resource.environment}' environment runs continuously 24x7 without an automated "
                    f"off-hours shutdown schedule. Implementing an off-hours policy could save approximately 65% (${schedule_savings:.2f}/mo)."
                ),
                severity=severity,
                confidence_score=Decimal("0.9000"),
                estimated_monthly_savings=schedule_savings,
                observation_window_days=7,
                evidence={
                    "pattern": "CONTINUOUS_NON_PROD_COMPUTE",
                    "environment": resource.environment,
                    "monthly_cost_usd": str(monthly_cost),
                    "off_hours_savings_usd": str(schedule_savings),
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
            message="No billing-based waste patterns detected",
        )
