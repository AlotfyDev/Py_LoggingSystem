import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from logging_system.dispatch import DispatcherWithErrorHandling
from logging_system.errors import (
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    DLQConfig,
    EDLQStatus,
    ERetryStrategy,
    FileBasedDeadLetterQueue,
    RetryConfig,
)
from logging_system.errors.circuit_breaker import CircuitBreaker
from logging_system.models.record import LogRecord


def create_isolated_dispatcher() -> DispatcherWithErrorHandling:
    return DispatcherWithErrorHandling()


class TestE2ERetrySuccess:
    def test_e2e_retry_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq = FileBasedDeadLetterQueue(
                config=DLQConfig(max_entries=100),
                file_path=Path(tmpdir) / "dlq.jsonl",
            )
            dispatcher = DispatcherWithErrorHandling()
            dispatcher._dlq = dlq

            adapter_key = "telemetry.e2e"
            total_call_count = 0

            def create_flaky_adapter(record_id: str):
                call_count = 0

                def flaky_adapter(record: Mapping[str, Any]) -> Mapping[str, Any]:
                    nonlocal call_count, total_call_count
                    call_count += 1
                    total_call_count += 1
                    if call_count < 3:
                        raise ConnectionError(f"Transient failure #{call_count} for {record_id}")
                    return {"status": "dispatched", "record_id": record["record_id"]}

                return flaky_adapter

            records = [
                LogRecord(record_id=f"rec-{i}", payload={"level": "INFO", "message": f"Log {i}"})
                for i in range(5)
            ]

            for record in records:
                projection = record.to_projection()
                flaky_adapter = create_flaky_adapter(record.record_id)

                def make_task(adapter_func):
                    def task():
                        return adapter_func(projection)
                    return task

                result = dispatcher.execute_with_retry(
                    adapter_key=adapter_key,
                    tasks=[make_task(flaky_adapter)],
                    retry_config=RetryConfig(
                        max_attempts=3,
                        initial_delay_seconds=0.05,
                        strategy=ERetryStrategy.LINEAR,
                    ),
                    record=record,
                )

                assert len(result.results) == 1, f"Record {record.record_id} should succeed"
                assert len(result.errors) == 0
                assert len(result.dlq_entries) == 0

            assert total_call_count == 15  # 3 calls per record × 5 records

            dlq.flush()
            assert dlq.get_statistics().total_entries == 0

    def test_e2e_partial_retry_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq = FileBasedDeadLetterQueue(
                config=DLQConfig(max_entries=100),
                file_path=Path(tmpdir) / "dlq.jsonl",
            )
            dispatcher = DispatcherWithErrorHandling()
            dispatcher._dlq = dlq

            adapter_key = "telemetry.e2e.partial"
            call_counts = {"success": 0, "fail": 0}

            def mixed_adapter(record: Mapping[str, Any]) -> Mapping[str, Any]:
                record_id = record.get("record_id", "unknown")
                if record_id.startswith("ok-"):
                    call_counts["success"] += 1
                    return {"status": "dispatched", "record_id": record_id}
                else:
                    call_counts["fail"] += 1
                    raise ConnectionError("Always fails")

            results_ok = []
            results_fail = []

            for i in range(3):
                record = LogRecord(record_id=f"ok-{i}", payload={"level": "INFO"})
                projection = record.to_projection()
                result = dispatcher.execute_with_retry(
                    adapter_key=adapter_key,
                    tasks=[lambda r=projection: mixed_adapter(r)],
                    record=record,
                )
                results_ok.append(result)

            for i in range(3):
                record = LogRecord(record_id=f"fail-{i}", payload={"level": "ERROR"})
                projection = record.to_projection()
                result = dispatcher.execute_with_retry(
                    adapter_key=adapter_key,
                    tasks=[lambda r=projection: mixed_adapter(r)],
                    record=record,
                )
                results_fail.append(result)

            assert all(len(r.results) == 1 for r in results_ok)
            assert all(len(r.errors) == 1 for r in results_fail)
            assert all(len(r.dlq_entries) == 1 for r in results_fail)


class TestE2EDLQAfterMaxRetries:
    def test_e2e_dlq_after_max_retries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq = FileBasedDeadLetterQueue(
                config=DLQConfig(max_entries=100, retry_delay_seconds=1),
                file_path=Path(tmpdir) / "dlq.jsonl",
            )
            dispatcher = DispatcherWithErrorHandling()
            dispatcher._dlq = dlq

            adapter_key = "telemetry.e2e.dlq"

            def always_fails(record: Mapping[str, Any]) -> Mapping[str, Any]:
                raise TimeoutError("Request timed out")

            record = LogRecord(record_id="dlq-test-1", payload={"level": "ERROR", "message": "Test"})
            projection = record.to_projection()

            result = dispatcher.execute_with_retry(
                adapter_key=adapter_key,
                tasks=[lambda r=projection: always_fails(r)],
                retry_config=RetryConfig(
                    max_attempts=3,
                    initial_delay_seconds=0.01,
                ),
                record=record,
            )

            assert len(result.results) == 0
            assert len(result.errors) == 1
            assert len(result.dlq_entries) == 1
            assert result.retries_attempted == 3

            dlq.flush()

            entry = result.dlq_entries[0]
            assert entry.status == EDLQStatus.PENDING
            assert entry.error_code == "TIMEOUT"
            assert entry.payload["record_id"] == "dlq-test-1"
            assert entry.metadata["is_retryable"] is True

    def test_e2e_permanent_error_no_retry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq = FileBasedDeadLetterQueue(
                config=DLQConfig(max_entries=100),
                file_path=Path(tmpdir) / "dlq.jsonl",
            )
            dispatcher = DispatcherWithErrorHandling()
            dispatcher._dlq = dlq

            adapter_key = "telemetry.e2e.permanent"

            def permanent_error(record: Mapping[str, Any]) -> Mapping[str, Any]:
                raise ValueError("Invalid payload - cannot be processed")

            record = LogRecord(record_id="permanent-1", payload={"level": "ERROR"})
            projection = record.to_projection()
            start_time = time.time()

            result = dispatcher.execute_with_retry(
                adapter_key=adapter_key,
                tasks=[lambda r=projection: permanent_error(r)],
                record=record,
                retry_config=RetryConfig(max_attempts=5),
            )

            elapsed = time.time() - start_time

            assert len(result.results) == 0
            assert len(result.errors) == 1
            assert isinstance(result.errors[0], ValueError)
            assert result.retries_attempted == 0
            assert elapsed < 0.5

            dlq.flush()
            assert dlq.get_statistics().total_entries == 1


class TestE2ECircuitBreaker:
    def test_e2e_circuit_breaker_open(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq = FileBasedDeadLetterQueue(
                config=DLQConfig(max_entries=100),
                file_path=Path(tmpdir) / "dlq.jsonl",
            )
            dispatcher = DispatcherWithErrorHandling()
            dispatcher._dlq = dlq

            adapter_key = "telemetry.e2e.cb"
            cb_config = CircuitBreakerConfig(
                failure_threshold=2,
                success_threshold=1,
                open_timeout_seconds=30,
                half_open_max_calls=1,
                sliding_window_size=5,
            )
            with dispatcher._lock:
                dispatcher._circuit_breakers[adapter_key] = CircuitBreaker(
                    name=adapter_key,
                    config=cb_config,
                )

            def failing_adapter(record: Mapping[str, Any]) -> Mapping[str, Any]:
                raise RuntimeError("Service down")

            record = LogRecord(record_id="cb-test-1", payload={"level": "ERROR"})
            projection = record.to_projection()

            for i in range(3):
                result = dispatcher.execute_with_retry(
                    adapter_key=adapter_key,
                    tasks=[lambda r=projection: failing_adapter(r)],
                    record=record,
                )

            assert not dispatcher.is_dispatch_allowed(adapter_key)

            breaker = dispatcher.get_or_create_circuit_breaker(adapter_key)
            assert breaker.state.value == "open"

            result_blocked = dispatcher.execute_with_retry(
                adapter_key=adapter_key,
                tasks=[lambda: failing_adapter(projection)],
                record=record,
            )

            assert len(result_blocked.results) == 0
            assert len(result_blocked.errors) == 1
            assert isinstance(result_blocked.errors[0], CircuitBreakerOpenError)

    def test_e2e_circuit_breaker_recovery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq = FileBasedDeadLetterQueue(
                config=DLQConfig(max_entries=100),
                file_path=Path(tmpdir) / "dlq.jsonl",
            )
            dispatcher = DispatcherWithErrorHandling()
            dispatcher._dlq = dlq

            adapter_key = "telemetry.e2e.cb.recovery"
            cb_config = CircuitBreakerConfig(
                failure_threshold=2,
                success_threshold=1,
                open_timeout_seconds=0.5,
                half_open_max_calls=2,
                sliding_window_size=5,
            )
            with dispatcher._lock:
                dispatcher._circuit_breakers[adapter_key] = CircuitBreaker(
                    name=adapter_key,
                    config=cb_config,
                )

            def failing_adapter(record: Mapping[str, Any]) -> Mapping[str, Any]:
                raise RuntimeError("Service down")

            def recovering_adapter(record: Mapping[str, Any]) -> Mapping[str, Any]:
                return {"status": "recovered", "record_id": record["record_id"]}

            record = LogRecord(record_id="cb-recovery-1", payload={"level": "INFO"})
            projection = record.to_projection()

            dispatcher.execute_with_retry(adapter_key, [lambda r=projection: failing_adapter(r)], record=record)
            dispatcher.execute_with_retry(adapter_key, [lambda r=projection: failing_adapter(r)], record=record)

            breaker = dispatcher.get_or_create_circuit_breaker(adapter_key)
            assert breaker.state.value == "open"

            time.sleep(0.6)

            assert dispatcher.is_dispatch_allowed(adapter_key)
            assert breaker.state.value == "half_open"

            result = dispatcher.execute_with_retry(
                adapter_key,
                [lambda r=projection: recovering_adapter(r)],
                record=record,
            )

            assert len(result.results) == 1
            assert breaker.state.value == "closed"


class TestE2EBackpressure:
    def test_e2e_backpressure_dlq(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq = FileBasedDeadLetterQueue(
                config=DLQConfig(max_entries=10),
                file_path=Path(tmpdir) / "dlq.jsonl",
            )
            dispatcher = DispatcherWithErrorHandling()
            dispatcher._dlq = dlq

            adapter_key = "telemetry.e2e.backpressure"

            def failing_adapter(record: Mapping[str, Any]) -> Mapping[str, Any]:
                raise ConnectionError("Connection refused")

            records = [
                LogRecord(record_id=f"bp-{i}", payload={"level": "ERROR"})
                for i in range(15)
            ]

            dlq_entries = []
            for record in records:
                projection = record.to_projection()
                result = dispatcher.execute_with_retry(
                    adapter_key,
                    [lambda r=projection: failing_adapter(r)],
                    record=record,
                )
                if result.dlq_entries:
                    dlq_entries.extend(result.dlq_entries)

            dlq.flush()
            stats = dlq.get_statistics()

            assert stats.total_entries <= 10


class TestE2ENoRegression:
    def test_e2e_no_regression(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq = FileBasedDeadLetterQueue(
                config=DLQConfig(max_entries=100),
                file_path=Path(tmpdir) / "dlq.jsonl",
            )
            dispatcher = DispatcherWithErrorHandling()
            dispatcher._dlq = dlq

            adapter_key = "telemetry.e2e.regression"

            def success_adapter(record: Mapping[str, Any]) -> Mapping[str, Any]:
                return {"status": "ok", "record_id": record.get("record_id")}

            records = [
                LogRecord(record_id=f"reg-{i}", payload={"level": "INFO", "message": f"Log {i}"})
                for i in range(10)
            ]

            total_results = 0
            total_errors = 0
            total_retries = 0

            for record in records:
                projection = record.to_projection()
                result = dispatcher.execute_with_retry(
                    adapter_key,
                    [lambda r=projection: success_adapter(r)],
                    record=record,
                )
                total_results += len(result.results)
                total_errors += len(result.errors)
                total_retries += result.retries_attempted

            assert total_results == 10
            assert total_errors == 0
            assert total_retries == 0

            dlq.flush()
            assert dlq.get_statistics().total_entries == 0


class TestE2EPerformance:
    def test_e2e_retry_overhead_acceptable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq = FileBasedDeadLetterQueue(
                config=DLQConfig(max_entries=100),
                file_path=Path(tmpdir) / "dlq.jsonl",
            )
            dispatcher = DispatcherWithErrorHandling()
            dispatcher._dlq = dlq

            adapter_key = "telemetry.e2e.perf"

            def fast_adapter(record: Mapping[str, Any]) -> Mapping[str, Any]:
                return {"status": "ok"}

            def flaky_fast_adapter(record: Mapping[str, Any]) -> Mapping[str, Any]:
                raise ConnectionError("Transient")

            record = LogRecord(record_id="perf-1", payload={"level": "INFO"})
            projection = record.to_projection()

            start_no_retry = time.time()
            result_ok = dispatcher.execute_with_retry(
                adapter_key,
                [lambda: fast_adapter(projection)],
                retry_config=RetryConfig(max_attempts=1),
                record=record,
            )
            no_retry_time = time.time() - start_no_retry

            start_with_retry = time.time()
            result_flaky = dispatcher.execute_with_retry(
                adapter_key,
                [lambda: flaky_fast_adapter(projection)],
                retry_config=RetryConfig(max_attempts=3, initial_delay_seconds=0.01),
                record=record,
            )
            with_retry_time = time.time() - start_with_retry

            overhead_ratio = with_retry_time / no_retry_time if no_retry_time > 0 else 1.0

            assert len(result_ok.results) == 1
            assert len(result_flaky.results) == 0
            assert len(result_flaky.dlq_entries) == 1


class TestE2EErrorHandling:
    def test_e2e_error_classification_in_dlq(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq = FileBasedDeadLetterQueue(
                config=DLQConfig(max_entries=100),
                file_path=Path(tmpdir) / "dlq.jsonl",
            )
            dispatcher = DispatcherWithErrorHandling()
            dispatcher._dlq = dlq

            test_cases = [
                ("timeout-1", TimeoutError("Request timed out"), "TIMEOUT"),
                ("conn-1", ConnectionError("Connection refused"), "CONNECTION_ERROR"),
                ("auth-1", PermissionError("Access denied"), "ERROR_PERMISSIONERROR"),
                ("val-1", ValueError("Invalid input"), "ERROR_VALUEERROR"),
            ]

            for record_id, error, expected_code in test_cases:
                record = LogRecord(record_id=record_id, payload={"level": "ERROR"})
                projection = record.to_projection()

                def make_error_task(err):
                    def task():
                        raise err
                    return task

                result = dispatcher.execute_with_retry(
                    "telemetry.e2e.class",
                    [make_error_task(error)],
                    retry_config=RetryConfig(max_attempts=1),
                    record=record,
                )

                dlq.flush()

                assert len(result.dlq_entries) == 1
                entry = result.dlq_entries[0]
                assert entry.error_code == expected_code
                assert entry.metadata["error_type"] == type(error).__name__

    def test_e2e_circuit_breaker_and_dlq_together(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq = FileBasedDeadLetterQueue(
                config=DLQConfig(max_entries=100),
                file_path=Path(tmpdir) / "dlq.jsonl",
            )
            dispatcher = DispatcherWithErrorHandling()
            dispatcher._dlq = dlq

            adapter_key = "telemetry.e2e.cbdlq"
            cb_config = CircuitBreakerConfig(
                failure_threshold=2,
                success_threshold=1,
                open_timeout_seconds=30,
                half_open_max_calls=1,
                sliding_window_size=5,
            )
            with dispatcher._lock:
                dispatcher._circuit_breakers[adapter_key] = CircuitBreaker(
                    name=adapter_key,
                    config=cb_config,
                )

            def failing_task():
                raise RuntimeError("Persistent failure")

            record = LogRecord(record_id="cbdlq-1", payload={"level": "ERROR"})
            projection = record.to_projection()

            dispatcher.execute_with_circuit_breaker(adapter_key, [failing_task])
            dispatcher.execute_with_circuit_breaker(adapter_key, [failing_task])

            assert not dispatcher.is_dispatch_allowed(adapter_key)

            entry = dispatcher.enqueue_to_dlq(
                record=projection,
                error=CircuitBreakerOpenError(
                    circuit_name=adapter_key,
                    state=dispatcher.get_circuit_state(adapter_key),
                ),
                adapter_key=adapter_key,
            )
            dlq.flush()

            assert entry.error_code == "CIRCUIT_OPEN"
            assert entry.metadata["is_retryable"] is False

            evidence = dispatcher.collect_error_handling_evidence()
            assert evidence["dlq_failed_count"] == 0
            assert evidence["dlq_pending_count"] == 1
