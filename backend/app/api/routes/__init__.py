"""API Routes Package."""
from backend.app.api.routes import ingestion, inventory, normalization, waste_detection

__all__ = ["ingestion", "inventory", "normalization", "waste_detection"]
