"""
CloudSage Waste Finding Severity Evaluator.
Maps financial savings thresholds and operational risk levels to standardized Severity rankings.
"""

from decimal import Decimal
from backend.app.core.enums import Severity


class SeverityEvaluator:
    """Evaluates finding severity based on financial impact and risk profile."""

    CRITICAL_SAVINGS_THRESHOLD = Decimal("500.0000")
    HIGH_SAVINGS_THRESHOLD = Decimal("150.0000")
    MEDIUM_SAVINGS_THRESHOLD = Decimal("30.0000")

    @classmethod
    def evaluate_severity(
        cls,
        estimated_monthly_savings: Decimal,
        is_informational_only: bool = False,
    ) -> Severity:
        """
        Calculates standardized severity tier:
        - CRITICAL: >= $500/mo waste
        - HIGH: >= $150/mo waste
        - MEDIUM: >= $30/mo waste
        - LOW: < $30/mo waste (> $0)
        - INFORMATIONAL: $0 waste or governance advisory
        """
        if is_informational_only or estimated_monthly_savings <= Decimal("0.0000"):
            return Severity.INFORMATIONAL

        if estimated_monthly_savings >= cls.CRITICAL_SAVINGS_THRESHOLD:
            return Severity.CRITICAL
        elif estimated_monthly_savings >= cls.HIGH_SAVINGS_THRESHOLD:
            return Severity.HIGH
        elif estimated_monthly_savings >= cls.MEDIUM_SAVINGS_THRESHOLD:
            return Severity.MEDIUM
        else:
            return Severity.LOW
