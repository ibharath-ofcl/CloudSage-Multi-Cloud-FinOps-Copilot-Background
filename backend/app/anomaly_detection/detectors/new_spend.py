"""
CloudSage New Spend Pattern Detector.
Detects newly appeared spending for services, SKUs, or resources that previously had zero expenditure.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from backend.app.anomaly_detection.base import BaseAnomalyDetector
from backend.app.anomaly_detection.impact import (
    calculate_deviations,
    calculate_excess_cost,
    calculate_projected_impact,
    determine_severity,
)
from backend.app.anomaly_detection.models import (
    AnomalyCandidate,
    BaselineResult,
    DetectorExecutionResult,
    TimeSeries,
)
from backend.app.core.enums import AnomalyCategory, DetectionMethod


class NewSpendPatternDetector(BaseAnomalyDetector):
    """Detects first-time or newly appeared cloud spending with zero baseline history."""

    @property
    def detector_id(self) -> str:
        return "new_spend_pattern_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> AnomalyCategory:
        return AnomalyCategory.NEW_SPEND

    @property
    def supported_dimensions(self) -> List[str]:
        return ["SERVICE", "RESOURCE", "SKU"]

    @property
    def description(self) -> str:
        return "Detects newly appeared spending on previously inactive or newly created resources/services."

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "min_new_spend_cost": Decimal("15.0000"),
            "required_zero_history_days": 7,
        }

    def detect(
        self,
        time_series: TimeSeries,
        baseline: Optional[BaselineResult] = None,
        billing_records: Optional[List[Any]] = None,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> DetectorExecutionResult:
        if not time_series.points:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                status="CLEAN",
                message="No points in time series.",
            )

        t = {**self.default_thresholds, **(thresholds or {})}
        min_cost = Decimal(str(t["min_new_spend_cost"]))
        min_zero_days = int(t["required_zero_history_days"])

        pts = time_series.points
        current_pt = pts[-1]

        # Check if current point has positive cost
        if current_pt.cost < min_cost:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                status="CLEAN",
                message="Current spend is below new spend threshold.",
            )

        # Check history prior to current point
        history_pts = pts[:-1]
        if len(history_pts) < min_zero_days:
            # First time seeing this entity at all
            is_new = True
            zero_days = len(history_pts)
        else:
            recent_history = history_pts[-min_zero_days:]
            zero_days = sum(1 for p in recent_history if p.cost == Decimal("0.0000"))
            is_new = (zero_days >= min_zero_days)

        if not is_new:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                status="CLEAN",
                message="Entity had prior spend in baseline window; not new spend.",
            )

        expected = Decimal("0.0000")
        excess = current_pt.cost
        devs = calculate_deviations(current_pt.cost, expected)
        proj = calculate_projected_impact(excess, anomaly_type="PERSISTENT_STEP", duration_days=1)
        sev = determine_severity(excess, devs["percentage_deviation"])

        target_name = time_series.resource_id or time_series.service_name or time_series.sku or "Entity"
        title = f"New Spend Appeared: {time_series.provider} {target_name}"
        explanation = (
            f"New expenditure of ${current_pt.cost:,.2f} detected on {time_series.provider} {target_name} "
            f"following at least {zero_days} days of zero expenditure."
        )

        candidate = AnomalyCandidate(
            detector_id=self.detector_id,
            detector_version=self.detector_version,
            provider=time_series.provider,
            account_id=time_series.account_id or "UNKNOWN",
            service_category=time_series.service_category or "GENERAL",
            service_name=time_series.service_name or "General",
            region=time_series.region or "GLOBAL",
            resource_id=time_series.resource_id,
            sku=time_series.sku,
            anomaly_date=current_pt.point_date,
            observed_cost=current_pt.cost,
            expected_cost=expected,
            absolute_deviation=devs["absolute_deviation"],
            percentage_deviation=devs["percentage_deviation"],
            estimated_excess_cost=excess,
            projected_monthly_impact=proj["projected_monthly_impact"],
            currency=time_series.currency,
            anomaly_category=self.category,
            detection_methods=[DetectionMethod.NEW_SPEND],
            severity=sev,
            confidence_score=Decimal("0.9500"),
            title=title,
            explanation=explanation,
            baseline_window_days=zero_days,
            observation_window_days=1,
            baseline_metrics={
                "zero_history_days": zero_days,
                "first_seen_cost": str(current_pt.cost),
            },
            source_billing_references=current_pt.source_record_ids,
        )

        return DetectorExecutionResult(
            detector_id=self.detector_id,
            status="DETECTED",
            anomalies=[candidate],
            message=explanation,
            metrics={"zero_history_days": zero_days, "first_cost": str(current_pt.cost)},
        )
