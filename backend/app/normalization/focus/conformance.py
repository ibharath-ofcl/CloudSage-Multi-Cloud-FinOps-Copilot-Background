"""
CloudSage FOCUS 1.0 Conformance Assessment Engine.
Generates conformance summaries and assessment matrices across datasets.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from backend.app.schemas.normalization import FocusConformanceSummary, FocusValidationResult


class FocusConformanceEngine:
    """Generates enterprise conformance reports and matrices for FOCUS 1.0."""

    FULLY_SUPPORTED = [
        "BillingAccountId",
        "BillingCurrency",
        "ChargeCategory",
        "ChargePeriodStart",
        "ChargePeriodEnd",
        "ConsumedQuantity",
        "ConsumedUnit",
        "EffectiveCost",
        "BilledCost",
        "PricingCategory",
        "ProviderName",
        "RegionId",
        "ResourceId",
        "ResourceName",
        "ResourceType",
        "ServiceCategory",
        "ServiceName",
        "SubAccountId",
        "Tags",
        "x_OriginalCost",
        "x_OriginalCurrency",
        "x_Fingerprint",
    ]

    PARTIALLY_SUPPORTED = [
        "BillingAccountName",
        "SubAccountName",
        "ListCost",
        "RegionName",
        "ChargeDescription",
    ]

    UNSUPPORTED = [
        "CommitmentDiscountCategory",
        "CapacityReservationId",
        "SkuPriceId",
    ]

    @classmethod
    def generate_summary(cls, results: List[FocusValidationResult]) -> FocusConformanceSummary:
        """Aggregates a set of validation results into a conformance report."""
        total = len(results)
        if total == 0:
            return FocusConformanceSummary(
                assessment_date=datetime.now(timezone.utc),
                total_evaluated_records=0,
                fully_compliant_count=0,
                conformance_percentage=Decimal("100.00"),
                mandatory_coverage_percentage=Decimal("100.00"),
                unsupported_columns=cls.UNSUPPORTED,
                partially_supported_columns=cls.PARTIALLY_SUPPORTED,
                fully_supported_columns=cls.FULLY_SUPPORTED,
            )

        compliant_count = sum(1 for r in results if r.is_compliant)
        avg_score = sum(r.compliance_score for r in results) / Decimal(str(total))
        mand_coverage = (
            sum(r.mandatory_columns_passed for r in results)
            / (Decimal(str(total)) * Decimal("11"))
            * Decimal("100")
        )

        return FocusConformanceSummary(
            assessment_date=datetime.now(timezone.utc),
            total_evaluated_records=total,
            fully_compliant_count=compliant_count,
            conformance_percentage=avg_score.quantize(Decimal("0.01")),
            mandatory_coverage_percentage=mand_coverage.quantize(Decimal("0.01")),
            unsupported_columns=cls.UNSUPPORTED,
            partially_supported_columns=cls.PARTIALLY_SUPPORTED,
            fully_supported_columns=cls.FULLY_SUPPORTED,
        )
