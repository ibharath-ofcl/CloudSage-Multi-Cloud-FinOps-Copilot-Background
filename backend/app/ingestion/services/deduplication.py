"""
CloudSage Ingestion Deduplication Service.
Computes deterministic idempotency fingerprints to prevent billing record duplication.
"""

import hashlib
from typing import Set
from sqlalchemy.orm import Session
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.base import RawBillingItem
from backend.app.models.billing import BillingRecord


class DeduplicationService:
    """Detects and filters duplicate billing line items across batch ingestion runs."""

    @staticmethod
    def generate_fingerprint(item: RawBillingItem) -> str:
        """
        Derives a deterministic SHA-256 fingerprint for a billing line item:
        provider : account_id : subscription_id : resource_id : start_time : cost
        """
        # Ensure UTC ISO string for timestamps
        start_iso = item.usage_start_time.isoformat()
        cost_str = str(item.unblended_cost)
        key_raw = f"{item.provider.value}:{item.billing_account_id}:{item.subscription_id}:{item.resource_id}:{start_iso}:{cost_str}"
        return hashlib.sha256(key_raw.encode("utf-8")).hexdigest()

    @classmethod
    def load_existing_fingerprints(
        cls,
        db: Session,
        provider: CloudProvider,
        account_id: str,
        start_time_min,
        start_time_max
    ) -> Set[str]:
        """
        Pre-loads existing record fingerprints within the target time window
        to perform in-memory set lookups (O(1)) instead of N individual database queries.
        """
        records = db.query(
            BillingRecord.provider,
            BillingRecord.billing_account_id,
            BillingRecord.subscription_id,
            BillingRecord.resource_id,
            BillingRecord.usage_start_time,
            BillingRecord.unblended_cost,
            BillingRecord.raw_metadata,
        ).filter(
            BillingRecord.provider == provider.value,
            BillingRecord.billing_account_id == account_id,
            BillingRecord.usage_start_time >= start_time_min,
            BillingRecord.usage_start_time <= start_time_max,
        ).all()

        existing: Set[str] = set()
        for r in records:
            # Check if fingerprint is in raw_metadata
            if r.raw_metadata and "_fingerprint" in r.raw_metadata:
                existing.add(r.raw_metadata["_fingerprint"])
            else:
                # Derive signature
                sig = f"{r.provider}:{r.billing_account_id}:{r.subscription_id}:{r.resource_id}:{r.usage_start_time.isoformat()}:{r.unblended_cost}"
                existing.add(hashlib.sha256(sig.encode("utf-8")).hexdigest())

        return existing
