from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from .error_hierarchy import ELogErrorCode


@unique
class EDLQStatus(str, Enum):
    PENDING = "PENDING"
    RETRYING = "RETRYING"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    DISCARDED = "DISCARDED"


@dataclass(frozen=True)
class DLQEntry:
    entry_id: str
    error_code: ELogErrorCode | str
    message: str
    payload: Any
    status: EDLQStatus = EDLQStatus.PENDING
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    retry_count: int = 0
    max_attempts: int = 3
    next_retry_at: str | None = None
    last_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "error_code": self.error_code.value if hasattr(self.error_code, "value") else self.error_code,
            "message": self.message,
            "payload": self.payload,
            "status": self.status.value if hasattr(self.status, "value") else self.status,
            "timestamp_utc": self.timestamp_utc,
            "retry_count": self.retry_count,
            "max_attempts": self.max_attempts,
            "next_retry_at": self.next_retry_at,
            "last_error": self.last_error,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class DLQConfig:
    max_entries: int = 1000
    max_attempts: int = 3
    retry_delay_seconds: float = 60.0
    expiration_seconds: float = 86400.0
    enable_auto_retry: bool = True
    auto_retry_interval_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.max_entries < 0:
            raise ValueError("max_entries must be >= 0")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.retry_delay_seconds <= 0:
            raise ValueError("retry_delay_seconds must be > 0")
        if self.expiration_seconds <= 0:
            raise ValueError("expiration_seconds must be > 0")


@dataclass(frozen=True)
class DLQStatistics:
    total_entries: int = 0
    pending_entries: int = 0
    retrying_entries: int = 0
    failed_entries: int = 0
    expired_entries: int = 0
    discarded_entries: int = 0
    total_retries: int = 0
    successful_recoveries: int = 0
    last_updated_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_entries": self.total_entries,
            "pending_entries": self.pending_entries,
            "retrying_entries": self.retrying_entries,
            "failed_entries": self.failed_entries,
            "expired_entries": self.expired_entries,
            "discarded_entries": self.discarded_entries,
            "total_retries": self.total_retries,
            "successful_recoveries": self.successful_recoveries,
            "last_updated_utc": self.last_updated_utc,
        }


class IDeadLetterQueue(Protocol):
    def add(
        self,
        error_code: ELogErrorCode | str,
        message: str,
        payload: Any,
        metadata: dict[str, Any] | None = None,
    ) -> DLQEntry: ...

    def get(self, entry_id: str) -> DLQEntry | None: ...

    def get_by_status(self, status: EDLQStatus) -> list[DLQEntry]: ...

    def update_status(self, entry_id: str, status: EDLQStatus) -> bool: ...

    def retry(self, entry_id: str) -> bool: ...

    def discard(self, entry_id: str) -> bool: ...

    def get_statistics(self) -> DLQStatistics: ...

    def cleanup_expired(self) -> int: ...

    def get_all(self) -> list[DLQEntry]: ...
