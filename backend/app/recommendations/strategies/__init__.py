"""
CloudSage Recommendation Strategies Package.
Exports all 8 canonical multi-cloud optimization strategies and helper to register them.
"""

from backend.app.recommendations.registry import RecommendationRegistry
from backend.app.recommendations.strategies.anomaly_investigation import AnomalyInvestigationStrategy
from backend.app.recommendations.strategies.compute_rightsizing import ComputeRightsizingStrategy
from backend.app.recommendations.strategies.database_optimization import DatabaseOptimizationStrategy
from backend.app.recommendations.strategies.environment_scheduling import EnvironmentSchedulingStrategy
from backend.app.recommendations.strategies.idle_compute import IdleComputeStrategy
from backend.app.recommendations.strategies.network_optimization import NetworkOptimizationStrategy
from backend.app.recommendations.strategies.pricing_usage import PricingUsageStrategy
from backend.app.recommendations.strategies.storage_optimization import StorageOptimizationStrategy


def register_all_strategies() -> None:
    """Registers all 8 canonical optimization strategies in the central registry."""
    strategies = [
        IdleComputeStrategy(),
        ComputeRightsizingStrategy(),
        StorageOptimizationStrategy(),
        DatabaseOptimizationStrategy(),
        NetworkOptimizationStrategy(),
        AnomalyInvestigationStrategy(),
        PricingUsageStrategy(),
        EnvironmentSchedulingStrategy(),
    ]
    for s in strategies:
        RecommendationRegistry.register(s)


__all__ = [
    "IdleComputeStrategy",
    "ComputeRightsizingStrategy",
    "StorageOptimizationStrategy",
    "DatabaseOptimizationStrategy",
    "NetworkOptimizationStrategy",
    "AnomalyInvestigationStrategy",
    "PricingUsageStrategy",
    "EnvironmentSchedulingStrategy",
    "register_all_strategies",
]
