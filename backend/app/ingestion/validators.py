"""
CloudSage Ingestion Validators.
Pre-flight checks and record validation rules ensuring financial accuracy and schema compliance.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from backend.app.core.enums import CloudProvider


class IngestionValidator:
    """Validates raw and normalized billing items prior to database persistence."""

    @staticmethod
    def validate_raw_fields(raw_record: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, List[str]]:
        """Verifies that all mandatory provider fields are present and non-empty."""
        missing = [f for f in required_fields if f not in raw_record or raw_record[f] is None or str(raw_record[f]).strip() == ""]
        return len(missing) == 0, missing

    @staticmethod
    def validate_timestamps(start_time: datetime, end_time: datetime) -> Tuple[bool, Optional[str]]:
        """Verifies usage timestamps are valid and chronological."""
        if not start_time:
            return False, "usage_start_time is required"
        if not end_time:
            return False, "usage_end_time is required"
        if end_time < start_time:
            return False, f"usage_end_time ({end_time}) cannot precede usage_start_time ({start_time})"
        return True, None

    @staticmethod
    def validate_financial_cost(cost: Decimal) -> Tuple[bool, Optional[str]]:
        """
        Validates cost decimal.
        Note: Negative costs are permissible only as legitimate credits, discounts, or refunds.
        """
        if not isinstance(cost, Decimal):
            return False, f"Cost must be of type Decimal, got {type(cost).__name__}"
        if cost.is_nan() or cost.is_infinite():
            return False, "Cost cannot be NaN or Infinite"
        return True, None

    @staticmethod
    def validate_resource_identifier(resource_id: str, provider: CloudProvider) -> Tuple[bool, Optional[str]]:
        """Checks for valid resource identifier formatting."""
        if not resource_id or not resource_id.strip():
            return False, "resource_id cannot be empty"
        if len(resource_id) > 512:
            return False, "resource_id exceeds maximum permitted length of 512 characters"
        return True, None
