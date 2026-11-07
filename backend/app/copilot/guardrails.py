"""
Security and Policy Guardrails for CloudSage AI FinOps Copilot.
Enforces prompt injection detection, sensitive data sanitization,
strict advisory-only mutation denial, and SQL injection prevention.
"""

import re
from typing import Dict, List, Optional, Tuple


# Patterns indicative of prompt injection or system prompt extraction attempts
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|directions|prompts)",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|directions|rules)",
    r"system\s+prompt\s+(reveal|leak|show|print|dump)",
    r"what\s+(are|is)\s+your\s+(original|system|core)\s+(instructions|prompt)",
    r"act\s+as\s+(dan|an\s+unfiltered|root|admin|superuser)",
    r"jailbreak",
    r"bypass\s+(safety|rules|guardrails|policy|filters)",
    r"developer\s+mode\s+(enable|activated|on)",
    r"print\s+your\s+rules",
    r"reveal\s+your\s+hidden\s+instructions",
    r"you\s+are\s+now\s+in\s+(god|maintenance|unrestricted)\s+mode",
]

# Patterns attempting mutating / destructive cloud infrastructure actions
MUTATION_PATTERNS = [
    r"(delete|terminate|destroy|kill|tear\s*down)\s+.*(instance|vm|server|database|disk|volume|snapshot|cluster|resource)",
    r"(shut\s*down|stop|reboot|restart)\s+.*(instance|vm|server|database|cluster|resource)",
    r"(resize|downsize|upsize)\s+.*(instance|vm|database|disk)",
    r"(execute|apply|deploy|run)\s+.*recommendation",
    r"drop\s+(table|database|schema|column)",
    r"truncate\s+table",
    r"modify\s+security\s+group",
]

# Patterns for sensitive credentials and secrets
SECRET_PATTERNS = [
    r"(AKIA[0-9A-Z]{16})",  # AWS Access Key ID
    r"(ghp_[0-9a-zA-Z]{36})",  # GitHub token
    r"([a-zA-Z0-9_-]{20,}:[a-zA-Z0-9_-]{40,})",  # Generic API secret pairs
    r"-----BEGIN\s+(RSA|OPENSSH|DSA|EC)?\s*PRIVATE\s+KEY-----",
    r"(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)",  # JWT Token
]


class GuardrailViolationError(Exception):
    """Raised when a query violates security or safety guardrails."""
    def __init__(self, reason: str, category: str):
        super().__init__(reason)
        self.reason = reason
        self.category = category


class CopilotGuardrails:
    """Validates user queries and assistant outputs against security and advisory rules."""

    @classmethod
    def validate_query(cls, query: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validates the incoming user query.
        Returns:
            (is_safe, error_category, explanation_message)
        """
        if not query or not query.strip():
            return False, "EMPTY_QUERY", "Query cannot be empty."

        clean_query = query.strip()

        # 1. Check Prompt Injection
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, clean_query, re.IGNORECASE):
                return (
                    False,
                    "PROMPT_INJECTION_DETECTED",
                    "Adversarial or prompt manipulation instruction detected. "
                    "CloudSage Copilot processes only FinOps domain questions.",
                )

        # 2. Check Mutating / Cloud Deletion Requests (Advisory-Only Enforcement)
        for pattern in MUTATION_PATTERNS:
            if re.search(pattern, clean_query, re.IGNORECASE):
                return (
                    False,
                    "MUTATION_DISALLOWED",
                    "CloudSage operates strictly as an advisory FinOps copilot. "
                    "Direct infrastructure modifications, automatic resource termination, "
                    "or deletion actions are strictly prohibited. Please review and execute "
                    "recommended actions through your cloud management console or IaC pipelines.",
                )

        # 3. Check for Secret Leakage in Query
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, clean_query):
                return (
                    False,
                    "SENSITIVE_DATA_DETECTED",
                    "The query appears to contain sensitive credentials, keys, or tokens. "
                    "CloudSage does not accept or store private credentials.",
                )

        return True, None, None

    @classmethod
    def sanitize_output(cls, text: str) -> str:
        """Sanitizes outgoing LLM output, masking any accidental credential strings."""
        sanitized = text
        for pattern in SECRET_PATTERNS:
            sanitized = re.sub(pattern, "[REDACTED_SECRET]", sanitized)
        return sanitized

    @classmethod
    def enforce_advisory_disclaimer(cls, response_text: str) -> str:
        """Ensures that every optimization advice carries the required advisory disclaimer."""
        disclaimer = (
            "\n\n*Advisory Notice: CloudSage recommendations are strictly advisory. "
            "Validate with system owners before implementing changes.*"
        )
        if "advisory" not in response_text.lower():
            return response_text + disclaimer
        return response_text
