"""CloudSage Provider Ingestion Adapters Package."""
from backend.app.ingestion.adapters.aws.adapter import AWSCurAdapter
from backend.app.ingestion.adapters.azure.adapter import AzureCostAdapter
from backend.app.ingestion.adapters.gcp.adapter import GCPApiAdapter

__all__ = ["AWSCurAdapter", "AzureCostAdapter", "GCPApiAdapter"]
