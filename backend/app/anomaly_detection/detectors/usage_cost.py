"""
CloudSage Usage vs Price Divergence Anomaly Detector.
Distinguishes between usage volume surges and SKU unit pricing/rate changes.
"""

from decimal import Decimal, ROUND_HALF_UP
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
from backend.app.anomaly_detection.statistics import mean, PRECISION_FOUR
from backend.app.core.enums import AnomalyCategory, DetectionMethod


class UsagePriceDivergenceDetector(BaseAnomalyDetector):
    """Detects whether expenditure increases are driven by usage volume surges or SKU unit rate changes."""

    @property
    def detector_id(self) -> str:
        return "usage_price_divergence_detector"

    @property
    def detector_version(self) -> str:
        return "1.0.0"

    @property
    def category(self) -> AnomalyCategory:
        return AnomalyCategory.SKU_PRICE_CHANGE

    @property
    def supported_dimensions(self) -> List[str]:
        return ["SERVICE", "RESOURCE", "SKU"]

    @property
    def description(self) -> str:
        return "Analyzes usage quantity vs unit price divergence to detect rate changes vs usage spikes."

    @property
    def default_thresholds(self) -> Dict[str, Any]:
        return {
            "min_excess_cost": Decimal("20.0000"),
            "rate_change_threshold_pct": Decimal("20.0000"),
            "usage_surge_threshold_pct": Decimal("40.0000"),
        }

    def detect(
        self,
        time_series: TimeSeries,
        baseline: Optional[BaselineResult] = None,
        billing_records: Optional[List[Any]] = None,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> DetectorExecutionResult:
        if len(time_series.points) < 8:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                status="INSUFFICIENT_DATA",
                message="Usage divergence requires at least 8 points.",
            )

        t = {**self.default_thresholds, **(thresholds or {})}
        min_excess = Decimal(str(t["min_excess_cost"]))
        rate_thresh_pct = Decimal(str(t["rate_change_threshold_pct"]))
        usage_thresh_pct = Decimal(str(t["usage_surge_threshold_pct"]))

        history_pts = time_series.points[:-1]
        current_pt = time_series.points[-1]

        # Calculate historical baseline for cost and usage
        costs_hist = [p.cost for p in history_pts]
        usage_hist = [p.usage_quantity for p in history_pts if p.usage_quantity > Decimal("0.0000")]

        mean_cost = mean(costs_hist)
        mean_usage = mean(usage_hist) if usage_hist else Decimal("0.0000")

        # Check if today's cost is anomalous
        excess = calculate_excess_cost(current_pt.cost, mean_cost)
        if excess < min_excess:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                status="CLEAN",
                message="Cost does not exceed excess threshold.",
            )

        # Baseline unit rate vs current unit rate
        base_rate = (
            (mean_cost / mean_usage).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
            if mean_usage > Decimal("0.0000")
            else Decimal("0.0000")
        )
        curr_rate = (
            (current_pt.cost / current_pt.usage_quantity).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
            if current_pt.usage_quantity > Decimal("0.0000")
            else Decimal("0.0000")
        )

        rate_pct_change = (
            (((curr_rate - base_rate) / base_rate) * Decimal("100.0000")).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
            if base_rate > Decimal("0.0000")
            else Decimal("0.0000")
        )

        usage_pct_change = (
            (((current_pt.usage_quantity - mean_usage) / mean_usage) * Decimal("100.0000")).quantize(PRECISION_FOUR, rounding=ROUND_HALF_UP)
            if mean_usage > Decimal("0.0000")
            else Decimal("0.0000")
        )

        # Differentiate between SKU Price Change vs Usage Spike
        if rate_pct_change >= rate_thresh_pct and abs(usage_pct_change) < Decimal("20.0000"):
            category = AnomalyCategory.SKU_PRICE_CHANGE
            method = DetectionMethod.USAGE_PRICE_DIVERGENCE
            title = f"SKU Unit Price Shift on {time_series.provider} {time_series.sku or time_series.service_name}"
            explanation = (
                f"Effective unit price increased by {rate_pct_change:.1f}% "
                f"(from ${base_rate:,.4f} to ${curr_rate:,.4f}) while usage volume remained flat "
                f"({usage_pct_change:+.1f}% change)."
            )
        elif usage_pct_change >= usage_thresh_pct:
            category = AnomalyCategory.USAGE_SPIKE
            method = DetectionMethod.USAGE_PRICE_DIVERGENCE
            title = f"Usage Volume Surge on {time_series.provider} {time_series.service_name}"
            explanation = (
                f"Usage quantity surged by {usage_pct_change:.1f}% "
                f"(from {mean_usage:,.1f} to {current_pt.usage_quantity:,.1f}) driving excess spend."
            )
        else:
            return DetectorExecutionResult(
                detector_id=self.detector_id,
                status="CLEAN",
                message="No clear price/usage divergence detected.",
            )

        devs = calculate_deviations(current_pt.cost, mean_cost)
        proj = calculate_projected_impact(excess, anomaly_type="SERVICE_SPIKE", duration_days=1)
        sev = determine_severity(excess, devs["percentage_deviation"])

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
            expected_cost=mean_cost,
            absolute_deviation=devs["absolute_deviation"],
            percentage_deviation=devs["percentage_deviation"],
            estimated_excess_cost=excess,
            projected_monthly_impact=proj["projected_monthly_impact"],
            currency=time_series.currency,
            anomaly_category=category,
            detection_methods=[method],
            severity=sev,
            confidence_score=Decimal("0.9200"),
            title=title,
            explanation=explanation,
            baseline_window_days=len(history_pts),
            observation_window_days=1,
            baseline_metrics={
                "mean_cost": str(mean_cost),
                "mean_usage": str(mean_usage),
                "baseline_unit_rate": str(base_rate),
                "current_unit_rate": str(curr_rate),
                "rate_pct_change": str(rate_pct_change),
                "usage_pct_change": str(usage_pct_change),
            },
            source_billing_references=current_pt.source_record_ids,
        )

        return DetectorExecutionResult(
            detector_id=self.detector_id,
            status="DETECTED",
            anomalies=[candidate],
            message=explanation,
            metrics={"category": category.value, "rate_change_pct": str(rate_pct_change)},
        )
