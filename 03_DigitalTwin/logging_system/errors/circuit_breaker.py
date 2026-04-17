from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ECircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class CircuitBreakerConfig:
    failure_threshold: int = 5
    success_threshold: int = 2
    open_timeout_seconds: float = 30.0
    half_open_max_calls: int = 3
    sliding_window_size: int = 10


@dataclass
class CircuitBreakerMetrics:
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_transitions: int = 0
    last_failure_time: str | None = None
    last_success_time: str | None = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    opened_at: str | None = None
    closed_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "state_transitions": self.state_transitions,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
        }


class CircuitBreakerOpenError(Exception):
    def __init__(
        self,
        circuit_name: str,
        state: ECircuitState,
        message: str | None = None,
    ) -> None:
        self.circuit_name = circuit_name
        self.state = state
        default_msg = f"Circuit breaker '{circuit_name}' is {state.value}"
        super().__init__(message or default_msg)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
