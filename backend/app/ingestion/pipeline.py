"""
CloudSage Ingestion Pipeline.
Executes the end-to-end multi-cloud billing ingestion workflow with partial success tolerance.
"""

from datetime import datetime, timezone
from decimal import Decimal
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union
import uuid
from sqlalchemy.orm import Session
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.base import BaseIngestionAdapter, IngestionResult, RawBillingItem
from backend.app.ingestion.normalizer import UnifiedNormalizer
from backend.app.ingestion.registry import IngestionRegistry
from backend.app.ingestion.services.deduplication import DeduplicationService
from backend.app.ingestion.services.ingestion_tracker import IngestionTracker
from backend.app.ingestion.validators import IngestionValidator
from backend.app.models.billing import BillingRecord
from backend.app.models.resource import CloudResource


class IngestionPipeline:
    """Orchestrates parsing, validation, normalization, deduplication, and persistence."""

    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        stream_or_path: Any,
        source_name: str,
        provider: Optional[CloudProvider] = None,
        checksum: Optional[str] = None,
        batch_size: int = 500
    ) -> IngestionResult:
        """
        Executes the 11-step ingestion pipeline with partial success support.
        """
        start_time = time.time()
        batch_id = uuid.uuid4()

        # Step 2 & 3: Select Adapter
        if provider:
            adapter = IngestionRegistry.get_adapter(provider)
        else:
            # Auto-detect from filename or peek sample
            adapter = IngestionRegistry.get_adapter(CloudProvider.AWS)

        actual_provider = adapter.provider

        # Step 10: Initialize Ingestion Run
        run = IngestionTracker.start_run(
            db=self.db,
            provider=actual_provider,
            source_filename=source_name,
            checksum=checksum,
        )

        total_records = 0
        ingested_records = 0
        duplicate_records = 0
        failed_records = 0
        total_cost = Decimal("0.0000")
        errors: List[Dict[str, Any]] = []

        seen_fingerprints = set()
        pending_billing_records: List[BillingRecord] = []
        pending_resources: Dict[str, CloudResource] = {}

        try:
            # Step 4: Parse Raw Records
            for raw_item in adapter.parse_stream(stream_or_path):
                total_records += 1

                # Step 5: Validate Required Fields
                val_ok, val_err = IngestionValidator.validate_timestamps(
                    raw_item.usage_start_time, raw_item.usage_end_time
                )
                if not val_ok:
                    failed_records += 1
                    errors.append({"line": total_records, "error": val_err, "resource_id": raw_item.resource_id})
                    continue

                cost_ok, cost_err = IngestionValidator.validate_financial_cost(raw_item.unblended_cost)
                if not cost_ok:
                    failed_records += 1
                    errors.append({"line": total_records, "error": cost_err, "resource_id": raw_item.resource_id})
                    continue

                # Step 8: Deduplication / Idempotency Check
                fingerprint = DeduplicationService.generate_fingerprint(raw_item)
                if fingerprint in seen_fingerprints:
                    duplicate_records += 1
                    continue

                # Check against database
                existing_in_db = (
                    self.db.query(BillingRecord.record_id)
                    .filter(
                        BillingRecord.provider == raw_item.provider.value,
                        BillingRecord.billing_account_id == raw_item.billing_account_id,
                        BillingRecord.resource_id == raw_item.resource_id,
                        BillingRecord.usage_start_time == raw_item.usage_start_time,
                        BillingRecord.unblended_cost == raw_item.unblended_cost,
                    )
                    .first()
                )
                if existing_in_db:
                    duplicate_records += 1
                    seen_fingerprints.add(fingerprint)
                    continue

                seen_fingerprints.add(fingerprint)

                # Step 6 & 7: Normalize & Validate with Pydantic
                try:
                    canonical_schema = UnifiedNormalizer.to_canonical_schema(raw_item)
                except Exception as ex:
                    failed_records += 1
                    errors.append({"line": total_records, "error": f"Schema normalization failure: {str(ex)}", "resource_id": raw_item.resource_id})
                    continue

                # Step 9: Prepare DB entity
                meta = dict(canonical_schema.raw_metadata or {})
                meta["_fingerprint"] = fingerprint

                db_record = BillingRecord(
                    provider=canonical_schema.provider.value,
                    billing_account_id=canonical_schema.billing_account_id,
                    subscription_id=canonical_schema.subscription_id,
                    resource_id=canonical_schema.resource_id,
                    resource_name=canonical_schema.resource_name,
                    service_category=canonical_schema.service_category.value,
                    service_name=canonical_schema.service_name,
                    region=canonical_schema.region,
                    zone=canonical_schema.zone,
                    usage_start_time=canonical_schema.usage_start_time,
                    usage_end_time=canonical_schema.usage_end_time,
                    usage_quantity=canonical_schema.usage_quantity,
                    usage_unit=canonical_schema.usage_unit,
                    unblended_cost=canonical_schema.unblended_cost,
                    blended_cost=canonical_schema.blended_cost,
                    list_cost=canonical_schema.list_cost,
                    pricing_model=canonical_schema.pricing_model.value,
                    currency=canonical_schema.currency,
                    tags=canonical_schema.tags,
                    raw_metadata=meta,
                )
                pending_billing_records.append(db_record)
                total_cost += canonical_schema.unblended_cost
                ingested_records += 1

                # Update / register CloudResource
                core_meta = UnifiedNormalizer.extract_core_metadata(canonical_schema.tags)
                res_id = canonical_schema.resource_id
                if res_id not in pending_resources:
                    pending_resources[res_id] = CloudResource(
                        resource_id=res_id,
                        provider=canonical_schema.provider.value,
                        account_id=canonical_schema.subscription_id,
                        resource_name=canonical_schema.resource_name,
                        service_category=canonical_schema.service_category.value,
                        service_name=canonical_schema.service_name,
                        resource_type=f"{canonical_schema.provider.value.lower()}:{canonical_schema.service_name.lower()}",
                        region=canonical_schema.region,
                        status="active",
                        tags=canonical_schema.tags,
                        owner=core_meta["owner"],
                        environment=core_meta["environment"] or "unknown",
                        cost_center=core_meta["cost_center"],
                        monthly_cost=canonical_schema.unblended_cost,
                        first_discovered_at=canonical_schema.usage_start_time,
                        last_seen_at=canonical_schema.usage_end_time,
                    )
                else:
                    pending_resources[res_id].monthly_cost += canonical_schema.unblended_cost

                # Batch Commit
                if len(pending_billing_records) >= batch_size:
                    self._flush_batch(pending_billing_records, pending_resources)
                    pending_billing_records.clear()
                    pending_resources.clear()

            # Final flush
            if pending_billing_records or pending_resources:
                self._flush_batch(pending_billing_records, pending_resources)
                pending_billing_records.clear()
                pending_resources.clear()

            # Determine final status
            if failed_records == 0:
                final_status = "COMPLETED"
            elif ingested_records > 0:
                final_status = "PARTIAL_SUCCESS"
            else:
                final_status = "FAILED"

        except Exception as ex:
            final_status = "FAILED"
            errors.append({"line": total_records, "error": f"Fatal ingestion exception: {str(ex)}"})

        elapsed_ms = (time.time() - start_time) * 1000.0

        # Step 10: Update Ingestion Run Tracking
        IngestionTracker.complete_run(
            db=self.db,
            run=run,
            status=final_status,
            total_records=total_records,
            ingested_records=ingested_records,
            duplicate_records=duplicate_records,
            failed_records=failed_records,
            total_cost=total_cost,
            error_summary=errors[:100],  # store top 100 errors for brevity
        )

        return IngestionResult(
            batch_id=batch_id,
            provider=actual_provider,
            source_name=source_name,
            total_records=total_records,
            ingested_records=ingested_records,
            skipped_duplicates=duplicate_records,
            failed_records=failed_records,
            total_cost_usd=total_cost,
            duration_ms=elapsed_ms,
            checksum=checksum or "",
            errors=[f"Line {e.get('line')}: {e.get('error')}" for e in errors],
        )

    def _flush_batch(self, billing_records: List[BillingRecord], resources: Dict[str, CloudResource]):
        """Persists a batch of billing records and merges cloud resources."""
        self.db.add_all(billing_records)
        for res_id, res in resources.items():
            existing = self.db.query(CloudResource).filter(CloudResource.resource_id == res_id).first()
            if existing:
                existing.last_seen_at = res.last_seen_at
                existing.monthly_cost += res.monthly_cost
                if res.tags:
                    existing.tags = {**existing.tags, **res.tags}
            else:
                self.db.add(res)
        self.db.commit()
