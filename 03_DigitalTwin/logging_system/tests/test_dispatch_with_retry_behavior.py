import time
from collections.abc import Mapping
from typing import Any

import pytest

from logging_system.dispatch import DispatcherWithErrorHandling
from logging_system.errors import RetryConfig, ERetryStrategy
from logging_system.models.record import LogRecord


class TestDispatchRetry:
    def test_dispatch_retry_on_transient_error(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = LogRecord(record_id="test-1", payload={"level": "ERROR", "message": "Test"})

        call_count = 0

        def flaky_task() -> Mapping[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return {"status": "ok", "attempts": call_count}

        result = dispatcher.execute_with_retry(
            adapter_key=adapter_key,
            tasks=[flaky_task],
            record=record,
        )

        assert len(result.results) == 1
        assert result.results[0]["status"] == "ok"
        assert result.results[0]["attempts"] == 3
        assert len(result.errors) == 0
        assert result.retries_attempted == 2
        assert len(result.dlq_entries) == 0

    def test_dispatch_no_retry_on_permanent_error(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = LogRecord(record_id="test-2", payload={"level": "ERROR", "message": "Test"})

        def permanent_error_task() -> Mapping[str, Any]:
            raise ValueError("Invalid value - cannot be retried")

        result = dispatcher.execute_with_retry(
            adapter_key=adapter_key,
            tasks=[permanent_error_task],
            record=record,
        )

        assert len(result.results) == 0
        assert len(result.errors) == 1
        assert isinstance(result.errors[0], ValueError)
        assert result.retries_attempted == 0
        assert len(result.dlq_entries) == 1

    def test_dispatch_max_retries_exceeded(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = LogRecord(record_id="test-3", payload={"level": "ERROR", "message": "Test"})

        def always_fails() -> Mapping[str, Any]:
            raise ConnectionError("Always fails")

        result = dispatcher.execute_with_retry(
            adapter_key=adapter_key,
            tasks=[always_fails],
            record=record,
            retry_config=RetryConfig(max_attempts=3),
        )

        assert len(result.results) == 0
        assert len(result.errors) == 1
        assert len(result.dlq_entries) == 1
        assert result.retries_attempted == 3

    def test_dispatch_backoff_applied(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = LogRecord(record_id="test-4", payload={"level": "ERROR", "message": "Test"})

        call_times: list[float] = []

        def tracked_task() -> Mapping[str, Any]:
            call_times.append(time.time())
            if len(call_times) < 3:
                raise TimeoutError("Timeout")
            return {"status": "ok"}

        start_time = time.time()
        result = dispatcher.execute_with_retry(
            adapter_key=adapter_key,
            tasks=[tracked_task],
            record=record,
            retry_config=RetryConfig(
                max_attempts=3,
                initial_delay_seconds=0.15,
                strategy=ERetryStrategy.LINEAR,
            ),
        )

        assert len(result.results) == 1

        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            assert delay1 >= 0.05
            assert delay2 >= delay1

    def test_dispatch_retry_count_tracked(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = LogRecord(record_id="test-5", payload={"level": "ERROR", "message": "Test"})

        retry_count = 0

        def retry_tracking_task() -> Mapping[str, Any]:
            nonlocal retry_count
            retry_count += 1
            if retry_count < 2:
                raise ConnectionError("Retry needed")
            return {"status": "ok", "retries": retry_count}

        result = dispatcher.execute_with_retry(
            adapter_key=adapter_key,
            tasks=[retry_tracking_task],
            record=record,
        )

        assert result.retries_attempted == 1
        assert retry_count == 2

        metrics = dispatcher.get_retry_metrics(adapter_key)
        assert metrics[adapter_key] == 1

    def test_dispatch_multiple_tasks_retry_independently(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = LogRecord(record_id="test-6", payload={"level": "ERROR", "message": "Test"})

        call_counts = {"task1": 0, "task2": 0, "task3": 0}

        def task1() -> Mapping[str, Any]:
            call_counts["task1"] += 1
            if call_counts["task1"] < 2:
                raise ConnectionError("Task 1 retry")
            return {"id": "task1", "status": "ok"}

        def task2() -> Mapping[str, Any]:
            call_counts["task2"] += 1
            return {"id": "task2", "status": "ok"}

        def task3() -> Mapping[str, Any]:
            call_counts["task3"] += 1
            raise TimeoutError("Task 3 always times out")

        result = dispatcher.execute_with_retry(
            adapter_key=adapter_key,
            tasks=[task1, task2, task3],
            record=record,
        )

        assert len(result.results) == 2
        assert len(result.errors) == 1
        assert result.retries_attempted >= 2

    def test_dispatch_non_retryable_goes_directly_to_dlq(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = LogRecord(record_id="test-7", payload={"level": "ERROR", "message": "Test"})

        call_count = 0

        def never_retried_task() -> Mapping[str, Any]:
            nonlocal call_count
            call_count += 1
            raise PermissionError("Permission denied")

        start_time = time.time()
        result = dispatcher.execute_with_retry(
            adapter_key=adapter_key,
            tasks=[never_retried_task],
            record=record,
        )
        elapsed = time.time() - start_time

        assert call_count == 1
        assert result.retries_attempted == 0
        assert len(result.dlq_entries) == 1
        assert elapsed < 0.5

    def test_dispatch_circuit_breaker_blocks_retry(self):
        from logging_system.errors import CircuitBreaker, CircuitBreakerConfig

        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=1,
            open_timeout_seconds=30,
            half_open_max_calls=1,
            sliding_window_size=5,
        )
        with dispatcher._lock:
            dispatcher._circuit_breakers[adapter_key] = CircuitBreaker(
                name=adapter_key,
                config=config,
            )

        record = LogRecord(record_id="test-8", payload={"level": "ERROR", "message": "Test"})

        def circuit_breaker_task() -> Mapping[str, Any]:
            raise RuntimeError("Fails to open circuit")

        result1 = dispatcher.execute_with_retry(
            adapter_key=adapter_key,
            tasks=[circuit_breaker_task],
            record=record,
        )
        result2 = dispatcher.execute_with_retry(
            adapter_key=adapter_key,
            tasks=[circuit_breaker_task],
            record=record,
        )

        assert len(result1.results) == 0
        assert len(result2.results) == 0
        assert len(result1.errors) == 1
        assert len(result2.errors) == 1

    def test_dispatch_dlq_entry_contains_retry_info(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = LogRecord(record_id="test-9", payload={"level": "ERROR", "message": "Test"})

        def failing_task() -> Mapping[str, Any]:
            raise ConnectionError("Connection failed")

        result = dispatcher.execute_with_retry(
            adapter_key=adapter_key,
            tasks=[failing_task],
            record=record,
        )

        assert len(result.dlq_entries) == 1
        entry = result.dlq_entries[0]
        assert entry.metadata["adapter_key"] == adapter_key
        assert entry.metadata["is_retryable"] is True
        assert entry.metadata["error_type"] == "ConnectionError"
        assert "context" in entry.metadata
        assert entry.metadata["context"]["retry_count"] == 3


class TestRetryMetrics:
    def test_retry_metrics_accumulate(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        call_count = 0

        def retrying_task() -> Mapping[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Retry")
            return {"status": "ok"}

        for i in range(5):
            record = LogRecord(record_id=f"test-{i}", payload={"level": "ERROR"})
            dispatcher.execute_with_retry(
                adapter_key=adapter_key,
                tasks=[retrying_task],
                record=record,
            )

        metrics = dispatcher.get_retry_metrics(adapter_key)
        assert metrics[adapter_key] >= 1

    def test_retry_metrics_per_adapter(self):
        dispatcher = DispatcherWithErrorHandling()

        call_count = 0

        def retrying_task() -> Mapping[str, Any]:
            nonlocal call_count
            call_count += 1
            if call_count % 3 != 0:
                raise ConnectionError("Retry")
            return {"status": "ok"}

        record = LogRecord(record_id="test-1", payload={"level": "ERROR"})
        dispatcher.execute_with_retry(adapter_key="adapter1", tasks=[retrying_task], record=record)

        record = LogRecord(record_id="test-2", payload={"level": "ERROR"})
        dispatcher.execute_with_retry(adapter_key="adapter2", tasks=[retrying_task], record=record)

        metrics = dispatcher.get_retry_metrics()
        assert "adapter1" in metrics
        assert "adapter2" in metrics
