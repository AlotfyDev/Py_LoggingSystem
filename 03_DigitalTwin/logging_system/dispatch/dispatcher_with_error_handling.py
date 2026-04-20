from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from ..errors import (
    BackoffCalculator,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    DLQConfig,
    DLQEntry,
    EDLQStatus,
    ECircuitState,
    ERetryStrategy,
    FileBasedDeadLetterQueue,
    RetryConfig,
)
from ..models.record import LogRecord
from ..models.utc_now_iso import utc_now_iso


@dataclass
class DispatchResult:
    results: list[Mapping[str, Any]]
    errors: list[Exception]
    retries_attempted: int = 0
    dlq_entries: list[DLQEntry] = field(default_factory=list)


@dataclass
class DispatcherWithErrorHandling:
    _circuit_breakers: dict[str, CircuitBreaker] = field(default_factory=dict)
    _dlq: FileBasedDeadLetterQueue = field(
        default_factory=lambda: FileBasedDeadLetterQueue(
            config=DLQConfig(max_entries=1000, retry_delay_seconds=60)
        )
    )
    _lock: RLock = field(default_factory=RLock)
    _default_circuit_config: CircuitBreakerConfig = field(
        default_factory=lambda: CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=2,
            open_timeout_seconds=30,
            half_open_max_calls=3,
            sliding_window_size=10,
        )
    )
    _default_retry_config: RetryConfig = field(
        default_factory=lambda: RetryConfig(
            max_attempts=3,
            initial_delay_seconds=0.1,
            max_delay_seconds=5.0,
            strategy=ERetryStrategy.EXPONENTIAL,
            retryable_error_codes=("TimeoutError", "ConnectionError", "RuntimeError"),
        )
    )
    _retryable_codes: tuple[str, ...] = field(
        default_factory=lambda: (
            "TimeoutError",
            "ConnectionError",
            "ConnectionResetError",
            "BrokenPipeError",
            "FileNotFoundError",
            "RuntimeError",
        )
    )
    _retry_metrics: dict[str, int] = field(default_factory=dict)

    def get_or_create_circuit_breaker(self, adapter_key: str) -> CircuitBreaker:
        with self._lock:
            if adapter_key not in self._circuit_breakers:
                self._circuit_breakers[adapter_key] = CircuitBreaker(
                    name=adapter_key,
                    config=self._default_circuit_config,
                )
            return self._circuit_breakers[adapter_key]

    def get_circuit_state(self, adapter_key: str) -> ECircuitState:
        with self._lock:
            if adapter_key not in self._circuit_breakers:
                return ECircuitState.CLOSED
            return self._circuit_breakers[adapter_key].state

    def is_dispatch_allowed(self, adapter_key: str) -> bool:
        breaker = self.get_or_create_circuit_breaker(adapter_key)
        return breaker.is_call_allowed()

    def is_error_retryable(self, error: Exception) -> bool:
        error_code = type(error).__name__
        return error_code in self._retryable_codes

    def execute_with_retry(
        self,
        adapter_key: str,
        tasks: list[Callable[[], Mapping[str, Any]]],
        retry_config: RetryConfig | None = None,
        record: LogRecord | Mapping[str, Any] | None = None,
    ) -> DispatchResult:
        config = retry_config or self._default_retry_config
        backoff = BackoffCalculator(
            initial_delay_seconds=config.initial_delay_seconds,
            max_delay_seconds=config.max_delay_seconds,
            strategy=config.strategy,
            jitter_mode=config.jitter_mode,
        )

        results: list[Mapping[str, Any]] = []
        errors: list[Exception] = []
        dlq_entries: list[DLQEntry] = []
        total_retries = 0

        for task in tasks:
            success, error, retry_count = self._execute_single_with_retry(
                adapter_key=adapter_key,
                task=task,
                config=config,
                backoff=backoff,
            )
            total_retries += retry_count

            if success:
                results.append(success)
            else:
                errors.append(error)
                if error is not None and record is not None:
                    entry = self.enqueue_to_dlq(
                        record=record,
                        error=error,
                        adapter_key=adapter_key,
                        context={"retry_count": retry_count},
                    )
                    dlq_entries.append(entry)

        return DispatchResult(
            results=results,
            errors=errors,
            retries_attempted=total_retries,
            dlq_entries=dlq_entries,
        )

    def _execute_single_with_retry(
        self,
        adapter_key: str,
        task: Callable[[], Mapping[str, Any]],
        config: RetryConfig,
        backoff: BackoffCalculator,
    ) -> tuple[Mapping[str, Any] | None, Exception | None, int]:
        breaker = self.get_or_create_circuit_breaker(adapter_key)
        retry_count = 0
        last_error: Exception | None = None

        for attempt in range(1, config.max_attempts + 1):
            try:
                if not breaker.is_call_allowed():
                    last_error = CircuitBreakerOpenError(
                        circuit_name=adapter_key,
                        state=breaker.state,
                        message=f"Circuit breaker is OPEN for adapter {adapter_key}",
                    )
                    break

                result = breaker.call(task)
                if retry_count > 0:
                    self._record_retry_metric(adapter_key)
                return result, None, retry_count

            except CircuitBreakerOpenError as exc:
                last_error = exc
                break

            except Exception as exc:  # noqa: BLE001
                last_error = exc

                if not self.is_error_retryable(exc):
                    break

                retry_count += 1

                if attempt < config.max_attempts:
                    delay = backoff.calculate_delay(attempt)
                    if delay > 0:
                        time.sleep(delay)

        return None, last_error, retry_count

    def _record_retry_metric(self, adapter_key: str) -> None:
        with self._lock:
            if adapter_key not in self._retry_metrics:
                self._retry_metrics[adapter_key] = 0
            self._retry_metrics[adapter_key] += 1

    def get_retry_metrics(self, adapter_key: str | None = None) -> dict[str, int]:
        with self._lock:
            if adapter_key:
                return {adapter_key: self._retry_metrics.get(adapter_key, 0)}
            return dict(self._retry_metrics)

    def execute_with_circuit_breaker(
        self,
        adapter_key: str,
        tasks: list[Callable[[], Mapping[str, Any]]],
    ) -> tuple[list[Mapping[str, Any]], list[Exception]]:
        breaker = self.get_or_create_circuit_breaker(adapter_key)
        results: list[Mapping[str, Any]] = []
        errors: list[Exception] = []

        for task in tasks:
            try:
                if not breaker.is_call_allowed():
                    error = CircuitBreakerOpenError(
                        circuit_name=adapter_key,
                        state=breaker.state,
                        message=f"Circuit breaker is OPEN for adapter {adapter_key}",
                    )
                    errors.append(error)
                    continue

                result = breaker.call(task)
                results.append(result)
            except CircuitBreakerOpenError as exc:
                errors.append(exc)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        return results, errors

    def enqueue_to_dlq(
        self,
        record: LogRecord | Mapping[str, Any],
        error: Exception,
        adapter_key: str,
        context: Mapping[str, Any] | None = None,
    ) -> DLQEntry:
        error_code = self._classify_error(error)
        message = f"Dispatch failed for adapter {adapter_key}: {str(error)}"

        if isinstance(record, LogRecord):
            payload = record.to_projection()
        else:
            payload = dict(record)

        metadata = {
            "adapter_key": adapter_key,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": utc_now_iso(),
            "is_retryable": self.is_error_retryable(error),
        }
        if context:
            metadata["context"] = dict(context)

        return self._dlq.add(
            error_code=error_code,
            message=message,
            payload=payload,
            metadata=metadata,
        )

    def _classify_error(self, error: Exception) -> str:
        error_type = type(error).__name__
        error_msg = str(error).lower()
        if isinstance(error, CircuitBreakerOpenError):
            return "CIRCUIT_OPEN"
        elif "timeout" in error_msg or "timed out" in error_msg:
            return "TIMEOUT"
        elif "connection" in error_msg:
            return "CONNECTION_ERROR"
        elif "auth" in error_msg or "permission" in error_msg or "unauthorized" in error_msg:
            return "AUTH_ERROR"
        return f"ERROR_{error_type.upper()}"

    def get_dlq_entry(self, entry_id: str) -> DLQEntry | None:
        return self._dlq.get(entry_id)

    def get_dlq_entries_by_status(self, status: EDLQStatus) -> list[DLQEntry]:
        return self._dlq.get_by_status(status)

    def get_dlq_statistics(self) -> dict[str, Any]:
        stats = self._dlq.get_statistics()
        return {
            "total_entries": stats.total_entries,
            "pending_entries": stats.pending_entries,
            "retrying_entries": stats.retrying_entries,
            "failed_entries": stats.failed_entries,
            "discarded_entries": stats.discarded_entries,
            "total_retries": stats.total_retries,
            "successful_recoveries": stats.successful_recoveries,
        }

    def retry_dlq_entry(self, entry_id: str) -> bool:
        return self._dlq.retry(entry_id)

    def discard_dlq_entry(self, entry_id: str) -> bool:
        return self._dlq.discard(entry_id)

    def get_failed_entries(self) -> list[DLQEntry]:
        return self._dlq.get_by_status(EDLQStatus.FAILED)

    def get_pending_entries(self) -> list[DLQEntry]:
        return self._dlq.get_by_status(EDLQStatus.PENDING)

    def get_all_dlq_entries(self) -> list[DLQEntry]:
        return self._dlq.get_all()

    def clear_dlq(self) -> int:
        return self._dlq.clear()

    def flush_dlq(self) -> None:
        self._dlq.flush()

    def get_all_circuit_states(self) -> Mapping[str, dict[str, Any]]:
        with self._lock:
            states = {}
            for adapter_key, breaker in self._circuit_breakers.items():
                m = breaker.metrics
                states[adapter_key] = {
                    "state": breaker.state.value,
                    "metrics": {
                        "total_calls": m.total_calls,
                        "successful_calls": m.successful_calls,
                        "failed_calls": m.failed_calls,
                        "rejected_calls": m.rejected_calls,
                        "consecutive_failures": m.consecutive_failures,
                        "consecutive_successes": m.consecutive_successes,
                        "opened_at": m.opened_at,
                        "closed_at": m.closed_at,
                    },
                }
            return states

    def reset_circuit(self, adapter_key: str) -> bool:
        with self._lock:
            if adapter_key not in self._circuit_breakers:
                return False
            self._circuit_breakers[adapter_key].reset()
            return True

    def reset_all_circuits(self) -> int:
        with self._lock:
            count = len(self._circuit_breakers)
            for breaker in self._circuit_breakers.values():
                breaker.reset()
            return count

    def get_circuit_metrics(self, adapter_key: str) -> dict[str, Any] | None:
        with self._lock:
            if adapter_key not in self._circuit_breakers:
                return None
            m = self._circuit_breakers[adapter_key].metrics
            return {
                "total_calls": m.total_calls,
                "successful_calls": m.successful_calls,
                "failed_calls": m.failed_calls,
                "rejected_calls": m.rejected_calls,
                "state_transitions": m.state_transitions,
                "consecutive_failures": m.consecutive_failures,
                "consecutive_successes": m.consecutive_successes,
                "last_failure_time": m.last_failure_time,
                "last_success_time": m.last_success_time,
                "opened_at": m.opened_at,
                "closed_at": m.closed_at,
            }

    def collect_error_handling_evidence(self) -> dict[str, Any]:
        return {
            "circuit_breakers": self.get_all_circuit_states(),
            "dlq_statistics": self.get_dlq_statistics(),
            "dlq_failed_count": len(self.get_failed_entries()),
            "dlq_pending_count": len(self.get_pending_entries()),
            "retry_metrics": self.get_retry_metrics(),
        }


def create_default_dispatcher() -> DispatcherWithErrorHandling:
    return DispatcherWithErrorHandling()


DispatcherWithCircuitBreaker = DispatcherWithErrorHandling
