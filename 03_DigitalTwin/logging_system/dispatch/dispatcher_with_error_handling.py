from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from ..errors import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError, ECircuitState
from ..models.record import LogRecord
from ..models.utc_now_iso import utc_now_iso


@dataclass
class DispatcherWithCircuitBreaker:
    _circuit_breakers: dict[str, CircuitBreaker] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)
    _default_config: CircuitBreakerConfig = field(
        default_factory=lambda: CircuitBreakerConfig(
            failure_threshold=5,
            success_threshold=2,
            open_timeout_seconds=30,
            half_open_max_calls=3,
            sliding_window_size=10,
        )
    )

    def get_or_create_circuit_breaker(self, adapter_key: str) -> CircuitBreaker:
        with self._lock:
            if adapter_key not in self._circuit_breakers:
                self._circuit_breakers[adapter_key] = CircuitBreaker(
                    name=adapter_key,
                    config=self._default_config,
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

    def execute_with_circuit_breaker_single(
        self,
        adapter_key: str,
        task: Callable[[], Mapping[str, Any]],
    ) -> tuple[Mapping[str, Any] | None, Exception | None]:
        breaker = self.get_or_create_circuit_breaker(adapter_key)

        try:
            if not breaker.is_call_allowed():
                error = CircuitBreakerOpenError(
                    circuit_name=adapter_key,
                    state=breaker.state,
                    message=f"Circuit breaker is OPEN for adapter {adapter_key}",
                )
                return None, error

            result = breaker.call(task)
            return result, None
        except CircuitBreakerOpenError as exc:
            return None, exc
        except Exception as exc:  # noqa: BLE001
            return None, exc

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


def create_default_dispatcher() -> DispatcherWithCircuitBreaker:
    return DispatcherWithCircuitBreaker()
