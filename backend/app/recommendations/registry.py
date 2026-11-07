"""
CloudSage Recommendation Strategy Registry.
Manages registration, discovery, and lifecycle of optimization strategies.
"""

from typing import Dict, List, Optional
from backend.app.recommendations.base import BaseRecommendationStrategy


class RecommendationRegistry:
    """Singleton registry holding active recommendation strategies."""
    _strategies: Dict[str, BaseRecommendationStrategy] = {}

    @classmethod
    def register(cls, strategy: BaseRecommendationStrategy) -> None:
        """Registers a new optimization strategy."""
        cls._strategies[strategy.strategy_id] = strategy

    @classmethod
    def get_strategy(cls, strategy_id: str) -> BaseRecommendationStrategy:
        """Retrieves a strategy by its unique identifier."""
        if strategy_id not in cls._strategies:
            raise KeyError(f"Recommendation strategy '{strategy_id}' not found in registry.")
        return cls._strategies[strategy_id]

    @classmethod
    def list_strategies(
        cls,
        category: Optional[str] = None,
    ) -> List[BaseRecommendationStrategy]:
        """Lists registered strategies, optionally filtered by category."""
        strategies = list(cls._strategies.values())
        if category:
            cat_upper = category.upper()
            strategies = [s for s in strategies if s.category.upper() == cat_upper]
        return strategies

    @classmethod
    def clear(cls) -> None:
        """Clears all registered strategies (primarily for testing)."""
        cls._strategies.clear()


def get_recommendation_registry() -> type[RecommendationRegistry]:
    """Returns the recommendation strategy registry."""
    return RecommendationRegistry
