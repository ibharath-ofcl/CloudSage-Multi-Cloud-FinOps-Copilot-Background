"""
CloudSage Synthetic Recommendation Scenarios Tests.
Validates that all 20 synthetic scenarios seed correctly and satisfy multi-cloud FinOps requirements.
"""

from decimal import Decimal
import pytest
from backend.app.core.enums import CloudProvider
from backend.app.models.recommendation import Recommendation, RecommendationEvidence
from backend.app.recommendations.synthetic import (
    SYNTHETIC_SCENARIOS,
    seed_synthetic_recommendation_scenarios,
)


def test_seed_synthetic_recommendation_scenarios(db_session):
    """Verifies seeding all 20 scenarios across AWS, Azure, and GCP."""
    recs = seed_synthetic_recommendation_scenarios(db_session)
    assert len(recs) == 20

    providers = {r.provider for r in recs}
    assert "AWS" in providers
    assert "AZURE" in providers
    assert "GCP" in providers

    total_monthly = sum((r.estimated_monthly_savings for r in recs), Decimal("0.0000"))
    assert total_monthly > Decimal("5000.0000")

    for r in recs:
        # Precision assertions
        assert isinstance(r.estimated_monthly_savings, Decimal)
        assert isinstance(r.estimated_annual_savings, Decimal)
        assert r.estimated_annual_savings == r.estimated_monthly_savings * Decimal("12")
        assert len(r.title) > 0
        assert len(r.remediation_guide) > 0
        assert r.savings_calculation is not None
        assert r.implementation_guidance is not None

        # Evidence assertions
        ev_items = db_session.query(RecommendationEvidence).filter_by(recommendation_id=r.id).all()
        assert len(ev_items) >= 1
