"""
CloudSage FinOps Tag Extractor.
Extracts standard organizational metadata (owner, environment, cost center, project, department)
using configurable regular expressions and standardizes canonical values.
"""

import re
from typing import Dict, Optional


class TagExtractor:
    """Extracts core FinOps metadata from sanitized tags."""

    # Configurable regex patterns for FinOps attributes
    OWNER_PATTERNS = [
        re.compile(r"^(owner|creator|created_by|team|author|contact)$", re.IGNORECASE),
    ]
    ENVIRONMENT_PATTERNS = [
        re.compile(r"^(environment|env|stage|tier)$", re.IGNORECASE),
    ]
    COST_CENTER_PATTERNS = [
        re.compile(r"^(cost_center|costcenter|cc|billing_code|cost_code)$", re.IGNORECASE),
    ]
    PROJECT_PATTERNS = [
        re.compile(r"^(project|project_name|app|application|workload)$", re.IGNORECASE),
    ]
    DEPARTMENT_PATTERNS = [
        re.compile(r"^(department|dept|org|business_unit|bu)$", re.IGNORECASE),
    ]

    # Canonical environment value standardization
    ENV_STANDARDIZATION_MAP: Dict[str, str] = {
        "prod": "production",
        "prd": "production",
        "production": "production",
        "dev": "development",
        "development": "development",
        "stg": "staging",
        "stage": "staging",
        "staging": "staging",
        "test": "testing",
        "testing": "testing",
        "qa": "testing",
        "uat": "testing",
        "sandbox": "sandbox",
        "sbx": "sandbox",
    }

    @classmethod
    def standardize_environment(cls, env_val: Optional[str]) -> Optional[str]:
        """Standardizes environment names to canonical tokens (e.g. 'prod' -> 'production')."""
        if not env_val:
            return None
        cleaned = env_val.strip().lower()
        return cls.ENV_STANDARDIZATION_MAP.get(cleaned, cleaned)

    @classmethod
    def extract_metadata(cls, tags: Dict[str, str]) -> Dict[str, Optional[str]]:
        """
        Extracts core FinOps attributes from normalized tags.
        Returns dictionary with keys: owner, environment, cost_center, project, department.
        """
        owner: Optional[str] = None
        environment: Optional[str] = None
        cost_center: Optional[str] = None
        project: Optional[str] = None
        department: Optional[str] = None

        for k, v in tags.items():
            val = v.strip()
            if not val:
                continue

            # Owner
            if not owner and any(pat.match(k) for pat in cls.OWNER_PATTERNS):
                owner = val

            # Environment
            if not environment and any(pat.match(k) for pat in cls.ENVIRONMENT_PATTERNS):
                environment = cls.standardize_environment(val)

            # Cost Center
            if not cost_center and any(pat.match(k) for pat in cls.COST_CENTER_PATTERNS):
                cost_center = val

            # Project
            if not project and any(pat.match(k) for pat in cls.PROJECT_PATTERNS):
                project = val

            # Department
            if not department and any(pat.match(k) for pat in cls.DEPARTMENT_PATTERNS):
                department = val

        return {
            "owner": owner,
            "environment": environment,
            "cost_center": cost_center,
            "project": project,
            "department": department,
        }
