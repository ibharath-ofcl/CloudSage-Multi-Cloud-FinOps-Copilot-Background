"""
CloudSage Recommendation Engine Package.
Advisory FinOps Optimization and Prioritization Platform.
"""

from backend.app.recommendations.base import BaseRecommendationStrategy
from backend.app.recommendations.correlation import (
    filter_and_consolidate_candidates,
    generate_recommendation_key,
)
from backend.app.recommendations.engine import RecommendationEngine
from backend.app.recommendations.evidence import (
    create_anomaly_evidence_link,
    create_metric_evidence_link,
    create_waste_evidence_link,
    validate_candidate_evidence,
)
from backend.app.recommendations.guidance import (
    ADVISORY_DISCLAIMER,
    build_implementation_guidance,
    generate_cli_command,
    generate_rollback_procedure,
    generate_terraform_snippet,
)
from backend.app.recommendations.lifecycle import (
    InvalidStateTransitionError,
    RejectionReasonRequiredError,
    transition_recommendation_status,
)
from backend.app.recommendations.models import (
    EvidenceLink,
    RecommendationCandidate,
    ScoringBreakdown,
    StrategyResult,
)
from backend.app.recommendations.registry import (
    RecommendationRegistry,
    get_recommendation_registry,
)
from backend.app.recommendations.savings import (
    annualize_savings,
    build_savings_breakdown,
    calculate_commitment_savings,
    calculate_idle_release_savings,
    calculate_rightsizing_savings,
    calculate_roi,
    calculate_savings_percentage,
    calculate_schedule_savings,
    calculate_storage_tier_savings,
    calculate_termination_savings,
    quantize_currency,
)
from backend.app.recommendations.scoring import (
    compute_multi_factor_score,
    quantize_score,
)
from backend.app.recommendations.synthetic import (
    SYNTHETIC_SCENARIOS,
    seed_synthetic_recommendation_scenarios,
)


def get_recommendation_engine() -> RecommendationEngine:
    """Singleton-like factory returning RecommendationEngine instance."""
    return RecommendationEngine()


__all__ = [
    "BaseRecommendationStrategy",
    "RecommendationRegistry",
    "get_recommendation_registry",
    "RecommendationEngine",
    "get_recommendation_engine",
    "RecommendationCandidate",
    "EvidenceLink",
    "ScoringBreakdown",
    "StrategyResult",
    "compute_multi_factor_score",
    "quantize_score",
    "quantize_currency",
    "calculate_termination_savings",
    "calculate_idle_release_savings",
    "calculate_rightsizing_savings",
    "calculate_schedule_savings",
    "calculate_storage_tier_savings",
    "calculate_commitment_savings",
    "annualize_savings",
    "calculate_savings_percentage",
    "calculate_roi",
    "build_savings_breakdown",
    "generate_cli_command",
    "generate_terraform_snippet",
    "generate_rollback_procedure",
    "build_implementation_guidance",
    "ADVISORY_DISCLAIMER",
    "generate_recommendation_key",
    "filter_and_consolidate_candidates",
    "transition_recommendation_status",
    "InvalidStateTransitionError",
    "RejectionReasonRequiredError",
    "create_waste_evidence_link",
    "create_anomaly_evidence_link",
    "create_metric_evidence_link",
    "validate_candidate_evidence",
    "SYNTHETIC_SCENARIOS",
    "seed_synthetic_recommendation_scenarios",
]
