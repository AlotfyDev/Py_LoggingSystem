from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any


@unique
class EErrorCategory(str, Enum):
    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    PARTIAL = "PARTIAL"


@unique
class ERetryableError(str, Enum):
    NETWORK_UNREACHABLE = "NETWORK_UNREACHABLE"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    READ_TIMEOUT = "READ_TIMEOUT"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    BACKPRESSURE = "BACKPRESSURE"
    TRANSIENT_BINDING_ERROR = "TRANSIENT_BINDING_ERROR"


@unique
class ELogErrorCode(str, Enum):
    ADAPTER_NOT_FOUND = "ADAPTER_NOT_FOUND"
    ADAPTER_INIT_FAILED = "ADAPTER_INIT_FAILED"
    ADAPTER_DISPATCH_FAILED = "ADAPTER_DISPATCH_FAILED"
    ADAPTER_TIMEOUT = "ADAPTER_TIMEOUT"
    SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
    SCHEMA_MISSING_REQUIRED_FIELD = "SCHEMA_MISSING_REQUIRED_FIELD"
    SCHEMA_INVALID_FIELD_TYPE = "SCHEMA_INVALID_FIELD_TYPE"
    BINDING_FAILED = "BINDING_FAILED"
    BINDING_MISSING_ADAPTER_KEY = "BINDING_MISSING_ADAPTER_KEY"
    BINDING_INVALID_PAYLOAD = "BINDING_INVALID_PAYLOAD"
    QUEUE_FULL = "QUEUE_FULL"
    QUEUE_PUT_FAILED = "QUEUE_PUT_FAILED"
    QUEUE_GET_FAILED = "QUEUE_GET_FAILED"
    ENVELOPE_MALFORMED = "ENVELOPE_MALFORMED"
    ENVELOPE_MISSING_CONTENT = "ENVELOPE_MISSING_CONTENT"
    ENVELOPE_SERIALIZATION_FAILED = "ENVELOPE_SERIALIZATION_FAILED"
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_MISSING_REQUIRED = "CONFIG_MISSING_REQUIRED"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    PROFILE_ACTIVATION_FAILED = "PROFILE_ACTIVATION_FAILED"
    CATALOG_ERROR = "CATALOG_ERROR"
    CONTAINER_ERROR = "CONTAINER_ERROR"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


@dataclass(frozen=True)
class ErrorContext:
    error_code: ELogErrorCode
    category: EErrorCategory
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)
    original_error: BaseException | None = None
    stack_trace: str | None = None

    def is_retryable(self) -> bool:
        if self.category == EErrorCategory.TRANSIENT:
            return True
        if self.category == EErrorCategory.PARTIAL:
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code.value if self.error_code else None,
            "category": self.category.value if self.category else None,
            "timestamp_utc": self.timestamp_utc,
            "metadata": self.metadata,
            "original_error": str(self.original_error) if self.original_error else None,
            "stack_trace": self.stack_trace,
        }
