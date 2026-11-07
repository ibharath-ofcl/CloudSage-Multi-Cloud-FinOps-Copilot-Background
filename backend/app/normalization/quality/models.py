"""
CloudSage Data Quality Models.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class QualitySeverity(str, Enum):
    """Data Quality Finding Severity Levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


@dataclass
class QualityFinding:
    """Individual data quality rule violation finding."""
    rule_id: str
    rule_name: str
    severity: QualitySeverity
    field_name: Optional[str]
    record_identifier: Optional[str]
    message: str
    suggested_remediation: Optional[str] = None


@dataclass
class QualityAssessmentResult:
    """Quality evaluation result for a batch of records."""
    total_records: int
    overall_score: Decimal
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    informational_count: int
    findings: List[QualityFinding]
    provider_scores: Dict[str, Decimal]
