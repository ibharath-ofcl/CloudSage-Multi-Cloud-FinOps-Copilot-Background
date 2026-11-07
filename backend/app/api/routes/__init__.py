"""API Routes Package."""
from backend.app.api.routes import (
    anomaly_detection,
    ingestion,
    inventory,
    normalization,
    waste_detection,
)

__all__ = ["anomaly_detection", "ingestion", "inventory", "normalization", "waste_detection"]
