"""
CloudSage AWS CUR Ingestion Adapter Implementation.
"""

import csv
import io
from typing import Any, Iterator, Union
from backend.app.core.enums import CloudProvider
from backend.app.ingestion.adapters.aws.parser import AWSCurParser
from backend.app.ingestion.base import BaseIngestionAdapter, RawBillingItem
from backend.app.ingestion.exceptions import FileFormatError


class AWSCurAdapter(BaseIngestionAdapter):
    """Production adapter for AWS Cost & Usage Reports."""

    def __init__(self):
        super().__init__(provider=CloudProvider.AWS)

    @classmethod
    def can_handle(cls, sample_content: str, filename: str = "") -> bool:
        """Determines if content or filename matches AWS CUR signature."""
        lower_fn = filename.lower()
        if "aws" in lower_fn or "cur" in lower_fn:
            return True
        sample_lower = sample_content.lower()
        aws_indicators = [
            "lineitem/usageaccountid",
            "lineitem/unblendedcost",
            "lineitem/productcode",
            "bill/payeraccountid",
            "identity/lineitemid",
        ]
        return any(ind in sample_lower for ind in aws_indicators)

    def parse_stream(self, stream_or_path: Union[str, io.TextIOBase]) -> Iterator[RawBillingItem]:
        """Streams and parses AWS CUR CSV records."""
        if isinstance(stream_or_path, str):
            f = open(stream_or_path, mode="r", encoding="utf-8-sig")
            should_close = True
        else:
            f = stream_or_path
            should_close = False

        try:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise FileFormatError("Empty or invalid AWS CUR file header")

            for idx, row in enumerate(reader, start=1):
                if not any(row.values()):
                    continue
                yield AWSCurParser.parse_row(row, row_idx=idx)
        finally:
            if should_close:
                f.close()
