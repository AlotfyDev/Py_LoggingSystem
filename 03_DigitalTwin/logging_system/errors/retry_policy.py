from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .error_hierarchy import EErrorCategory


@unique
class ERetryStrategy(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    LINEAR = "LINEAR"
    EXPONENTIAL = "EXPONENTIAL"
    FIBONACCI = "FIBONACCI"


@unique
class EJitterMode(str, Enum):
    NONE = "NONE"
    FULL = "FULL"
    DECORRELATED = "DECORRELATED"


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 3
    initial_delay_seconds: float = 0.1
    max_delay_seconds: float = 60.0
    timeout_seconds: float | None = None
    strategy: ERetryStrategy = ERetryStrategy.EXPONENTIAL
    jitter_mode: EJitterMode = EJitterMode.FULL
    retryable_categories: tuple[EErrorCategory, ...] = ()
    retryable_error_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds must be >= 0")
        if self.max_delay_seconds < 0:
            raise ValueError("max_delay_seconds must be >= 0")
        if self.timeout_seconds is not None and self.timeout_seconds < 0:
            raise ValueError("timeout_seconds must be >= 0")

    def is_error_retryable(self, error_code: str | None, category: EErrorCategory | None) -> bool:
        if category and category in self.retryable_categories:
            return True
        if error_code and error_code in self.retryable_error_codes:
            return True
        return False


@dataclass(frozen=True)
class RetryAttempt:
    attempt_number: int
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    delay_seconds: float = 0.0
    success: bool = False
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class RetryBudget:
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_delay_seconds: float = 0.0
    first_attempt_timestamp: str | None = None
    last_attempt_timestamp: str | None = None
    attempts: tuple[RetryAttempt, ...] = ()

    def add_attempt(self, attempt: RetryAttempt) -> RetryBudget:
        new_attempts = self.attempts + (attempt,)
        return RetryBudget(
            total_attempts=self.total_attempts + 1,
            successful_attempts=self.successful_attempts + (1 if attempt.success else 0),
            failed_attempts=self.failed_attempts + (0 if attempt.success else 1),
            total_delay_seconds=self.total_delay_seconds + attempt.delay_seconds,
            first_attempt_timestamp=self.first_attempt_timestamp or attempt.timestamp_utc,
            last_attempt_timestamp=attempt.timestamp_utc,
            attempts=new_attempts,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "total_delay_seconds": self.total_delay_seconds,
            "first_attempt_timestamp": self.first_attempt_timestamp,
            "last_attempt_timestamp": self.last_attempt_timestamp,
            "attempts": [
                {
                    "attempt_number": a.attempt_number,
                    "timestamp_utc": a.timestamp_utc,
                    "delay_seconds": a.delay_seconds,
                    "success": a.success,
                    "error_code": a.error_code,
                    "error_message": a.error_message,
                }
                for a in self.attempts
            ],
        }
