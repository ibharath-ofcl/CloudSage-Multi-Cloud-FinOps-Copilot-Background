"""
CloudSage Recommendation Engine Internal Data Models.
Dataclasses for candidate proposals, evidence links, strategy execution metrics, and scoring breakdowns.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from backend.app.core.enums import (
    CloudProvider,
    ImplementationEffort,
    Priority,
    RecommendationAction,
    RecommendationStatus,
    RiskLevel,
    ServiceCategory,
)


@dataclass
class EvidenceLink:
    """Internal representation of a supporting evidence artifact."""
    evidence_type: str
    description: str
    confidence_score: Decimal = Decimal("1.0000")
    waste_detection_id: Optional[UUID] = None
    anomaly_id: Optional[UUID] = None
    resource_id: Optional[str] = None
    telemetry_data: Dict[str, Any] = field(default_factory=dict)
    billing_record_ids: List[str] = field(default_factory=list)


@dataclass
class ScoringBreakdown:
    """Breakdown of multi-factor prioritization and risk components."""
    savings_score: Decimal
    confidence_score: Decimal
    effort_score: Decimal
    risk_score: Decimal
    urgency_score: Decimal
    composite_priority_score: Decimal
    priority_tier: Priority
    risk_level: RiskLevel
    effort_level: ImplementationEffort
    factors_explanation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecommendationCandidate:
    """
    Unpersisted optimization candidate produced by a strategy.
    Contains financial calculations, multi-factor scoring, guidance, and evidence links.
    """
    provider: CloudProvider
    action_type: RecommendationAction
    title: str
    description: str
    remediation_guide: str
    estimated_monthly_savings: Decimal
    estimated_annual_savings: Decimal
    current_monthly_cost: Decimal
    projected_monthly_cost: Decimal
    strategy_id: str
    strategy_version: str = "1.0"
    resource_id: Optional[str] = None
    account_id: Optional[str] = None
    region: Optional[str] = None
    service_name: Optional[str] = None
    service_category: Optional[ServiceCategory] = None
    resource_name: Optional[str] = None
    priority: Priority = Priority.P2
    priority_score: Decimal = Decimal("0.5000")
    risk_level: RiskLevel = RiskLevel.LOW
    risk_score: Decimal = Decimal("0.2000")
    confidence_score: Decimal = Decimal("1.0000")
    implementation_effort: ImplementationEffort = ImplementationEffort.LOW
    status: RecommendationStatus = RecommendationStatus.PROPOSED
    currency: str = "USD"
    waste_detection_id: Optional[UUID] = None
    anomaly_id: Optional[UUID] = None
    recommendation_key: Optional[str] = None
    savings_calculation: Dict[str, Any] = field(default_factory=dict)
    implementation_guidance: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    evidence_summary: Dict[str, Any] = field(default_factory=dict)
    evidence_items: List[EvidenceLink] = field(default_factory=list)
    tags: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StrategyResult:
    """Telemetry and execution metrics for a strategy run."""
    strategy_id: str
    candidates_generated: int = 0
    records_evaluated: int = 0
    execution_time_ms: Decimal = Decimal("0.00")
    status: str = "SUCCESS"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
