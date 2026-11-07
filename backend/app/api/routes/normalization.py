"""
CloudSage Normalization and FOCUS 1.0 Compliance API Endpoints.
Provides REST endpoints for batch normalization, FOCUS conformance checks,
data quality evaluations, SKU catalog lookups, and FX rates.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_sync_db
from backend.app.models.billing import BillingRecord
from backend.app.models.normalization import (
    DataQualityReport,
    ExchangeRate,
    NormalizationRun,
    SkuCatalogMapping,
)
from backend.app.normalization.catalog.mappings import SYSTEM_CATALOG_MAPPINGS
from backend.app.normalization.currency.providers import STATIC_REFERENCE_RATES_TO_USD
from backend.app.normalization.focus.conformance import FocusConformanceEngine
from backend.app.normalization.focus.exporter import FocusExporter
from backend.app.normalization.focus.validator import Focus10Validator
from backend.app.normalization.pipeline import NormalizationPipeline
from backend.app.normalization.quality.evaluator import DataQualityEngine
from backend.app.normalization.quality.service import DataQualityService
from backend.app.normalization.tags.extractor import TagExtractor
from backend.app.normalization.tags.quality import TagQualityScorer
from backend.app.schemas.normalization import (
    DataQualityReportResponse,
    ExchangeRateResponse,
    FocusConformanceSummary,
    NormalizationRunRequest,
    NormalizationRunResponse,
    SkuCatalogLookupResponse,
    SkuCatalogMappingResponse,
    TagQualityAnalysisResult,
)

router = APIRouter(prefix="/normalization", tags=["FOCUS Normalization & Data Quality"])


@router.post("/run", response_model=NormalizationRunResponse, summary="Trigger Batch Normalization / Reprocessing")
def trigger_normalization_run(
    request: NormalizationRunRequest,
    db: Session = Depends(get_sync_db),
):
    """
    Executes the 15-step batch normalization or historical re-normalization pipeline.
    Reprocesses records in-place without generating duplicates.
    """
    pipeline = NormalizationPipeline(db=db)
    run = pipeline.reprocess_existing_records(
        provider=request.provider,
        start_date=request.start_date,
        end_date=request.end_date,
        batch_size=request.batch_size,
    )
    return run


@router.get("/runs", response_model=List[NormalizationRunResponse], summary="List Normalization Runs")
def list_normalization_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db),
):
    """Retrieves chronological execution history of normalization jobs."""
    runs = (
        db.query(NormalizationRun)
        .order_by(NormalizationRun.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return runs


@router.get("/runs/{run_id}", response_model=NormalizationRunResponse, summary="Get Specific Normalization Run")
def get_normalization_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_sync_db),
):
    """Retrieves detailed status and errors for a single normalization run."""
    run = db.query(NormalizationRun).filter(NormalizationRun.run_id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Normalization run '{run_id}' not found",
        )
    return run


@router.get("/quality-report", response_model=DataQualityReportResponse, summary="Get Latest Data Quality Assessment")
def get_data_quality_report(
    provider: Optional[str] = Query(None, description="Filter by cloud provider"),
    db: Session = Depends(get_sync_db),
):
    """
    Returns the latest data quality report. If none exists, runs an evaluation over active records.
    """
    latest = DataQualityService.get_latest_report(db, provider=provider)
    if latest:
        return latest

    # Evaluate current billing records on the fly
    records = db.query(BillingRecord).limit(1000).all()
    report = DataQualityService.evaluate_and_persist(db, records=records, provider=provider)
    return report


@router.get("/focus-validation", response_model=FocusConformanceSummary, summary="Get FOCUS 1.0 Conformance Assessment")
def get_focus_conformance(
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_sync_db),
):
    """
    Evaluates current billing records against FOCUS 1.0 specification and generates conformance summary.
    """
    records = db.query(BillingRecord).limit(limit).all()
    if not records:
        return FocusConformanceEngine.generate_summary([])

    results = []
    for rec in records:
        f_dict = FocusExporter.to_focus_dict(rec)
        results.append(Focus10Validator.validate_record(f_dict))

    return FocusConformanceEngine.generate_summary(results)


@router.get("/catalog", summary="List Catalog SKU Mappings")
def list_catalog_mappings(
    provider: Optional[str] = Query(None, description="AWS, AZURE, GCP"),
    db: Session = Depends(get_sync_db),
):
    """Returns static and database-backed catalog mappings."""
    db_mappings = db.query(SkuCatalogMapping).all()
    results = [
        {
            "provider": m.provider,
            "service_code": m.service_code,
            "sku_id": m.sku_id,
            "canonical_category": m.canonical_category,
            "service_family": m.service_family,
            "resource_type": m.resource_type,
            "normalized_unit": m.normalized_unit,
            "confidence": float(m.confidence),
            "provenance": m.provenance,
        }
        for m in db_mappings
    ]

    # Include system catalog entries
    for (p, s), entry in SYSTEM_CATALOG_MAPPINGS.items():
        if not provider or p.upper() == provider.upper():
            results.append({
                "provider": entry.provider,
                "service_code": entry.service_code,
                "sku_id": entry.sku_id,
                "canonical_category": entry.canonical_category,
                "service_family": entry.service_family,
                "resource_type": entry.resource_type,
                "normalized_unit": entry.normalized_unit,
                "confidence": float(entry.confidence),
                "provenance": entry.provenance,
            })

    return {"total": len(results), "mappings": results}


@router.get("/currency-rates", summary="List Active Currency Exchange Rates")
def list_currency_rates(
    db: Session = Depends(get_sync_db),
):
    """Returns static baseline and database registered exchange rates to USD."""
    db_rates = db.query(ExchangeRate).all()
    rates_dict = {k: float(v) for k, v in STATIC_REFERENCE_RATES_TO_USD.items()}
    for r in db_rates:
        rates_dict[r.currency_code] = float(r.rate_to_usd)

    return {
        "base_currency": "USD",
        "rates_to_usd": rates_dict,
        "total_currencies": len(rates_dict),
        "source": "ECB_AND_STATIC_FALLBACK",
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/tag-quality", response_model=List[TagQualityAnalysisResult], summary="Get Resource Tag Hygiene Breakdown")
def get_tag_quality_breakdown(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_sync_db),
):
    """Analyzes tag hygiene scores across stored billing resources."""
    records = db.query(BillingRecord).limit(limit).all()
    results = []
    seen_resources = set()

    for rec in records:
        if rec.resource_id in seen_resources:
            continue
        seen_resources.add(rec.resource_id)

        clean_tags = rec.tags or {}
        extracted = TagExtractor.extract_metadata(clean_tags)
        analysis = TagQualityScorer.evaluate(
            resource_id=rec.resource_id,
            raw_tags=clean_tags,
            sanitized_tags=clean_tags,
            extracted_metadata=extracted,
        )
        results.append(analysis)

    return results
