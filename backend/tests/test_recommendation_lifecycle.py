"""
CloudSage Recommendation Lifecycle State Machine Unit Tests.
Tests valid transitions, invalid transition rejections, mandatory justification, and audit history.
"""

from decimal import Decimal
import uuid
import pytest
from backend.app.core.enums import CloudProvider, Priority, RecommendationAction, RecommendationStatus, RiskLevel
from backend.app.models.recommendation import Recommendation, RecommendationHistory
from backend.app.recommendations.lifecycle import (
    InvalidStateTransitionError,
    RejectionReasonRequiredError,
    transition_recommendation_status,
)


@pytest.fixture
def sample_recommendation(db_session):
    """Creates a sample recommendation in PROPOSED status."""
    rec = Recommendation(
        id=uuid.uuid4(),
        provider=CloudProvider.AWS.value,
        action_type=RecommendationAction.TERMINATE.value,
        title="Test Proposal",
        description="Test description",
        remediation_guide="aws ec2 terminate-instances",
        estimated_monthly_savings=Decimal("250.0000"),
        estimated_annual_savings=Decimal("3000.0000"),
        current_monthly_cost=Decimal("250.0000"),
        projected_monthly_cost=Decimal("0.0000"),
        status=RecommendationStatus.PROPOSED.value,
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)
    return rec


def test_valid_lifecycle_transitions(db_session, sample_recommendation):
    """Tests normal path: PROPOSED -> UNDER_REVIEW -> APPROVED -> IN_PROGRESS -> IMPLEMENTED -> VERIFIED."""
    rec_id = sample_recommendation.id

    # 1. Move to UNDER_REVIEW
    r1 = transition_recommendation_status(
        db=db_session,
        recommendation_id=rec_id,
        new_status=RecommendationStatus.UNDER_REVIEW,
        actor="analyst@enterprise.com",
    )
    assert r1.status == "UNDER_REVIEW"

    # 2. Approve
    r2 = transition_recommendation_status(
        db=db_session,
        recommendation_id=rec_id,
        new_status=RecommendationStatus.APPROVED,
        actor="finops-lead@enterprise.com",
    )
    assert r2.status == "APPROVED"
    assert r2.approved_by == "finops-lead@enterprise.com"
    assert r2.approved_at is not None

    # 3. In Progress
    r3 = transition_recommendation_status(
        db=db_session,
        recommendation_id=rec_id,
        new_status=RecommendationStatus.IN_PROGRESS,
        actor="engineer@enterprise.com",
    )
    assert r3.status == "IN_PROGRESS"

    # 4. Implemented
    r4 = transition_recommendation_status(
        db=db_session,
        recommendation_id=rec_id,
        new_status=RecommendationStatus.IMPLEMENTED,
        actor="engineer@enterprise.com",
    )
    assert r4.status == "IMPLEMENTED"
    assert r4.implemented_at is not None

    # 5. Verified
    r5 = transition_recommendation_status(
        db=db_session,
        recommendation_id=rec_id,
        new_status=RecommendationStatus.VERIFIED,
        actor="finops-lead@enterprise.com",
        verified_savings=Decimal("245.0000"),
    )
    assert r5.status == "VERIFIED"
    assert r5.verified_savings == Decimal("245.0000")
    assert r5.verified_at is not None

    # Check history records
    history = db_session.query(RecommendationHistory).filter_by(recommendation_id=rec_id).all()
    assert len(history) == 5


def test_invalid_transition_raises_error(db_session, sample_recommendation):
    """Skipping lifecycle stages (e.g. PROPOSED directly to VERIFIED) must raise InvalidStateTransitionError."""
    with pytest.raises(InvalidStateTransitionError):
        transition_recommendation_status(
            db=db_session,
            recommendation_id=sample_recommendation.id,
            new_status=RecommendationStatus.VERIFIED,
            actor="attacker@test.com",
        )


def test_dismissal_requires_reason(db_session, sample_recommendation):
    """Dismissing or rejecting a recommendation without a reason must raise RejectionReasonRequiredError."""
    with pytest.raises(RejectionReasonRequiredError):
        transition_recommendation_status(
            db=db_session,
            recommendation_id=sample_recommendation.id,
            new_status=RecommendationStatus.DISMISSED,
            actor="reviewer@enterprise.com",
            reason="",  # Empty reason
        )

    # Valid dismissal with reason
    dismissed = transition_recommendation_status(
        db=db_session,
        recommendation_id=sample_recommendation.id,
        new_status=RecommendationStatus.DISMISSED,
        actor="reviewer@enterprise.com",
        reason="Instance is reserved for upcoming DR failover exercise next month.",
    )
    assert dismissed.status == "DISMISSED"
    assert dismissed.review_reason == "Instance is reserved for upcoming DR failover exercise next month."
