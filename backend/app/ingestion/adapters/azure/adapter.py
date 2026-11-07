"""
CloudSage Azure Cost Management Ingestion Adapter Implementation.
"""

import csv
import io
from typing import Any, Iterator, Union
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.adapters.azure.parser import AzureCostParser
from backend.app.ingestion.base import BaseIngestionAdapter, RawBillingItem
from backend.app.ingestion.exceptions import FileFormatError


class AzureCostAdapter(BaseIngestionAdapter):
    """Production adapter for Microsoft Azure Cost Management exports."""

    def __init__(self):
        super().__init__(provider=CloudProvider.AZURE)

    @classmethod
    def can_handle(cls, sample_content: str, filename: str = "") -> bool:
        """Determines if content or filename matches Azure export signature."""
        lower_fn = filename.lower()
        if "azure" in lower_fn:
            return True
        sample_lower = sample_content.lower()
        azure_indicators = [
            "metercategory",
            "subscriptionguid",
            "costinbillingcurrency",
            "resourcegroup",
            "consumedservice",
            "subscriptionname",
        ]
        return any(ind in sample_lower for ind in azure_indicators)

    def parse_stream(self, stream_or_path: Union[str, io.TextIOBase]) -> Iterator[RawBillingItem]:
        """Streams and parses Azure CSV cost export records."""
        if isinstance(stream_or_path, str):
            f = open(stream_or_path, mode="r", encoding="utf-8-sig")
            should_close = True
        else:
            f = stream_or_path
            should_close = False

        try:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise FileFormatError("Empty or invalid Azure Cost export header")

            for idx, row in enumerate(reader, start=1):
                if not any(row.values()):
                    continue
                yield AzureCostParser.parse_row(row, row_idx=idx)
        finally:
            if should_close:
                f.close()
