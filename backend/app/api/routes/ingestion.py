"""
CloudSage Ingestion API Endpoints.
FastAPI router providing multi-cloud billing file upload, synthetic generation, and run tracking.
"""

import io
import os
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_sync_db
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.base import IngestionResult
from backend.app.ingestion.services.ingestion_service import IngestionService
from backend.app.ingestion.synthetic.datasets import export_sample_datasets
from backend.app.schemas.ingestion import (
    IngestionRunResponse,
    IngestionSummaryResponse,
    SyntheticGenerateRequest,
    SyntheticGenerateResponse,
)

router = APIRouter(prefix="/ingestion", tags=["Multi-Cloud Ingestion"])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit
ALLOWED_EXTENSIONS = {".csv", ".json", ".jsonl"}


def validate_uploaded_file(file: UploadFile) -> str:
    """Validates file presence, filename, and extension."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing file provided or filename is missing"
        )
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Permitted extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    return ext


def process_file_upload(
    db: Session,
    file: UploadFile,
    provider: CloudProvider
) -> Dict[str, Any]:
    """Safely streams uploaded file to temporary storage and executes ingestion."""
    validate_uploaded_file(file)

    # Use a secure temporary file
    temp_dir = tempfile.mkdtemp(prefix="cloudsage_ingest_")
    safe_filename = os.path.basename(file.filename)
    temp_path = os.path.join(temp_dir, safe_filename)

    try:
        size = 0
        with open(temp_path, "wb") as f_out:
            while chunk := file.file.read(65536):
                size += len(chunk)
                if size > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Uploaded file exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB"
                    )
                f_out.write(chunk)

        # Execute ingestion pipeline
        result: IngestionResult = IngestionService.ingest_file(
            db=db,
            file_path=temp_path,
            provider=provider
        )

        return {
            "status": "success" if result.failed_records == 0 else "partial_success",
            "batch_id": str(result.batch_id),
            "provider": result.provider.value,
            "filename": safe_filename,
            "total_records": result.total_records,
            "ingested_records": result.ingested_records,
            "duplicate_records": result.skipped_duplicates,
            "failed_records": result.failed_records,
            "total_cost_usd": result.total_cost_usd,
            "duration_ms": round(result.duration_ms, 2),
            "errors": result.errors[:20],
        }

    finally:
        # Clean up temporary file and directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/aws", status_code=status.HTTP_200_OK, summary="Ingest AWS Cost & Usage Report (CUR)")
def ingest_aws_billing(
    file: UploadFile = File(...),
    db: Session = Depends(get_sync_db)
):
    """
    Accepts an AWS Cost and Usage Report (CUR CSV) file and ingests it into normalized billing records.
    """
    return process_file_upload(db=db, file=file, provider=CloudProvider.AWS)


@router.post("/azure", status_code=status.HTTP_200_OK, summary="Ingest Azure Cost Management Export")
def ingest_azure_billing(
    file: UploadFile = File(...),
    db: Session = Depends(get_sync_db)
):
    """
    Accepts an Azure Cost Management Export (CSV) file and ingests it into normalized billing records.
    """
    return process_file_upload(db=db, file=file, provider=CloudProvider.AZURE)


@router.post("/gcp", status_code=status.HTTP_200_OK, summary="Ingest GCP Cloud Billing Export")
def ingest_gcp_billing(
    file: UploadFile = File(...),
    db: Session = Depends(get_sync_db)
):
    """
    Accepts a GCP Cloud Billing Export (BigQuery JSON array, JSONL, or CSV) and ingests it.
    """
    return process_file_upload(db=db, file=file, provider=CloudProvider.GCP)


@router.post(
    "/synthetic/generate",
    response_model=SyntheticGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Synthetic Multi-Cloud Benchmark Datasets"
)
def generate_synthetic_data(request: SyntheticGenerateRequest):
    """
    Generates synthetic multi-cloud billing datasets with seeded waste and anomaly scenarios.
    Outputs files to backend/sample_data/.
    """
    files = export_sample_datasets(
        output_dir="backend/sample_data",
        total_records=request.record_count,
        seed=request.seed
    )
    records_per_provider = request.record_count // 3
    return SyntheticGenerateResponse(
        status="generated",
        total_records_generated=request.record_count,
        files_created=files,
        scenario_distribution={
            "normal_expenditure": int(request.record_count * 0.40),
            "idle_vm_waste": int(request.record_count * 0.15),
            "unattached_storage": int(request.record_count * 0.15),
            "oversized_compute": int(request.record_count * 0.10),
            "cost_spikes": int(request.record_count * 0.05),
            "poorly_tagged": int(request.record_count * 0.15),
        },
        generation_timestamp=datetime.now()
    )


@router.get("/runs", response_model=List[IngestionRunResponse], summary="List Ingestion Runs")
def list_ingestion_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    provider: Optional[str] = Query(None, description="Filter by cloud provider (AWS, AZURE, GCP)"),
    db: Session = Depends(get_sync_db)
):
    """Retrieves chronological history of all executed ingestion jobs."""
    return IngestionService.get_runs(db=db, limit=limit, offset=offset, provider=provider)


@router.get("/runs/{run_id}", response_model=IngestionRunResponse, summary="Get Specific Ingestion Run")
def get_ingestion_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_sync_db)
):
    """Fetches full telemetry, error summaries, and metrics for a specific ingestion run."""
    run = IngestionService.get_run(db=db, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion run with ID '{run_id}' not found"
        )
    return run


@router.get("/summary", summary="Get Global Ingestion Summary")
def get_ingestion_summary(db: Session = Depends(get_sync_db)):
    """Provides high-level aggregated metrics across all ingestion runs."""
    return IngestionService.get_summary(db=db)
