"""
CloudSage Tag Sanitizer.
Cleans and normalizes heterogeneous multi-cloud resource tags and labels.
"""

import re
from typing import Any, Dict, List, Tuple


class TagSanitizer:
    """Sanitizes raw tags from AWS, Azure, and GCP into uniform key-value pairs."""

    PROVIDER_PREFIXES = [
        "resourcetags/user:",
        "resourcetags/aws:",
        "user:",
        "tag:",
        "labels/",
        "labels:",
    ]

    INVALID_CHAR_REGEX = re.compile(r"[^a-zA-Z0-9_\-\.\:\/]")

    @classmethod
    def sanitize(cls, raw_tags: Any) -> Tuple[Dict[str, str], List[str]]:
        """
        Cleans tag dictionary:
        - Strips provider prefixes.
        - Trims whitespace.
        - Converts keys to snake_case lowercase.
        - Filters out empty keys/values.
        - Detects invalid tags.
        Returns: (sanitized_dict, warnings)
        """
        if not raw_tags or not isinstance(raw_tags, dict):
            return {}, ["No tags present or tags is not a valid dictionary"]

        sanitized: Dict[str, str] = {}
        warnings: List[str] = []

        for raw_k, raw_v in raw_tags.items():
            if raw_k is None or str(raw_k).strip() == "":
                warnings.append("Encountered empty or null tag key; skipped")
                continue

            # Strip whitespace
            key_str = str(raw_k).strip()
            val_str = str(raw_v).strip() if raw_v is not None else ""

            if val_str == "":
                warnings.append(f"Tag key '{key_str}' has empty value")

            # Strip provider prefixes (case-insensitively)
            key_lower = key_str.lower()
            for prefix in cls.PROVIDER_PREFIXES:
                if key_lower.startswith(prefix):
                    key_lower = key_lower[len(prefix):]
                    break

            # Normalize key: replace spaces and hyphens with underscores
            clean_key = key_lower.replace("-", "_").replace(" ", "_")

            # Validate key character set
            if cls.INVALID_CHAR_REGEX.search(clean_key):
                warnings.append(f"Tag key '{clean_key}' contains invalid characters")

            # Store in sanitized dict
            sanitized[clean_key] = val_str

        return sanitized, warnings
