"""
CloudSage Advanced Root Cause Analysis Engine Coordinator.
Orchestrates multi-dimensional cost decomposition, contribution ranking,
usage vs. pricing separation, time-series baseline analysis, resource topology,
cross-signal correlation, and automated hypothesis generation.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.investigation.confidence import ConfidenceScorer
from backend.app.investigation.contribution_analysis import ContributionAnalysisEngine
from backend.app.investigation.dimension_analysis import DimensionAnalysisEngine
from backend.app.investigation.hypotheses import HypothesisEvaluator
from backend.app.investigation.resource_correlation import ResourceCorrelationEngine
from backend.app.investigation.time_series_analysis import TimeSeriesAnalysisEngine
from backend.app.investigation.usage_price_analysis import UsagePriceAnalysisEngine
from backend.app.models.anomaly import CostAnomaly
from backend.app.models.resource import CloudResource
from backend.app.schemas.investigation import (
    ContributionRankingResponse,
    CrossSignalCorrelationResponse,
    MultiDimensionalAnalysisResponse,
    ResourceInvestigationResponse,
    TimelineAnalysisResponse,
    UsagePriceAnalysisResponse,
)


class InvestigationEngine:
    """Facade coordinator for multi-dimensional root cause analysis."""

    def __init__(self, db: Session):
        self.db = db

    def run_full_analysis(
        self,
        anomaly: CostAnomaly,
        investigation_id: UUID,
    ) -> Dict[str, Any]:
        """
        Executes all root-cause analytical engines and generates synthesized findings.
        """
        # 1. Multi-Dimensional Decomposition (10 dimensions)
        dim_analysis: MultiDimensionalAnalysisResponse = (
            DimensionAnalysisEngine.analyze_dimensions(
                db=self.db,
                anomaly=anomaly,
                investigation_id=investigation_id,
            )
        )

        # 2. Contribution Ranking & Pareto Analysis
        contrib_ranking: ContributionRankingResponse = (
            ContributionAnalysisEngine.rank_contributors(
                db=self.db,
                anomaly=anomaly,
                investigation_id=investigation_id,
            )
        )

        # 3. Usage vs. Price Decomposition
        usage_price: UsagePriceAnalysisResponse = (
            UsagePriceAnalysisEngine.decompose(
                db=self.db,
                anomaly=anomaly,
                investigation_id=investigation_id,
            )
        )

        # 4. Time-Series Timeline Analysis
        timeline: TimelineAnalysisResponse = (
            TimeSeriesAnalysisEngine.analyze_timeline(
                db=self.db,
                anomaly=anomaly,
                investigation_id=investigation_id,
            )
        )

        # 5. Resource Topology & Metrics
        res_investigation: ResourceInvestigationResponse = (
            ResourceCorrelationEngine.get_resource_investigation(
                db=self.db,
                anomaly=anomaly,
                investigation_id=investigation_id,
            )
        )

        # 6. Cross-Signal Correlations (Waste, Recommendations, Alerts)
        cross_signals: CrossSignalCorrelationResponse = (
            ResourceCorrelationEngine.get_cross_signals(
                db=self.db,
                anomaly=anomaly,
                investigation_id=investigation_id,
            )
        )

        # 7. Synthesize Automated Findings & Hypotheses
        top_contrib = contrib_ranking.top_contributors[0] if contrib_ranking.top_contributors else None
        top_contrib_id = top_contrib.entity_id if top_contrib else anomaly.resource_id
        top_contrib_share = top_contrib.contribution_share if top_contrib else Decimal("100.00")

        # Check resource existence and telemetry
        primary_res = None
        if top_contrib_id:
            primary_res = self.db.query(CloudResource).filter(CloudResource.resource_id == top_contrib_id).first()

        telemetry_summary = {}
        if res_investigation.resources:
            telemetry_summary = res_investigation.resources[0].metrics_summary

        has_waste = len(cross_signals.correlated_waste_detections) > 0
        waste_name = cross_signals.correlated_waste_detections[0]["rule_name"] if has_waste else None

        has_rec = len(cross_signals.correlated_recommendations) > 0
        rec_title = cross_signals.correlated_recommendations[0]["title"] if has_rec else None

        synthesized_findings = HypothesisEvaluator.evaluate_hypotheses(
            investigation_id=investigation_id,
            provider=anomaly.provider,
            service_name=anomaly.service_name,
            total_excess_cost=anomaly.estimated_excess_cost,
            dominant_dimension=dim_analysis.dominant_dimension,
            top_contributor_id=top_contrib_id,
            top_contributor_share=top_contrib_share,
            usage_effect=usage_price.usage_effect,
            price_effect=usage_price.price_effect,
            primary_cost_driver=usage_price.primary_cost_driver,
            resource_exists=(primary_res is not None),
            resource_status=primary_res.status if primary_res else None,
            has_waste_match=has_waste,
            waste_rule_name=waste_name,
            has_recommendation=has_rec,
            recommendation_title=rec_title,
            telemetry_metrics=telemetry_summary,
            is_new_resource=(anomaly.expected_cost == Decimal("0.0000")),
        )

        # 8. Overall Confidence Score Evaluation
        score, category, supp, contra, next_step = ConfidenceScorer.evaluate(
            has_direct_billing=True,
            billing_record_count=max(1, len(dim_analysis.dimensions.get("SERVICE", []))),
            has_inventory_match=(primary_res is not None),
            inventory_status=primary_res.status if primary_res else None,
            is_inventory_stale=False,
            has_telemetry_metrics=(bool(telemetry_summary and telemetry_summary.get("sample_count", 0) > 0)),
            telemetry_corroborates_surge=(
                telemetry_summary.get("avg_cpu_percent", 0) > 50 if telemetry_summary else None
            ),
            has_waste_detection_match=has_waste,
            has_recommendation_match=has_rec,
            has_alert_match=(len(cross_signals.correlated_alerts) > 0),
            has_valid_baseline=(anomaly.expected_cost > Decimal("0.0000")),
            is_unreconciled=False,
        )

        return {
            "dimensions": dim_analysis,
            "contributions": contrib_ranking,
            "usage_price": usage_price,
            "timeline": timeline,
            "resources": res_investigation,
            "correlations": cross_signals,
            "findings": synthesized_findings,
            "confidence_score": score,
            "confidence_category": category,
            "supporting_observations": supp,
            "contradictory_observations": contra,
            "suggested_next_step": next_step,
        }
