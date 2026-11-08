"""API Routes Package."""
from backend.app.api.routes import (
    alerts,
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
    "alerts",
    "anomaly_detection",
    "copilot",
    "dashboard",
    "ingestion",
    "inventory",
    "normalization",
    "recommendations",
    "waste_detection",
]
