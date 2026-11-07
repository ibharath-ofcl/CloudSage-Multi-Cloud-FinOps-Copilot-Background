"""
CloudSage Recommendation Correlation and Anti-Double-Counting Engine.
Consolidates cross-stage findings (waste detections, cost anomalies, metric telemetry)
and enforces anti-double-counting rules across overlapping optimization candidates.
"""

import hashlib
from typing import Dict, List, Optional, Set, Tuple

from backend.app.core.enums import RecommendationAction
from backend.app.recommendations.models import RecommendationCandidate


# Action priority ranking: higher rank wins when conflicting actions target the same resource
ACTION_HIERARCHY: Dict[RecommendationAction, int] = {
    RecommendationAction.TERMINATE: 100,
    RecommendationAction.RELEASE_IP: 100,
    RecommendationAction.CLEANUP_UNATTACHED: 90,
    RecommendationAction.DELETE_SNAPSHOT: 85,
    RecommendationAction.RIGHTSIZE: 70,
    RecommendationAction.PAUSE: 65,
    RecommendationAction.SCHEDULE_SHUTDOWN: 60,
    RecommendationAction.CONVERT_STORAGE_TIER: 50,
    RecommendationAction.PURCHASE_SAVINGS_PLAN: 40,
    RecommendationAction.RESERVE_CAPACITY: 40,
    RecommendationAction.INVESTIGATE_ANOMALY: 30,
}


def generate_recommendation_key(
    provider: str,
    account_id: Optional[str],
    resource_id: Optional[str],
    action_type: str,
    strategy_id: Optional[str] = None,
) -> str:
    """
    Computes a deterministic hash key for deduplicating recommendations.
    Format: sha256(provider:account_id:resource_id:action_type:strategy_id)[:32]
    """
    prov_str = (provider or "UNKNOWN").upper()
    acc_str = (account_id or "GLOBAL").strip()
    res_str = (resource_id or "ACCOUNT_SCOPED").strip()
    act_str = (action_type or "OPTIMIZE").upper()
    strat_str = (strategy_id or "DEFAULT").strip()

    raw_key = f"{prov_str}:{acc_str}:{res_str}:{act_str}:{strat_str}"
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return f"rec_{digest[:28]}"


def filter_and_consolidate_candidates(
    candidates: List[RecommendationCandidate],
) -> Tuple[List[RecommendationCandidate], List[Dict[str, str]]]:
    """
    Applies anti-double-counting and action precedence rules across candidates.
    If multiple recommendations target the same resource:
      - TERMINATE takes absolute precedence over RIGHTSIZE or SCHEDULE_SHUTDOWN.
      - Higher priority/savings wins when conflicting actions collide.
    Returns:
      (active_candidates, suppressed_records)
    """
    grouped_by_resource: Dict[str, List[RecommendationCandidate]] = {}
    unscoped_candidates: List[RecommendationCandidate] = []

    for cand in candidates:
        if not cand.recommendation_key:
            cand.recommendation_key = generate_recommendation_key(
                provider=cand.provider.value,
                account_id=cand.account_id,
                resource_id=cand.resource_id,
                action_type=cand.action_type.value,
                strategy_id=cand.strategy_id,
            )

        if not cand.resource_id:
            unscoped_candidates.append(cand)
        else:
            grouped_by_resource.setdefault(cand.resource_id, []).append(cand)

    active_candidates: List[RecommendationCandidate] = list(unscoped_candidates)
    suppressed_logs: List[Dict[str, str]] = []

    for res_id, res_candidates in grouped_by_resource.items():
        if len(res_candidates) == 1:
            active_candidates.append(res_candidates[0])
            continue

        # Sort candidates targeting the same resource by:
        # 1. Action hierarchy rank (e.g. TERMINATE > RIGHTSIZE)
        # 2. Priority score descending
        # 3. Monthly savings descending
        sorted_candidates = sorted(
            res_candidates,
            key=lambda c: (
                ACTION_HIERARCHY.get(c.action_type, 0),
                c.priority_score,
                c.estimated_monthly_savings,
            ),
            reverse=True,
        )

        winning_candidate = sorted_candidates[0]
        active_candidates.append(winning_candidate)

        for suppressed in sorted_candidates[1:]:
            suppressed_logs.append({
                "resource_id": res_id,
                "suppressed_strategy": suppressed.strategy_id,
                "suppressed_action": suppressed.action_type.value,
                "winning_action": winning_candidate.action_type.value,
                "reason": (
                    f"Anti-double-counting: {winning_candidate.action_type.value} on {res_id} "
                    f"supersedes {suppressed.action_type.value} (${suppressed.estimated_monthly_savings:.2f}/mo savings suppressed)."
                ),
            })

    return active_candidates, suppressed_logs
