"""
CloudSage Recommendation Correlation and Anti-Double-Counting Unit Tests.
Verifies deduplication key generation, action hierarchy, and conflict suppression.
"""

from decimal import Decimal
import pytest
from backend.app.core.enums import CloudProvider, Priority, RecommendationAction, RiskLevel
from backend.app.recommendations.correlation import (
    filter_and_consolidate_candidates,
    generate_recommendation_key,
)
from backend.app.recommendations.models import RecommendationCandidate


def test_generate_recommendation_key_deterministic():
    """Confirms recommendation key is deterministic for identical inputs."""
    key1 = generate_recommendation_key("AWS", "112233", "i-12345", "TERMINATE", "idle_compute")
    key2 = generate_recommendation_key("AWS", "112233", "i-12345", "TERMINATE", "idle_compute")
    key3 = generate_recommendation_key("AWS", "112233", "i-12345", "RIGHTSIZE", "idle_compute")

    assert key1 == key2
    assert key1 != key3
    assert key1.startswith("rec_")


def test_anti_double_counting_suppression():
    """
    If both TERMINATE and RIGHTSIZE are proposed for the same resource,
    TERMINATE must win and RIGHTSIZE must be suppressed to prevent double-counting savings.
    """
    res_id = "i-overlapping-vm-01"

    cand_terminate = RecommendationCandidate(
        provider=CloudProvider.AWS,
        action_type=RecommendationAction.TERMINATE,
        title="Terminate Idle Instance",
        description="Terminating idle instance",
        remediation_guide="aws ec2 terminate-instances",
        estimated_monthly_savings=Decimal("300.0000"),
        estimated_annual_savings=Decimal("3600.0000"),
        current_monthly_cost=Decimal("300.0000"),
        projected_monthly_cost=Decimal("0.0000"),
        strategy_id="idle_compute_strategy",
        resource_id=res_id,
        account_id="112233",
        priority=Priority.P1,
        priority_score=Decimal("0.8500"),
    )

    cand_rightsize = RecommendationCandidate(
        provider=CloudProvider.AWS,
        action_type=RecommendationAction.RIGHTSIZE,
        title="Rightsize Instance",
        description="Rightsizing oversized instance",
        remediation_guide="aws ec2 modify-instance-attribute",
        estimated_monthly_savings=Decimal("150.0000"),
        estimated_annual_savings=Decimal("1800.0000"),
        current_monthly_cost=Decimal("300.0000"),
        projected_monthly_cost=Decimal("150.0000"),
        strategy_id="compute_rightsizing_strategy",
        resource_id=res_id,
        account_id="112233",
        priority=Priority.P2,
        priority_score=Decimal("0.6000"),
    )

    active, suppressed = filter_and_consolidate_candidates([cand_terminate, cand_rightsize])

    assert len(active) == 1
    assert active[0].action_type == RecommendationAction.TERMINATE
    assert len(suppressed) == 1
    assert suppressed[0]["resource_id"] == res_id
    assert suppressed[0]["suppressed_action"] == RecommendationAction.RIGHTSIZE.value
    assert "Anti-double-counting" in suppressed[0]["reason"]


def test_independent_resources_both_kept():
    """Candidates targeting different resources are both retained."""
    cand1 = RecommendationCandidate(
        provider=CloudProvider.AWS,
        action_type=RecommendationAction.TERMINATE,
        title="Terminate Node A",
        description="...",
        remediation_guide="...",
        estimated_monthly_savings=Decimal("100.0000"),
        estimated_annual_savings=Decimal("1200.0000"),
        current_monthly_cost=Decimal("100.0000"),
        projected_monthly_cost=Decimal("0.0000"),
        strategy_id="idle_compute_strategy",
        resource_id="i-res-aaa",
    )
    cand2 = RecommendationCandidate(
        provider=CloudProvider.AWS,
        action_type=RecommendationAction.RIGHTSIZE,
        title="Rightsize Node B",
        description="...",
        remediation_guide="...",
        estimated_monthly_savings=Decimal("80.0000"),
        estimated_annual_savings=Decimal("960.0000"),
        current_monthly_cost=Decimal("160.0000"),
        projected_monthly_cost=Decimal("80.0000"),
        strategy_id="compute_rightsizing_strategy",
        resource_id="i-res-bbb",
    )

    active, suppressed = filter_and_consolidate_candidates([cand1, cand2])
    assert len(active) == 2
    assert len(suppressed) == 0
