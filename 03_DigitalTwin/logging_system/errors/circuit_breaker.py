from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Any, Callable, TypeVar

T = TypeVar("T")


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

    def __post_init__(self) -> None:
        if self.failure_threshold <= 0:
            raise ValueError("failure_threshold must be > 0")
        if self.success_threshold <= 0:
            raise ValueError("success_threshold must be > 0")
        if self.open_timeout_seconds <= 0:
            raise ValueError("open_timeout_seconds must be > 0")
        if self.half_open_max_calls <= 0:
            raise ValueError("half_open_max_calls must be > 0")
        if self.sliding_window_size <= 0:
            raise ValueError("sliding_window_size must be > 0")


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
    half_open_calls_allowed: int = 0
    half_open_calls_made: int = 0

    @property
    def failure_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    @property
    def rejection_rate(self) -> float:
        total_attempts = self.total_calls + self.rejected_calls
        if total_attempts == 0:
            return 0.0
        return self.rejected_calls / total_attempts

    @property
    def availability(self) -> float:
        total = self.successful_calls + self.failed_calls
        if total == 0:
            return 1.0
        return self.successful_calls / total

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
            "half_open_calls_allowed": self.half_open_calls_allowed,
            "half_open_calls_made": self.half_open_calls_made,
            "failure_rate": self.failure_rate,
            "success_rate": self.success_rate,
            "rejection_rate": self.rejection_rate,
            "availability": self.availability,
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


@dataclass
class CircuitBreaker:
    name: str
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    def __post_init__(self) -> None:
        self._state: ECircuitState = ECircuitState.CLOSED
        self._lock = RLock()
        self._failure_history: deque[bool] = deque(maxlen=self.config.sliding_window_size)
        self._consecutive_failures: int = 0
        self._consecutive_successes: int = 0
        self._half_open_calls: int = 0
        self._opened_at: datetime | None = None
        self._metrics = CircuitBreakerMetrics()

    @property
    def state(self) -> ECircuitState:
        with self._lock:
            self._check_state_transition()
            return self._state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        with self._lock:
            return CircuitBreakerMetrics(
                total_calls=self._metrics.total_calls,
                successful_calls=self._metrics.successful_calls,
                failed_calls=self._metrics.failed_calls,
                rejected_calls=self._metrics.rejected_calls,
                state_transitions=self._metrics.state_transitions,
                last_failure_time=self._metrics.last_failure_time,
                last_success_time=self._metrics.last_success_time,
                consecutive_failures=self._consecutive_failures,
                consecutive_successes=self._consecutive_successes,
                opened_at=self._opened_at.isoformat() if self._opened_at else None,
                closed_at=self._metrics.closed_at,
                half_open_calls_allowed=self._metrics.half_open_calls_allowed,
                half_open_calls_made=self._metrics.half_open_calls_made,
            )

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        if not self.is_call_allowed():
            self._metrics.rejected_calls += 1
            raise CircuitBreakerOpenError(
                circuit_name=self.name,
                state=self._state,
            )

        with self._lock:
            self._metrics.total_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def is_call_allowed(self) -> bool:
        with self._lock:
            self._check_state_transition()
            if self._state == ECircuitState.OPEN:
                return False
            if self._state == ECircuitState.HALF_OPEN:
                allowed = self._half_open_calls < self.config.half_open_max_calls
                if allowed:
                    self._metrics.half_open_calls_allowed += 1
                return allowed
            return True

    def _check_state_transition(self) -> None:
        if self._state == ECircuitState.OPEN and self._opened_at is not None:
            elapsed = (datetime.now(timezone.utc) - self._opened_at).total_seconds()
            if elapsed >= self.config.open_timeout_seconds:
                self._transition_to(ECircuitState.HALF_OPEN)

    def _on_success(self) -> None:
        with self._lock:
            self._metrics.successful_calls += 1
            self._metrics.last_success_time = _utc_now()
            self._failure_history.append(True)
            self._consecutive_failures = 0

            if self._state == ECircuitState.HALF_OPEN:
                self._half_open_calls += 1
                self._metrics.half_open_calls_made += 1
                self._consecutive_successes += 1
                if self._consecutive_successes >= self.config.success_threshold:
                    self._transition_to(ECircuitState.CLOSED)
            elif self._state == ECircuitState.CLOSED:
                self._consecutive_successes += 1

    def _on_failure(self) -> None:
        with self._lock:
            self._metrics.failed_calls += 1
            self._metrics.last_failure_time = _utc_now()
            self._failure_history.append(False)
            self._consecutive_successes = 0
            self._consecutive_failures += 1

            if self._state == ECircuitState.HALF_OPEN:
                self._transition_to(ECircuitState.OPEN)
            elif self._state == ECircuitState.CLOSED:
                if self._consecutive_failures >= self.config.failure_threshold:
                    self._transition_to(ECircuitState.OPEN)

    def _transition_to(self, new_state: ECircuitState) -> None:
        if self._state == new_state:
            return

        old_state = self._state
        self._state = new_state
        self._metrics.state_transitions += 1

        if new_state == ECircuitState.OPEN:
            self._opened_at = datetime.now(timezone.utc)
            self._metrics.opened_at = self._opened_at.isoformat()
            self._half_open_calls = 0
            self._consecutive_successes = 0
        elif new_state == ECircuitState.CLOSED:
            self._opened_at = None
            self._metrics.closed_at = _utc_now()
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._half_open_calls = 0
            self._failure_history.clear()
        elif new_state == ECircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._consecutive_failures = 0

    def get_recent_failures(self) -> int:
        with self._lock:
            return sum(1 for f in self._failure_history if not f)

    def reset(self) -> None:
        with self._lock:
            self._state = ECircuitState.CLOSED
            self._opened_at = None
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._half_open_calls = 0
            self._failure_history.clear()
            self._metrics = CircuitBreakerMetrics()
