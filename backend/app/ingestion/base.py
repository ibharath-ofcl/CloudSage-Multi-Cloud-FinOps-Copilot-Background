"""
CloudSage Ingestion Base Framework.
Defines base interfaces, data structures, and idempotency mechanisms for multi-cloud ingestion.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
from typing import Any, Dict, Generator, Iterator, List, Optional
import uuid
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory


@dataclass
class RawBillingItem:
    """Standard intermediate representation emitted by provider ingestion adapters."""
    provider: CloudProvider
    billing_account_id: str
    subscription_id: str
    resource_id: str
    resource_name: Optional[str]
    service_category: ServiceCategory
    service_name: str
    region: str
    zone: Optional[str]
    usage_start_time: datetime
    usage_end_time: datetime
    usage_quantity: Decimal
    usage_unit: str
    unblended_cost: Decimal
    blended_cost: Optional[Decimal] = None
    list_cost: Optional[Decimal] = None
    pricing_model: PricingModel = PricingModel.ON_DEMAND
    currency: str = "USD"
    tags: Dict[str, Any] = field(default_factory=dict)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = ""

    def __post_init__(self):
        # Automatically generate SHA-256 idempotency key if not explicitly set
        if not self.idempotency_key:
            unique_signature = (
                f"{self.provider.value}:{self.billing_account_id}:{self.subscription_id}:"
                f"{self.resource_id}:{self.usage_start_time.isoformat()}:{self.unblended_cost}"
            )
            self.idempotency_key = hashlib.sha256(unique_signature.encode("utf-8")).hexdigest()


@dataclass
class IngestionResult:
    """Summary metrics of an executed ingestion batch."""
    batch_id: uuid.UUID
    provider: CloudProvider
    source_name: str
    total_records: int = 0
    ingested_records: int = 0
    skipped_duplicates: int = 0
    failed_records: int = 0
    total_cost_usd: Decimal = Decimal("0.0000")
    duration_ms: float = 0.0
    checksum: str = ""
    errors: List[str] = field(default_factory=list)


class BaseIngestionAdapter(ABC):
    """
    Abstract Base Class for Cloud Ingestion Adapters.
    Every cloud provider adapter (AWS, Azure, GCP, Synthetic) inherits from this.
    """

    def __init__(self, provider: CloudProvider):
        self.provider = provider

    @abstractmethod
    def parse_stream(self, stream_or_path: Any) -> Iterator[RawBillingItem]:
        """
        Parses raw input files/streams in chunks or lines, yielding RawBillingItem instances.
        Must be a generator to prevent Out-Of-Memory (OOM) on large billing datasets.
        """
        pass

    @staticmethod
    def calculate_file_checksum(file_path: str) -> str:
        """Calculates SHA-256 checksum of an incoming billing file for audit verification."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def sanitize_tag_key(key: str) -> str:
        """Sanitizes tag keys to clean, lowercase, alphanumeric FinOps format."""
        cleaned = key.strip().lower()
        # Strip common provider prefixes like 'tag:', 'resourceTags/user:', 'user:'
        for prefix in ["resourcetags/user:", "user:", "tag:", "labels/"]:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
        return cleaned.replace("-", "_").replace(" ", "_")

    @staticmethod
    def parse_decimal(value: Any, default: Decimal = Decimal("0.0000")) -> Decimal:
        """Safely parses monetary or numeric values to strict Decimal without float cast."""
        if value is None or value == "":
            return default
        try:
            return Decimal(str(value).strip())
        except Exception:
            return default
