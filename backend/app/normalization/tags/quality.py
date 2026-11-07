"""
CloudSage Tag Quality and Governance Scorer.
Computes tag quality scores and evaluates compliance against FinOps tagging policies.
"""

from decimal import Decimal
from typing import Dict, List, Optional
from backend.app.schemas.normalization import TagQualityAnalysisResult


class TagQualityScorer:
    """Evaluates tag hygiene, coverage of mandatory keys, and overall quality score."""

    MANDATORY_WEIGHTS: Dict[str, int] = {
        "owner": 30,
        "environment": 30,
        "project": 20,
        "cost_center": 20,
    }

    @classmethod
    def evaluate(
        cls,
        resource_id: str,
        raw_tags: Dict[str, str],
        sanitized_tags: Dict[str, str],
        extracted_metadata: Dict[str, Optional[str]],
    ) -> TagQualityAnalysisResult:
        """
        Calculates tag score out of 100 points based on coverage of core FinOps tags.
        """
        if not sanitized_tags:
            return TagQualityAnalysisResult(
                resource_id=resource_id,
                raw_tags_count=len(raw_tags) if isinstance(raw_tags, dict) else 0,
                normalized_tags_count=0,
                sanitized_tags={},
                extracted_owner=None,
                extracted_environment=None,
                extracted_cost_center=None,
                extracted_project=None,
                extracted_department=None,
                missing_mandatory_tags=["owner", "environment", "project", "cost_center"],
                quality_score=Decimal("0.00"),
                hygiene_rating="UNTAGGED",
            )

        score = 0
        missing_mandatory: List[str] = []

        for attr, weight in cls.MANDATORY_WEIGHTS.items():
            if extracted_metadata.get(attr):
                score += weight
            else:
                missing_mandatory.append(attr)

        # Rating classification
        if score >= 90:
            rating = "EXCELLENT"
        elif score >= 70:
            rating = "GOOD"
        elif score > 0:
            rating = "POOR"
        else:
            rating = "UNTAGGED"

        return TagQualityAnalysisResult(
            resource_id=resource_id,
            raw_tags_count=len(raw_tags),
            normalized_tags_count=len(sanitized_tags),
            sanitized_tags=sanitized_tags,
            extracted_owner=extracted_metadata.get("owner"),
            extracted_environment=extracted_metadata.get("environment"),
            extracted_cost_center=extracted_metadata.get("cost_center"),
            extracted_project=extracted_metadata.get("project"),
            extracted_department=extracted_metadata.get("department"),
            missing_mandatory_tags=missing_mandatory,
            quality_score=Decimal(str(score)).quantize(Decimal("0.01")),
            hygiene_rating=rating,
        )
