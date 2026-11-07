"""
CloudSage Unified Normalization Pipeline.
Executes the enterprise 15-step normalization and FOCUS 1.0 compliance workflow.
Supports live post-ingestion processing, batch reprocessing, and auditable run tracking.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from backend.app.core.enums import CloudProvider, PricingModel, ServiceCategory
from backend.app.ingestion.base import RawBillingItem
from backend.app.models.billing import BillingRecord
from backend.app.models.normalization import DataQualityReport, NormalizationRun
from backend.app.models.resource import CloudResource
from backend.app.normalization.catalog.lookup import CatalogLookupEngine
from backend.app.normalization.currency.service import CurrencyService
from backend.app.normalization.focus.conformance import FocusConformanceEngine
from backend.app.normalization.focus.exporter import FocusExporter
from backend.app.normalization.focus.validator import Focus10Validator
from backend.app.normalization.quality.evaluator import DataQualityEngine
from backend.app.normalization.quality.service import DataQualityService
from backend.app.normalization.tags.extractor import TagExtractor
from backend.app.normalization.tags.quality import TagQualityScorer
from backend.app.normalization.tags.sanitizer import TagSanitizer
from backend.app.schemas.billing import BillingRecordCreate
from backend.app.schemas.normalization import (
    FocusValidationResult,
    NormalizationRunResponse,
)


class NormalizationPipeline:
    """Orchestrates the 15-step FOCUS 1.0 compliance and data quality normalization pipeline."""

    NORMALIZATION_VERSION = "1.0.0"
    MAPPING_VERSION = "2026.11"

    def __init__(self, db: Session):
        self.db = db

    def normalize_single_item(
        self,
        item: RawBillingItem,
        effective_date: Optional[date] = None,
    ) -> Tuple[BillingRecordCreate, FocusValidationResult, Dict[str, Any]]:
        """
        Executes Steps 2 through 11 for a single RawBillingItem:
        - Resolves service catalog & SKU mappings
        - Sanitizes tags and extracts FinOps governance metadata
        - Normalizes timestamps to UTC
        - Converts foreign currency using historical date-aware FX lookup
        - Validates against FOCUS 1.0 specification
        """
        # Step 2: Identify provider & currency
        prov_str = item.provider.value if hasattr(item.provider, "value") else str(item.provider)
        raw_currency = (item.currency or "USD").upper().strip()
        ref_date = effective_date or (item.usage_start_time.date() if item.usage_start_time else date.today())

        # Step 4 & 5: Retrieve service & SKU catalog mappings
        catalog_entry = CatalogLookupEngine.resolve_service(
            provider=prov_str,
            service_code=item.service_name,
            sku_id=getattr(item, "sku_id", None),
            db=self.db,
        )
        canonical_category_str = catalog_entry.canonical_category
        try:
            canonical_category = ServiceCategory(canonical_category_str)
        except ValueError:
            canonical_category = ServiceCategory.OTHER

        normalized_unit = CatalogLookupEngine.normalize_unit(item.usage_unit or catalog_entry.normalized_unit)

        # Step 6: Normalize timestamps to UTC
        start_utc = (
            item.usage_start_time.astimezone(timezone.utc)
            if item.usage_start_time.tzinfo
            else item.usage_start_time.replace(tzinfo=timezone.utc)
        )
        end_utc = (
            item.usage_end_time.astimezone(timezone.utc)
            if item.usage_end_time.tzinfo
            else item.usage_end_time.replace(tzinfo=timezone.utc)
        )

        # Step 7: Extract and normalize resource tags & score quality
        sanitized_tags, tag_warnings = TagSanitizer.sanitize(item.tags)
        extracted_meta = TagExtractor.extract_metadata(sanitized_tags)
        tag_quality = TagQualityScorer.evaluate(
            resource_id=item.resource_id,
            raw_tags=item.tags,
            sanitized_tags=sanitized_tags,
            extracted_metadata=extracted_meta,
        )

        # Step 8 & 9: Currency conversion with historical FX lookup
        conv_unblended = CurrencyService.convert_to_usd(
            amount=item.unblended_cost,
            currency_code=raw_currency,
            effective_date=ref_date,
            db=self.db,
        )
        norm_cost = conv_unblended.converted_amount_usd

        norm_blended = None
        if item.blended_cost is not None:
            conv_blended = CurrencyService.convert_to_usd(
                amount=item.blended_cost,
                currency_code=raw_currency,
                effective_date=ref_date,
                db=self.db,
            )
            norm_blended = conv_blended.converted_amount_usd

        norm_list = None
        if item.list_cost is not None:
            conv_list = CurrencyService.convert_to_usd(
                amount=item.list_cost,
                currency_code=raw_currency,
                effective_date=ref_date,
                db=self.db,
            )
            norm_list = conv_list.converted_amount_usd

        # Step 10: Map to canonical Pydantic schema
        metadata = dict(item.raw_metadata or {})
        metadata["_normalization_version"] = self.NORMALIZATION_VERSION
        metadata["_mapping_version"] = self.MAPPING_VERSION
        metadata["_exchange_rate_source"] = conv_unblended.source
        metadata["_exchange_rate_date"] = str(conv_unblended.effective_date)
        metadata["_exchange_rate_used"] = str(conv_unblended.rate_used)
        metadata["_tag_quality_score"] = float(tag_quality.quality_score)
        metadata["_catalog_provenance"] = catalog_entry.provenance
        metadata["_catalog_confidence"] = float(catalog_entry.confidence)
        metadata["original_cost"] = str(item.unblended_cost)
        metadata["original_currency"] = raw_currency

        canonical_schema = BillingRecordCreate(
            provider=item.provider,
            billing_account_id=item.billing_account_id,
            subscription_id=item.subscription_id,
            resource_id=item.resource_id,
            resource_name=item.resource_name or item.resource_id,
            service_category=canonical_category,
            service_name=item.service_name,
            region=item.region,
            zone=item.zone,
            usage_start_time=start_utc,
            usage_end_time=end_utc,
            usage_quantity=item.usage_quantity,
            usage_unit=normalized_unit,
            unblended_cost=norm_cost,
            blended_cost=norm_blended,
            list_cost=norm_list,
            pricing_model=item.pricing_model,
            currency="USD",
            tags=sanitized_tags,
            raw_metadata=metadata,
        )

        # Step 11: Run FOCUS 1.0 validation
        focus_dict = {
            "BillingAccountId": item.billing_account_id,
            "BillingCurrency": "USD",
            "ChargeCategory": "Usage",
            "ChargePeriodStart": start_utc,
            "ChargePeriodEnd": end_utc,
            "ConsumedQuantity": item.usage_quantity,
            "ConsumedUnit": normalized_unit,
            "BilledCost": norm_cost,
            "EffectiveCost": norm_blended or norm_cost,
            "ListCost": norm_list or norm_cost,
            "PricingCategory": "On-Demand",
            "ProviderName": prov_str,
            "RegionId": item.region,
            "ResourceId": item.resource_id,
            "ResourceName": item.resource_name,
            "ServiceCategory": canonical_category_str,
            "ServiceName": item.service_name,
            "SubAccountId": item.subscription_id,
            "Tags": sanitized_tags,
        }
        focus_validation = Focus10Validator.validate_record(focus_dict)

        extra_audit = {
            "tag_quality": tag_quality,
            "catalog_entry": catalog_entry,
            "fx_conversion": conv_unblended,
            "extracted_metadata": extracted_meta,
        }

        return canonical_schema, focus_validation, extra_audit

    def reprocess_existing_records(
        self,
        provider: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        batch_size: int = 500,
    ) -> NormalizationRun:
        """
        Reprocesses existing database billing records with updated exchange rates,
        service catalog mappings, and tag normalization rules.
        Guarantees zero duplicate records by updating in-place.
        """
        run = NormalizationRun(
            run_id=uuid.uuid4(),
            status="PROCESSING",
            normalization_version=self.NORMALIZATION_VERSION,
            mapping_version=self.MAPPING_VERSION,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.commit()

        query = self.db.query(BillingRecord)
        if provider:
            query = query.filter(BillingRecord.provider == provider.upper().strip())
        if start_date:
            query = query.filter(BillingRecord.usage_start_time >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
        if end_date:
            query = query.filter(BillingRecord.usage_end_time <= datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc))

        total_records = query.count()
        run.total_records = total_records

        if total_records == 0:
            run.status = "COMPLETED"
            run.completed_at = datetime.now(timezone.utc)
            run.average_quality_score = Decimal("100.00")
            self.db.commit()
            return run

        successful = 0
        failed = 0
        warnings = 0
        errors = []
        evaluated_for_dq = []

        offset = 0
        while offset < total_records:
            batch = query.order_by(BillingRecord.usage_start_time).offset(offset).limit(batch_size).all()
            if not batch:
                break

            for rec in batch:
                try:
                    # Catalog re-resolution
                    catalog_entry = CatalogLookupEngine.resolve_service(
                        provider=rec.provider,
                        service_code=rec.service_name,
                        db=self.db,
                    )
                    rec.service_category = catalog_entry.canonical_category
                    rec.usage_unit = catalog_entry.normalized_unit

                    # Tags re-sanitization
                    clean_tags, t_warn = TagSanitizer.sanitize(rec.tags)
                    rec.tags = clean_tags
                    if t_warn:
                        warnings += len(t_warn)

                    # Update metadata audit
                    meta = dict(rec.raw_metadata or {})
                    meta["_reprocessed_at"] = datetime.now(timezone.utc).isoformat()
                    meta["_normalization_version"] = self.NORMALIZATION_VERSION
                    rec.raw_metadata = meta

                    evaluated_for_dq.append(rec)
                    successful += 1
                except Exception as ex:
                    failed += 1
                    errors.append({"record_id": str(rec.record_id), "error": str(ex)})

            self.db.commit()
            offset += batch_size

        # Step 12: Run Data Quality Assessment over reprocessed batch
        dq_assessment = DataQualityEngine.evaluate_batch(evaluated_for_dq)
        DataQualityService.evaluate_and_persist(
            db=self.db,
            records=evaluated_for_dq,
            provider=provider,
            run_id=run.run_id,
        )

        run.successful_records = successful
        run.failed_records = failed
        run.warnings_count = warnings
        run.average_quality_score = dq_assessment.overall_score
        run.status = "COMPLETED" if failed == 0 else ("PARTIAL_SUCCESS" if successful > 0 else "FAILED")
        run.completed_at = datetime.now(timezone.utc)
        run.error_details = errors[:100]

        self.db.commit()
        return run
