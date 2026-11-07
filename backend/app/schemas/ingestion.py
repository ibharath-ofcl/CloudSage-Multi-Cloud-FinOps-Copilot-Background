"""
CloudSage Ingestion Pydantic Schemas.
Request and response schemas for billing file ingestion, run tracking, and synthetic data generation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from backend.app.core.enums import CloudProvider


class IngestionRunResponse(BaseModel):
    id: UUID
    provider: str
    source_filename: str
    status: str
    total_records: int
    ingested_records: int
    duplicate_records: int
    failed_records: int
    total_cost: Decimal
    checksum: Optional[str] = None
    error_summary: Optional[List[Dict[str, Any]]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class IngestionSummaryResponse(BaseModel):
    total_runs: int
    total_records_ingested: int
    total_cost_ingested_usd: Decimal
    provider_breakdown: Dict[str, int]
    latest_run: Optional[IngestionRunResponse] = None


class SyntheticGenerateRequest(BaseModel):
    record_count: int = Field(default=1000, ge=10, le=50000, description="Total synthetic records to generate")
    scenarios: List[str] = Field(
        default=["normal", "idle_vm", "unattached_storage", "oversized_compute", "cost_spike", "poor_tagging"],
        description="Scenarios to simulate"
    )
    seed: int = Field(default=42, description="Random seed for deterministic generation")
    output_format: str = Field(default="json", description="Output file format: json or csv")


class SyntheticGenerateResponse(BaseModel):
    status: str
    total_records_generated: int
    files_created: Dict[str, str]
    scenario_distribution: Dict[str, int]
    generation_timestamp: datetime
