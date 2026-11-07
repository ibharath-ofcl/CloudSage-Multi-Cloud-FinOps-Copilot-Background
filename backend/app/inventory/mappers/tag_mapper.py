"""
CloudSage Inventory Tag Mapper.
Connects Stage 4 Tag Sanitization, Extraction, and Quality Scoring into inventory resources.
"""

from decimal import Decimal
from typing import Any, Dict, Optional, Tuple
from backend.app.normalization.tags.extractor import TagExtractor
from backend.app.normalization.tags.quality import TagQualityScorer
from backend.app.normalization.tags.sanitizer import TagSanitizer


class InventoryTagMapper:
    """Enriches inventory assets with clean tags and FinOps governance attributes."""

    @classmethod
    def process_tags(
        cls,
        resource_id: str,
        raw_tags: Any,
    ) -> Tuple[Dict[str, str], Dict[str, Optional[str]], Decimal]:
        """
        Processes raw tags:
        1. Sanitizes keys and values
        2. Extracts FinOps attributes (owner, department, project, environment, cost_center)
        3. Computes Tag Hygiene Score (0.00 to 100.00)
        Returns: (sanitized_tags, extracted_metadata, hygiene_score)
        """
        sanitized, _ = TagSanitizer.sanitize(raw_tags)
        extracted = TagExtractor.extract_metadata(sanitized)
        quality_res = TagQualityScorer.evaluate(
            resource_id=resource_id,
            raw_tags=raw_tags if isinstance(raw_tags, dict) else {},
            sanitized_tags=sanitized,
            extracted_metadata=extracted,
        )

        return sanitized, extracted, quality_res.quality_score
