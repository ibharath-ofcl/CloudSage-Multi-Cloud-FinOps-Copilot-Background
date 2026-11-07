"""
CloudSage Inventory Adapters Package.
Hyperscaler adapters for AWS, Azure, and GCP resource discovery.
"""

from backend.app.inventory.adapters.aws import AWSInventoryAdapter
from backend.app.inventory.adapters.azure import AzureInventoryAdapter
from backend.app.inventory.adapters.gcp import GCPInventoryAdapter

__all__ = [
    "AWSInventoryAdapter",
    "AzureInventoryAdapter",
    "GCPInventoryAdapter",
]
