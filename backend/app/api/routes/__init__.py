"""API Routes Package."""
from backend.app.api.routes import (
    anomaly_detection,
    copilot,
    dashboard,
    ingestion,
    inventory,
    normalization,
    recommendations,
    waste_detection,
)

__all__ = [
    "anomaly_detection",
    "copilot",
    "dashboard",
    "ingestion",
    "inventory",
    "normalization",
    "recommendations",
    "waste_detection",
]
