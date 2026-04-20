import time
from collections.abc import Mapping
from typing import Any

import pytest

from logging_system.dispatch import DispatcherWithCircuitBreaker
from logging_system.errors import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    ECircuitState,
)


def create_breaker_with_config(dispatcher, adapter_key, config):
    with dispatcher._lock:
        dispatcher._circuit_breakers[adapter_key] = CircuitBreaker(
            name=adapter_key,
            config=config,
        )


class TestDispatchWithCircuitBreaker:
    def test_dispatch_with_circuit_breaker_success(self):
        dispatcher = DispatcherWithCircuitBreaker()
        adapter_key = "telemetry.test"

        def success_task() -> Mapping[str, Any]:
            return {"status": "ok", "data": "test"}

        tasks = [success_task, success_task]
        results, errors = dispatcher.execute_with_circuit_breaker(adapter_key, tasks)

        assert len(results) == 2
        assert len(errors) == 0
        assert results[0]["status"] == "ok"

    def test_dispatch_with_circuit_breaker_failure(self):
        dispatcher = DispatcherWithCircuitBreaker()
        adapter_key = "telemetry.test"
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            open_timeout_seconds=30,
            half_open_max_calls=3,
            sliding_window_size=10,
        )
        create_breaker_with_config(dispatcher, adapter_key, config)

        def failing_task() -> Mapping[str, Any]:
            raise RuntimeError("Adapter failure")

        tasks = [failing_task, failing_task, failing_task]
        results, errors = dispatcher.execute_with_circuit_breaker(adapter_key, tasks)

        assert len(results) == 0
        assert len(errors) == 3

        breaker = dispatcher.get_or_create_circuit_breaker(adapter_key)
        assert breaker.state == ECircuitState.OPEN

    def test_circuit_open_rejects_dispatch(self):
        dispatcher = DispatcherWithCircuitBreaker()
        adapter_key = "telemetry.test"
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=1,
            open_timeout_seconds=1,
            half_open_max_calls=1,
            sliding_window_size=5,
        )
        create_breaker_with_config(dispatcher, adapter_key, config)

        def failing_task() -> Mapping[str, Any]:
            raise RuntimeError("Adapter failure")

        tasks = [failing_task, failing_task]
        dispatcher.execute_with_circuit_breaker(adapter_key, tasks)

        breaker = dispatcher.get_or_create_circuit_breaker(adapter_key)
        assert breaker.state == ECircuitState.OPEN
        assert not dispatcher.is_dispatch_allowed(adapter_key)

        def success_task() -> Mapping[str, Any]:
            return {"status": "ok"}

        tasks = [success_task]
        results, errors = dispatcher.execute_with_circuit_breaker(adapter_key, tasks)

        assert len(results) == 0
        assert len(errors) == 1
        assert isinstance(errors[0], CircuitBreakerOpenError)

    def test_circuit_half_open_allows_dispatch(self):
        dispatcher = DispatcherWithCircuitBreaker()
        adapter_key = "telemetry.test"
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=1,
            open_timeout_seconds=0.5,
            half_open_max_calls=2,
            sliding_window_size=5,
        )
        create_breaker_with_config(dispatcher, adapter_key, config)

        def failing_task() -> Mapping[str, Any]:
            raise RuntimeError("Adapter failure")

        tasks = [failing_task, failing_task]
        dispatcher.execute_with_circuit_breaker(adapter_key, tasks)

        breaker = dispatcher.get_or_create_circuit_breaker(adapter_key)
        assert breaker.state == ECircuitState.OPEN

        time.sleep(0.6)

        assert breaker.is_call_allowed()
        assert breaker.state == ECircuitState.HALF_OPEN

        def success_task() -> Mapping[str, Any]:
            return {"status": "ok"}

        tasks = [success_task]
        results, errors = dispatcher.execute_with_circuit_breaker(adapter_key, tasks)

        assert len(results) == 1
        assert len(errors) == 0

    def test_circuit_state_reflected_in_metrics(self):
        dispatcher = DispatcherWithCircuitBreaker()
        adapter_key = "telemetry.test"

        def success_task() -> Mapping[str, Any]:
            return {"status": "ok"}

        def failing_task() -> Mapping[str, Any]:
            raise RuntimeError("Adapter failure")

        dispatcher.execute_with_circuit_breaker(adapter_key, [success_task])
        dispatcher.execute_with_circuit_breaker(adapter_key, [failing_task])

        metrics = dispatcher.get_circuit_metrics(adapter_key)
        assert metrics is not None
        assert metrics["total_calls"] == 2
        assert metrics["successful_calls"] == 1
        assert metrics["failed_calls"] == 1

    def test_no_adapter_calls_when_circuit_open(self):
        dispatcher = DispatcherWithCircuitBreaker()
        adapter_key = "telemetry.test"
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            open_timeout_seconds=30,
            half_open_max_calls=3,
            sliding_window_size=10,
        )
        create_breaker_with_config(dispatcher, adapter_key, config)
        call_count = 0

        def tracked_task() -> Mapping[str, Any]:
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Adapter failure")

        tasks = [tracked_task] * 3
        dispatcher.execute_with_circuit_breaker(adapter_key, tasks)

        assert call_count == 3
        assert not dispatcher.is_dispatch_allowed(adapter_key)

        call_count = 0
        tasks = [tracked_task] * 2
        results, errors = dispatcher.execute_with_circuit_breaker(adapter_key, tasks)

        assert call_count == 0
        assert len(results) == 0
        assert len(errors) == 2

    def test_get_all_circuit_states(self):
        dispatcher = DispatcherWithCircuitBreaker()

        def success_task() -> Mapping[str, Any]:
            return {"status": "ok"}

        dispatcher.execute_with_circuit_breaker("adapter1", [success_task])
        dispatcher.execute_with_circuit_breaker("adapter2", [success_task])

        states = dispatcher.get_all_circuit_states()

        assert "adapter1" in states
        assert "adapter2" in states
        assert states["adapter1"]["state"] == ECircuitState.CLOSED.value
        assert states["adapter2"]["state"] == ECircuitState.CLOSED.value

    def test_reset_circuit(self):
        dispatcher = DispatcherWithCircuitBreaker()
        adapter_key = "telemetry.test"
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            open_timeout_seconds=30,
            half_open_max_calls=3,
            sliding_window_size=10,
        )
        create_breaker_with_config(dispatcher, adapter_key, config)

        def failing_task() -> Mapping[str, Any]:
            raise RuntimeError("Adapter failure")

        tasks = [failing_task] * 3
        dispatcher.execute_with_circuit_breaker(adapter_key, tasks)

        breaker = dispatcher.get_or_create_circuit_breaker(adapter_key)
        assert breaker.state == ECircuitState.OPEN

        result = dispatcher.reset_circuit(adapter_key)
        assert result is True
        assert breaker.state == ECircuitState.CLOSED
        assert dispatcher.is_dispatch_allowed(adapter_key)

    def test_reset_all_circuits(self):
        dispatcher = DispatcherWithCircuitBreaker()
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            open_timeout_seconds=30,
            half_open_max_calls=3,
            sliding_window_size=10,
        )
        create_breaker_with_config(dispatcher, "adapter1", config)
        create_breaker_with_config(dispatcher, "adapter2", config)

        def failing_task() -> Mapping[str, Any]:
            raise RuntimeError("Adapter failure")

        dispatcher.execute_with_circuit_breaker("adapter1", [failing_task] * 3)
        dispatcher.execute_with_circuit_breaker("adapter2", [failing_task] * 3)

        count = dispatcher.reset_all_circuits()
        assert count == 2

        assert dispatcher.is_dispatch_allowed("adapter1")
        assert dispatcher.is_dispatch_allowed("adapter2")


class TestCircuitBreakerIntegration:
    def test_circuit_breaker_per_adapter_isolation(self):
        dispatcher = DispatcherWithCircuitBreaker()
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            open_timeout_seconds=30,
            half_open_max_calls=3,
            sliding_window_size=10,
        )
        create_breaker_with_config(dispatcher, "adapter1", config)

        def failing_task() -> Mapping[str, Any]:
            raise RuntimeError("Adapter failure")

        def success_task() -> Mapping[str, Any]:
            return {"status": "ok"}

        dispatcher.execute_with_circuit_breaker("adapter1", [failing_task] * 3)
        assert not dispatcher.is_dispatch_allowed("adapter1")

        dispatcher.execute_with_circuit_breaker("adapter2", [success_task])
        assert dispatcher.is_dispatch_allowed("adapter2")

    def test_circuit_breaker_state_transitions(self):
        dispatcher = DispatcherWithCircuitBreaker()
        adapter_key = "telemetry.test"
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=1,
            open_timeout_seconds=0.3,
            half_open_max_calls=1,
            sliding_window_size=5,
        )
        create_breaker_with_config(dispatcher, adapter_key, config)

        def failing_task() -> Mapping[str, Any]:
            raise RuntimeError("Adapter failure")

        assert dispatcher.get_circuit_state(adapter_key) == ECircuitState.CLOSED

        tasks = [failing_task]
        dispatcher.execute_with_circuit_breaker(adapter_key, tasks)
        assert dispatcher.get_circuit_state(adapter_key) == ECircuitState.CLOSED

        tasks = [failing_task]
        dispatcher.execute_with_circuit_breaker(adapter_key, tasks)
        assert dispatcher.get_circuit_state(adapter_key) == ECircuitState.OPEN

        time.sleep(0.4)
        assert dispatcher.get_circuit_state(adapter_key) == ECircuitState.HALF_OPEN

        def success_task() -> Mapping[str, Any]:
            return {"status": "ok"}

        tasks = [success_task]
        dispatcher.execute_with_circuit_breaker(adapter_key, tasks)
        assert dispatcher.get_circuit_state(adapter_key) == ECircuitState.CLOSED
