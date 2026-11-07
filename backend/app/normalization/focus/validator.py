"""
CloudSage FOCUS 1.0 Compliance Validator.
Validates records against official FinOps FOCUS 1.0 specification requirements.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List
from backend.app.normalization.focus.models import (
    Focus10Record,
    FocusChargeCategory,
    FocusPricingCategory,
    FocusServiceCategory,
)
from backend.app.schemas.normalization import (
    FocusFieldValidationDetail,
    FocusValidationResult,
)


class Focus10Validator:
    """Validator evaluating record conformance against FOCUS 1.0 rules."""

    MANDATORY_COLUMNS = [
        "BillingAccountId",
        "BillingCurrency",
        "ChargeCategory",
        "ChargePeriodStart",
        "ChargePeriodEnd",
        "BilledCost",
        "EffectiveCost",
        "PricingCategory",
        "ProviderName",
        "ServiceCategory",
        "ServiceName",
    ]

    CONDITIONAL_COLUMNS = [
        "ConsumedQuantity",
        "ConsumedUnit",
        "ResourceId",
        "ResourceType",
        "RegionId",
        "SubAccountId",
    ]

    RECOMMENDED_COLUMNS = [
        "ListCost",
        "BillingAccountName",
        "ResourceName",
        "SubAccountName",
        "Tags",
    ]

    @classmethod
    def validate_record(cls, data: Dict[str, Any]) -> FocusValidationResult:
        """
        Evaluates a raw dictionary or serialized record against FOCUS 1.0 specification.
        """
        details: List[FocusFieldValidationDetail] = []
        mandatory_passed = 0
        mandatory_failed = 0
        conditional_passed = 0
        recommended_passed = 0

        # 1. Validate Mandatory Columns
        for col in cls.MANDATORY_COLUMNS:
            val = data.get(col)
            val_present = val is not None and str(val).strip() != ""
            data_type_valid = True
            enum_valid = True
            msg = None

            if not val_present:
                mandatory_failed += 1
                msg = f"Mandatory column '{col}' is missing or empty"
            else:
                # Type & enum checks
                if "Cost" in col:
                    try:
                        dec = Decimal(str(val))
                        if dec < 0:
                            data_type_valid = False
                            msg = f"Monetary column '{col}' cannot be negative"
                    except Exception:
                        data_type_valid = False
                        msg = f"Monetary column '{col}' is not a valid Decimal"

                if "Period" in col:
                    if not isinstance(val, (datetime, str)):
                        data_type_valid = False
                        msg = f"DateTime column '{col}' is not valid"

                if col == "ChargeCategory":
                    enum_valid = any(
                        str(val).lower() == e.value.lower() for e in FocusChargeCategory
                    )
                    if not enum_valid:
                        msg = f"Invalid ChargeCategory: {val}"

                if col == "PricingCategory":
                    enum_valid = any(
                        str(val).lower() == e.value.lower() for e in FocusPricingCategory
                    )
                    if not enum_valid:
                        msg = f"Invalid PricingCategory: {val}"

                if col == "ServiceCategory":
                    enum_valid = any(
                        str(val).lower() == e.value.lower() for e in FocusServiceCategory
                    )
                    if not enum_valid:
                        msg = f"Invalid ServiceCategory: {val}"

                if val_present and data_type_valid and enum_valid:
                    mandatory_passed += 1
                else:
                    mandatory_failed += 1

            details.append(
                FocusFieldValidationDetail(
                    column_name=col,
                    is_valid=val_present and data_type_valid and enum_valid,
                    value_present=val_present,
                    requirement_level="Mandatory",
                    data_type_valid=data_type_valid,
                    enum_valid=enum_valid,
                    message=msg,
                )
            )

        # 2. Validate Conditional Columns
        for col in cls.CONDITIONAL_COLUMNS:
            val = data.get(col)
            val_present = val is not None and str(val).strip() != ""
            if val_present:
                conditional_passed += 1
            details.append(
                FocusFieldValidationDetail(
                    column_name=col,
                    is_valid=True,
                    value_present=val_present,
                    requirement_level="Conditional",
                    data_type_valid=True,
                    enum_valid=True,
                    message=None if val_present else f"Conditional column '{col}' omitted",
                )
            )

        # 3. Validate Recommended Columns
        for col in cls.RECOMMENDED_COLUMNS:
            val = data.get(col)
            val_present = val is not None and (len(val) > 0 if isinstance(val, dict) else str(val).strip() != "")
            if val_present:
                recommended_passed += 1
            details.append(
                FocusFieldValidationDetail(
                    column_name=col,
                    is_valid=True,
                    value_present=val_present,
                    requirement_level="Recommended",
                    data_type_valid=True,
                    enum_valid=True,
                    message=None,
                )
            )

        total_cols = len(cls.MANDATORY_COLUMNS) + len(cls.CONDITIONAL_COLUMNS) + len(cls.RECOMMENDED_COLUMNS)
        is_compliant = mandatory_failed == 0

        # Score computation:
        # Mandatory: 70% weight
        # Conditional: 20% weight
        # Recommended: 10% weight
        mand_score = (mandatory_passed / len(cls.MANDATORY_COLUMNS)) * 70.0
        cond_score = (conditional_passed / len(cls.CONDITIONAL_COLUMNS)) * 20.0
        rec_score = (recommended_passed / len(cls.RECOMMENDED_COLUMNS)) * 10.0
        total_score = Decimal(str(round(mand_score + cond_score + rec_score, 2)))

        return FocusValidationResult(
            is_compliant=is_compliant,
            total_columns_evaluated=total_cols,
            mandatory_columns_passed=mandatory_passed,
            mandatory_columns_failed=mandatory_failed,
            conditional_columns_passed=conditional_passed,
            recommended_columns_passed=recommended_passed,
            field_details=details,
            compliance_score=total_score,
        )
