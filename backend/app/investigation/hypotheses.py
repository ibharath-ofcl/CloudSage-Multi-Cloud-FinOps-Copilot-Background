"""
CloudSage Root Cause Hypothesis Engine.
Generates structured diagnostic hypotheses and findings distinguishing between:
1. FACT: Measurable billing line-item aggregates, discovered inventory, observed telemetry.
2. CORRELATION: Coincident events (e.g. concurrent CPU spike, same-day deployment).
3. HYPOTHESIS: Plausible root-cause explanations pending human or playbook verification.
4. VERIFIED_CAUSE: Definitively verified operational root causes.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from backend.app.core.enums import ConfidenceCategory, EvidenceSource, FindingType


class HypothesisEvaluator:
    """
    Evaluates multi-signal telemetry and billing data to synthesize explainable
    root-cause findings and hypotheses.
    """

    @classmethod
    def evaluate_hypotheses(
        cls,
        investigation_id: UUID,
        provider: str,
        service_name: str,
        total_excess_cost: Decimal,
        dominant_dimension: str,
        top_contributor_id: Optional[str],
        top_contributor_share: Decimal,
        usage_effect: Decimal,
        price_effect: Decimal,
        primary_cost_driver: str,
        resource_exists: bool,
        resource_status: Optional[str],
        has_waste_match: bool,
        waste_rule_name: Optional[str],
        has_recommendation: bool,
        recommendation_title: Optional[str],
        telemetry_metrics: Dict[str, Any],
        is_new_resource: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes a prioritized collection of findings (FACT, CORRELATION, HYPOTHESIS).
        """
        findings: List[Dict[str, Any]] = []

        # -------------------------------------------------------------------------
        # 1. ESTABLISHED FACTS (Billing & Scope)
        # -------------------------------------------------------------------------
        facts_title = f"Total Anomalous Excess Spend of ${total_excess_cost:.2f} in {service_name}"
        facts_explanation = (
            f"Observed spending exceeded statistical baseline by ${total_excess_cost:.2f} USD "
            f"in {provider} {service_name}. The primary analytical concentration is along "
            f"the {dominant_dimension} dimension, where the top contributor accounts for "
            f"{top_contributor_share:.1f}% of anomalous excess."
        )
        findings.append({
            "finding_type": FindingType.FACT.value,
            "title": facts_title,
            "explanation": facts_explanation,
            "dimension": dominant_dimension,
            "financial_impact": total_excess_cost,
            "contribution_percentage": top_contributor_share,
            "confidence_category": ConfidenceCategory.HIGH.value,
            "confidence_score": Decimal("1.0000"),
            "evidence_source": EvidenceSource.BILLING_RECORD.value,
            "evidence_reference": top_contributor_id,
            "supporting_observations": [
                f"Normalized FOCUS 1.0 billing records establish verified total excess of ${total_excess_cost:.2f}",
                f"Concentration along {dominant_dimension} verified by multi-dimensional slice analysis",
            ],
            "contradictory_observations": [],
            "suggested_next_step": "Review contributor breakdown and usage vs. pricing decomposition.",
        })

        # -------------------------------------------------------------------------
        # 2. USAGE VS PRICE DRIVER HYPOTHESIS / FACT
        # -------------------------------------------------------------------------
        if primary_cost_driver == "USAGE_DRIVEN" or (total_excess_cost > 0 and usage_effect > price_effect):
            driver_title = f"Consumption Volume Increase Driving ${usage_effect:.2f} of Excess"
            driver_explanation = (
                f"Mathematical decomposition indicates volumetric usage change accounts for "
                f"${usage_effect:.2f} of total excess spend at baseline pricing. "
                f"Unit rates remained consistent, demonstrating increased consumption demand."
            )
            pct = Decimal("0.00")
            if total_excess_cost > Decimal("0.00"):
                pct = ((usage_effect / total_excess_cost) * Decimal("100")).quantize(Decimal("0.01"))
            findings.append({
                "finding_type": FindingType.FACT.value,
                "title": driver_title,
                "explanation": driver_explanation,
                "dimension": "USAGE_QUANTITY",
                "financial_impact": usage_effect,
                "contribution_percentage": min(Decimal("100.00"), max(Decimal("0.00"), pct)),
                "confidence_category": ConfidenceCategory.HIGH.value,
                "confidence_score": Decimal("0.9000"),
                "evidence_source": EvidenceSource.BILLING_RECORD.value,
                "evidence_reference": "FOCUS_USAGE_QUANTITY_DECOMPOSITION",
                "supporting_observations": [
                    f"Usage quantity delta multiplied by baseline unit rate yields ${usage_effect:.2f}",
                ],
                "contradictory_observations": [],
                "suggested_next_step": "Correlate with application traffic, batch job schedules, or scaling logs.",
            })

            # Formulate actionable hypothesis for usage surge
            hyp_title = "Hypothesis: Unplanned Workload Autoscaling or Batch Processing Surge"
            hyp_exp = (
                "The cost increase is driven by higher consumption units. Suspected causes include "
                "an unexpected traffic surge triggering automated horizontal scaling, runaway batch jobs, "
                "or misconfigured retry loops."
            )
            findings.append({
                "finding_type": FindingType.HYPOTHESIS.value,
                "title": hyp_title,
                "explanation": hyp_exp,
                "dimension": "SERVICE",
                "financial_impact": usage_effect,
                "contribution_percentage": pct,
                "confidence_category": ConfidenceCategory.MEDIUM.value,
                "confidence_score": Decimal("0.7000"),
                "evidence_source": EvidenceSource.HEURISTIC_RULE.value,
                "evidence_reference": None,
                "supporting_observations": [
                    "Direct volumetric usage growth without rate card escalation",
                ],
                "contradictory_observations": [],
                "suggested_next_step": "Examine autoscaling group events and container scheduler scaling logs.",
            })

        elif primary_cost_driver == "PRICE_DRIVEN" or (total_excess_cost > 0 and price_effect > usage_effect):
            driver_title = f"Effective Unit Rate Escalation Driving ${price_effect:.2f} of Excess"
            driver_explanation = (
                f"Effective unit price changed significantly, accounting for ${price_effect:.2f} of excess spend. "
                f"This commonly occurs when commitments (Reserved Instances or Savings Plans) expire, shifting "
                f"consumption to on-demand rates, or when resources move to premium provisioned tiers."
            )
            pct = Decimal("0.00")
            if total_excess_cost > Decimal("0.00"):
                pct = ((price_effect / total_excess_cost) * Decimal("100")).quantize(Decimal("0.01"))
            findings.append({
                "finding_type": FindingType.FACT.value,
                "title": driver_title,
                "explanation": driver_explanation,
                "dimension": "PRICING_MODEL",
                "financial_impact": price_effect,
                "contribution_percentage": min(Decimal("100.00"), max(Decimal("0.00"), pct)),
                "confidence_category": ConfidenceCategory.HIGH.value,
                "confidence_score": Decimal("0.8500"),
                "evidence_source": EvidenceSource.BILLING_RECORD.value,
                "evidence_reference": "FOCUS_PRICING_DECOMPOSITION",
                "supporting_observations": [
                    f"Unit rate change explains ${price_effect:.2f} of total excess expenditure",
                ],
                "contradictory_observations": [],
                "suggested_next_step": "Check commitment expiration dates or SKU tier migration records.",
            })

            findings.append({
                "finding_type": FindingType.HYPOTHESIS.value,
                "title": "Hypothesis: Commitment Expiration or Shift to On-Demand Pricing Tier",
                "explanation": (
                    "Observed unit rate increased abruptly while usage volume remained relatively stable. "
                    "Suspected causes include expiry of commitment coverage or accidental deployment on on-demand capacity."
                ),
                "dimension": "PRICING_MODEL",
                "financial_impact": price_effect,
                "contribution_percentage": pct,
                "confidence_category": ConfidenceCategory.MEDIUM.value,
                "confidence_score": Decimal("0.7500"),
                "evidence_source": EvidenceSource.HEURISTIC_RULE.value,
                "evidence_reference": None,
                "supporting_observations": ["Sharp unit price delta between baseline and anomaly date"],
                "contradictory_observations": [],
                "suggested_next_step": "Verify active reservation portfolio and apply appropriate savings commitment.",
            })

        # -------------------------------------------------------------------------
        # 3. NEW RESOURCE OR INFRASTRUCTURE ANOMALY
        # -------------------------------------------------------------------------
        if is_new_resource:
            findings.append({
                "finding_type": FindingType.FACT.value,
                "title": f"Newly Provisioned Asset First Observed on Anomaly Date ({top_contributor_id or 'Unknown'})",
                "explanation": (
                    f"The resource {top_contributor_id} had zero historical billing line items "
                    f"prior to the anomaly period, establishing it as a net-new infrastructure deployment."
                ),
                "dimension": "RESOURCE",
                "financial_impact": total_excess_cost,
                "contribution_percentage": top_contributor_share,
                "confidence_category": ConfidenceCategory.HIGH.value,
                "confidence_score": Decimal("0.9500"),
                "evidence_source": EvidenceSource.RESOURCE_INVENTORY.value,
                "evidence_reference": top_contributor_id,
                "supporting_observations": [
                    "Zero historical spend in preceding 30-day baseline window",
                    f"New resource creation confirmed: {top_contributor_id}",
                ],
                "contradictory_observations": [],
                "suggested_next_step": "Verify deployment authorization and infrastructure-as-code change tickets.",
            })

        # -------------------------------------------------------------------------
        # 4. CROSS-SIGNAL CORRELATIONS (Waste Detections & Recommendations)
        # -------------------------------------------------------------------------
        if has_waste_match and waste_rule_name:
            findings.append({
                "finding_type": FindingType.CORRELATION.value,
                "title": f"Correlated with Active Waste Detection: {waste_rule_name}",
                "explanation": (
                    f"CloudSage Waste Detection Engine flagged this resource under rule '{waste_rule_name}'. "
                    f"The resource exhibits wasteful expenditure patterns that directly compound the anomaly impact."
                ),
                "dimension": "RESOURCE",
                "financial_impact": total_excess_cost,
                "contribution_percentage": top_contributor_share,
                "confidence_category": ConfidenceCategory.HIGH.value,
                "confidence_score": Decimal("0.8500"),
                "evidence_source": EvidenceSource.WASTE_DETECTION.value,
                "evidence_reference": waste_rule_name,
                "supporting_observations": [
                    f"Waste engine detection active for rule {waste_rule_name}",
                    "Resource matches idle or overprovisioned criteria",
                ],
                "contradictory_observations": [],
                "suggested_next_step": "Review Waste Management workspace to execute remediation playbook.",
            })

        if has_recommendation and recommendation_title:
            findings.append({
                "finding_type": FindingType.CORRELATION.value,
                "title": f"Correlated with FinOps Recommendation: {recommendation_title}",
                "explanation": (
                    f"CloudSage Recommendation Engine generated advisory playbook '{recommendation_title}' "
                    f"for this affected infrastructure."
                ),
                "dimension": "SERVICE",
                "financial_impact": total_excess_cost,
                "contribution_percentage": top_contributor_share,
                "confidence_category": ConfidenceCategory.MEDIUM.value,
                "confidence_score": Decimal("0.8000"),
                "evidence_source": EvidenceSource.RECOMMENDATION.value,
                "evidence_reference": recommendation_title,
                "supporting_observations": [
                    f"Recommendation '{recommendation_title}' exists in catalog",
                ],
                "contradictory_observations": [],
                "suggested_next_step": "Review and apply advisory recommendation.",
            })

        # -------------------------------------------------------------------------
        # 5. TELEMETRY CORRELATION
        # -------------------------------------------------------------------------
        if telemetry_metrics:
            avg_cpu = telemetry_metrics.get("avg_cpu_percent")
            max_cpu = telemetry_metrics.get("max_cpu_percent")
            if avg_cpu is not None:
                avg_cpu_dec = Decimal(str(avg_cpu))
                if avg_cpu_dec < Decimal("5.0"):
                    findings.append({
                        "finding_type": FindingType.CORRELATION.value,
                        "title": f"Low Compute Utilization Coincident with Cost Surge (Avg CPU: {avg_cpu_dec:.1f}%)",
                        "explanation": (
                            f"During the anomaly window, recorded average CPU utilization remained at {avg_cpu_dec:.1f}%. "
                            f"High spending paired with near-idle telemetry indicates provisioned but unutilized capacity."
                        ),
                        "dimension": "RESOURCE",
                        "financial_impact": total_excess_cost,
                        "contribution_percentage": top_contributor_share,
                        "confidence_category": ConfidenceCategory.HIGH.value,
                        "confidence_score": Decimal("0.8500"),
                        "evidence_source": EvidenceSource.UTILIZATION_METRIC.value,
                        "evidence_reference": "TELEMETRY_CPU_UTILIZATION",
                        "supporting_observations": [
                            f"Average CPU utilization: {avg_cpu_dec:.1f}%",
                            f"Maximum CPU utilization: {max_cpu if max_cpu is not None else 'N/A'}%",
                        ],
                        "contradictory_observations": [],
                        "suggested_next_step": "Investigate instance rightsizing or consider stopping unutilized instance.",
                    })
                elif avg_cpu_dec > Decimal("75.0"):
                    findings.append({
                        "finding_type": FindingType.CORRELATION.value,
                        "title": f"Heavy Compute Workload Corroborates Surge (Avg CPU: {avg_cpu_dec:.1f}%)",
                        "explanation": (
                            f"CPU utilization averaged {avg_cpu_dec:.1f}%, confirming active computational load "
                            f"driving the observed resource billing surge."
                        ),
                        "dimension": "RESOURCE",
                        "financial_impact": total_excess_cost,
                        "contribution_percentage": top_contributor_share,
                        "confidence_category": ConfidenceCategory.HIGH.value,
                        "confidence_score": Decimal("0.8500"),
                        "evidence_source": EvidenceSource.UTILIZATION_METRIC.value,
                        "evidence_reference": "TELEMETRY_CPU_UTILIZATION",
                        "supporting_observations": [
                            f"High sustained CPU load ({avg_cpu_dec:.1f}%) corroborates usage surge",
                        ],
                        "contradictory_observations": [],
                        "suggested_next_step": "Profile workload efficiency or scale horizontally with spot instances.",
                    })

        return findings
