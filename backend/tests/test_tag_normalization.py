"""
CloudSage Tag Normalization, Governance, and Quality Scoring Tests.
Verifies prefix removal, regex metadata extraction, environment standardization, and hygiene scoring.
"""

from decimal import Decimal
import pytest
from backend.app.normalization.tags.extractor import TagExtractor
from backend.app.normalization.tags.quality import TagQualityScorer
from backend.app.normalization.tags.sanitizer import TagSanitizer


def test_tag_sanitizer_prefix_and_casing():
    """Verify provider prefixes are stripped and keys are converted to snake_case."""
    raw_tags = {
        "resourceTags/user:Owner": "FinOps Team",
        "labels/environment": "Production",
        "tag:Cost-Center": "CC-1002",
        "Application Name": "CloudSage Core",
        "user:EmptyTag": "",
    }

    sanitized, warnings = TagSanitizer.sanitize(raw_tags)
    assert sanitized["owner"] == "FinOps Team"
    assert sanitized["environment"] == "Production"
    assert sanitized["cost_center"] == "CC-1002"
    assert sanitized["application_name"] == "CloudSage Core"
    assert sanitized["emptytag"] == ""
    assert any("empty value" in w for w in warnings)


def test_tag_extractor_regex_and_environment_standardization():
    """Verify regex extraction accurately extracts attributes and standardizes environment tokens."""
    tags = {
        "creator": "alice@company.com",
        "env": "prod",  # Should standardize to 'production'
        "cc": "FIN-200",
        "app": "PaymentGateway",
        "bu": "Payments Engineering",
    }

    meta = TagExtractor.extract_metadata(tags)
    assert meta["owner"] == "alice@company.com"
    assert meta["environment"] == "production"
    assert meta["cost_center"] == "FIN-200"
    assert meta["project"] == "PaymentGateway"
    assert meta["department"] == "Payments Engineering"


def test_tag_quality_scoring_full_coverage():
    """Verify resources with complete FinOps governance tags receive 100% and EXCELLENT rating."""
    sanitized = {
        "owner": "devops@company.com",
        "environment": "production",
        "project": "CloudSage",
        "cost_center": "CC-99",
    }
    extracted = TagExtractor.extract_metadata(sanitized)
    report = TagQualityScorer.evaluate("res-1", sanitized, sanitized, extracted)

    assert report.quality_score == Decimal("100.00")
    assert report.hygiene_rating == "EXCELLENT"
    assert len(report.missing_mandatory_tags) == 0


def test_tag_quality_scoring_missing_owner():
    """Verify resources missing owner tags are penalized and flagged."""
    sanitized = {
        "environment": "production",
        "project": "CloudSage",
    }
    extracted = TagExtractor.extract_metadata(sanitized)
    report = TagQualityScorer.evaluate("res-2", sanitized, sanitized, extracted)

    assert "owner" in report.missing_mandatory_tags
    assert report.quality_score < Decimal("90.00")


def test_tag_quality_scoring_completely_untagged():
    """Verify untagged resources receive 0.00 score and UNTAGGED rating."""
    report = TagQualityScorer.evaluate("res-orphaned", {}, {}, {})
    assert report.quality_score == Decimal("0.00")
    assert report.hygiene_rating == "UNTAGGED"
    assert len(report.missing_mandatory_tags) == 4
