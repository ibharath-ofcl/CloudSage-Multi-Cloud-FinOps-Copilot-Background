"""
CloudSage Base Recommendation Strategy Interface.
Abstract base class for all pluggable multi-cloud optimization strategies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.recommendations.models import RecommendationCandidate, StrategyResult


class BaseRecommendationStrategy(ABC):
    """
    Pluggable optimization heuristic strategy.
    Evaluates cloud resources, waste detections, and cost anomalies to produce advisory recommendations.
    """

    @property
    @abstractmethod
    def strategy_id(self) -> str:
        """Unique machine-readable strategy identifier."""
        pass

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Human-readable strategy name."""
        pass

    @property
    @abstractmethod
    def strategy_version(self) -> str:
        """Strategy logic version."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Optimization category (COMPUTE, STORAGE, DATABASE, NETWORK, ANOMALY, PRICING, SCHEDULING)."""
        pass

    @property
    def description(self) -> str:
        """Summary explanation of what this strategy optimizes."""
        return "Advisory FinOps optimization strategy."

    @abstractmethod
    def evaluate(
        self,
        db: Session,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[RecommendationCandidate]:
        """
        Executes optimization logic against database state.
        Returns a list of unpersisted RecommendationCandidate objects.
        """
        pass
