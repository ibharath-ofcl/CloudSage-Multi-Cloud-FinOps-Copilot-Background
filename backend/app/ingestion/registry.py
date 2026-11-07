"""
CloudSage Ingestion Adapter Registry.
Provides dynamic adapter discovery, registration, and content-based auto-detection.
"""

from typing import Dict, Optional, Type
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.adapters.aws.adapter import AWSCurAdapter
from backend.app.ingestion.adapters.azure.adapter import AzureCostAdapter
from backend.app.ingestion.adapters.gcp.adapter import GCPApiAdapter
from backend.app.ingestion.base import BaseIngestionAdapter
from backend.app.ingestion.exceptions import AdapterNotFoundError


class IngestionRegistry:
    """Registry managing available multi-cloud billing adapters."""

    _adapters: Dict[CloudProvider, BaseIngestionAdapter] = {}

    @classmethod
    def register(cls, provider: CloudProvider, adapter: BaseIngestionAdapter) -> None:
        """Registers a custom or provider adapter instance."""
        cls._adapters[provider] = adapter

    @classmethod
    def get_adapter(cls, provider: CloudProvider) -> BaseIngestionAdapter:
        """Retrieves adapter registered for the given provider."""
        if provider not in cls._adapters:
            # Lazy initialize default providers
            if provider == CloudProvider.AWS:
                cls._adapters[CloudProvider.AWS] = AWSCurAdapter()
            elif provider == CloudProvider.AZURE:
                cls._adapters[CloudProvider.AZURE] = AzureCostAdapter()
            elif provider == CloudProvider.GCP:
                cls._adapters[CloudProvider.GCP] = GCPApiAdapter()
            else:
                raise AdapterNotFoundError(f"No adapter registered for provider: {provider.value}")
        return cls._adapters[provider]

    @classmethod
    def detect_adapter(cls, content_sample: str, filename: str = "") -> BaseIngestionAdapter:
        """Auto-detects the matching adapter based on file content signature or filename."""
        if AWSCurAdapter.can_handle(content_sample, filename):
            return cls.get_adapter(CloudProvider.AWS)
        if AzureCostAdapter.can_handle(content_sample, filename):
            return cls.get_adapter(CloudProvider.AZURE)
        if GCPApiAdapter.can_handle(content_sample, filename):
            return cls.get_adapter(CloudProvider.GCP)
        
        raise AdapterNotFoundError(f"Unable to auto-detect cloud provider adapter for file: {filename}")


# Pre-register default hyperscaler adapters
IngestionRegistry.register(CloudProvider.AWS, AWSCurAdapter())
IngestionRegistry.register(CloudProvider.AZURE, AzureCostAdapter())
IngestionRegistry.register(CloudProvider.GCP, GCPApiAdapter())
