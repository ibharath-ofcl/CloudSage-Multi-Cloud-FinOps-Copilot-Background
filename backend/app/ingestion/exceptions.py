"""
CloudSage Ingestion Exceptions.
Domain-specific exceptions for multi-cloud billing parsing, validation, and normalization.
"""

from typing import Any, Dict, List, Optional


class IngestionError(Exception):
    """Base exception for all ingestion failures."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AdapterNotFoundError(IngestionError):
    """Raised when no adapter is registered for a given cloud provider or file format."""
    pass


class FileFormatError(IngestionError):
    """Raised when the uploaded billing file is malformed, empty, or unsupported."""
    pass


class IngestionValidationError(IngestionError):
    """Raised when a billing record fails schema or data type validation."""
    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message, {"validation_errors": errors or []})
        self.errors = errors or []


class DuplicateBatchError(IngestionError):
    """Raised when an identical file batch is uploaded and rejected."""
    pass


class CorruptedRecordError(IngestionError):
    """Raised when a single line item is structurally corrupted."""
    pass
