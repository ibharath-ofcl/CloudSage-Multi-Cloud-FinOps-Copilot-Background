"""
CloudSage Google Cloud Platform Ingestion Adapter Implementation.
"""

import csv
import io
import json
from typing import Any, Iterator, Union
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.adapters.gcp.parser import GCPApiParser
from backend.app.ingestion.base import BaseIngestionAdapter, RawBillingItem
from backend.app.ingestion.exceptions import FileFormatError


class GCPApiAdapter(BaseIngestionAdapter):
    """Production adapter for GCP Cloud Billing exports (JSON & CSV formats)."""

    def __init__(self):
        super().__init__(provider=CloudProvider.GCP)

    @classmethod
    def can_handle(cls, sample_content: str, filename: str = "") -> bool:
        """Determines if content or filename matches GCP signature."""
        lower_fn = filename.lower()
        if "gcp" in lower_fn or "bigquery" in lower_fn:
            return True
        sample_lower = sample_content.lower()
        gcp_indicators = [
            "billing_account_id",
            "project.id",
            "service.description",
            "compute.googleapis.com",
            "gcp-billing",
        ]
        return any(ind in sample_lower for ind in gcp_indicators)

    def parse_stream(self, stream_or_path: Union[str, io.TextIOBase]) -> Iterator[RawBillingItem]:
        """Streams and parses GCP Billing records (JSON array, JSONL, or CSV)."""
        if isinstance(stream_or_path, str):
            f = open(stream_or_path, mode="r", encoding="utf-8-sig")
            should_close = True
        else:
            f = stream_or_path
            should_close = False

        try:
            # Peek first character to distinguish JSON from CSV
            pos = f.tell() if hasattr(f, "tell") else 0
            first_char = f.read(1)
            if hasattr(f, "seek"):
                f.seek(pos)

            if first_char in ("[", "{"):
                # JSON or JSONL format
                content = f.read()
                content_stripped = content.strip()
                if content_stripped.startswith("[") and content_stripped.endswith("]"):
                    # JSON Array
                    items = json.loads(content_stripped)
                    for idx, row in enumerate(items, start=1):
                        yield GCPApiParser.parse_record(row, row_idx=idx)
                else:
                    # Newline-delimited JSON (JSONL)
                    for idx, line in enumerate(content.splitlines(), start=1):
                        line_str = line.strip()
                        if line_str:
                            row = json.loads(line_str)
                            yield GCPApiParser.parse_record(row, row_idx=idx)
            else:
                # CSV format
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise FileFormatError("Empty or invalid GCP CSV billing export header")
                for idx, row in enumerate(reader, start=1):
                    if not any(row.values()):
                        continue
                    yield GCPApiParser.parse_record(row, row_idx=idx)
        finally:
            if should_close:
                f.close()
