"""
CloudSage Inventory Adapter Registry.
Central registry for cloud provider inventory adapters with auto-detection.
"""

import json
import os
from typing import Any, Dict, Optional, Type
from backend.app.core.enums import CloudProvider
from backend.app.inventory.adapters.aws import AWSInventoryAdapter
from backend.app.inventory.adapters.azure import AzureInventoryAdapter
from backend.app.inventory.adapters.gcp import GCPInventoryAdapter
from backend.app.inventory.base import BaseInventoryAdapter


class InventoryRegistry:
    """Registry maintaining active inventory discovery adapters."""

    _adapters: Dict[str, BaseInventoryAdapter] = {}

    @classmethod
    def initialize_defaults(cls) -> None:
        """Initializes default hyperscaler adapters."""
        cls._adapters = {
            CloudProvider.AWS.value: AWSInventoryAdapter(),
            CloudProvider.AZURE.value: AzureInventoryAdapter(),
            CloudProvider.GCP.value: GCPInventoryAdapter(),
        }

    @classmethod
    def register(cls, provider: str, adapter: BaseInventoryAdapter) -> None:
        """Registers a custom or extended inventory adapter."""
        cls._adapters[provider.upper().strip()] = adapter

    @classmethod
    def get_adapter(cls, provider: str) -> BaseInventoryAdapter:
        """Retrieves the inventory adapter for a provider."""
        if not cls._adapters:
            cls.initialize_defaults()

        prov_key = provider.upper().strip()
        if prov_key not in cls._adapters:
            raise ValueError(f"No inventory adapter registered for provider: {provider}")
        return cls._adapters[prov_key]

    @classmethod
    def detect_provider(cls, stream_or_path: Any) -> Optional[str]:
        """
        Heuristically inspects an inventory payload to detect cloud provider.
        Checks structure, keys, and resource ID patterns.
        """
        try:
            payload = None
            if isinstance(stream_or_path, str):
                if os.path.exists(stream_or_path):
                    with open(stream_or_path, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                else:
                    payload = json.loads(stream_or_path)
            elif hasattr(stream_or_path, "read"):
                content = stream_or_path.read()
                if hasattr(stream_or_path, "seek"):
                    stream_or_path.seek(0)
                if isinstance(content, bytes):
                    content = content.decode("utf-8")
                payload = json.loads(content)
            elif isinstance(stream_or_path, (list, dict)):
                payload = stream_or_path

            if not payload:
                return None

            text_sample = json.dumps(payload)[:2000]

            if "/subscriptions/" in text_sample or "Microsoft.Compute" in text_sample or "Microsoft.Storage" in text_sample:
                return "AZURE"
            if "//compute.googleapis.com" in text_sample or "googleapis.com" in text_sample or "assetType" in text_sample:
                return "GCP"
            if "arn:aws:" in text_sample or "ec2:instance" in text_sample or "AmazonEC2" in text_sample or "attached_volume_ids" in text_sample:
                return "AWS"

            return None
        except Exception:
            return None


# Initialize on import
InventoryRegistry.initialize_defaults()
