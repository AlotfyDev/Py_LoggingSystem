from collections.abc import Mapping
from typing import Any

import pytest

from logging_system.dispatch import DispatcherWithErrorHandling
from logging_system.errors import (
    CircuitBreakerOpenError,
    DLQEntry,
    EDLQStatus,
)
from logging_system.models.record import LogRecord


class TestDispatchDLQIntegration:
    def test_dispatch_failure_enqueues_dlq(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = LogRecord(
            record_id="test-123",
            payload={"level": "ERROR", "message": "Test error"},
        )

        error = RuntimeError("Adapter connection failed")
        entry = dispatcher.enqueue_to_dlq(record, error, adapter_key)

        assert entry is not None
        assert entry.error_code == "CONNECTION_ERROR"
        assert "Adapter connection failed" in entry.message
        assert entry.status == EDLQStatus.PENDING

    def test_dlq_entry_contains_record(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = LogRecord(
            record_id="test-456",
            payload={"level": "ERROR", "message": "Test message", "extra": "data"},
        )

        error = ValueError("Invalid payload")
        entry = dispatcher.enqueue_to_dlq(record, error, adapter_key)

        assert entry.payload is not None
        assert entry.payload["record_id"] == "test-456"
        assert entry.payload["payload"]["level"] == "ERROR"
        assert entry.payload["payload"]["message"] == "Test message"
        assert entry.payload["payload"]["extra"] == "data"

    def test_dlq_entry_contains_error_context(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = LogRecord(
            record_id="test-789",
            payload={"level": "ERROR", "message": "Test"},
        )

        error = ConnectionError("Could not connect to server")
        context = {"request_id": "req-123", "endpoint": "/api/logs"}
        entry = dispatcher.enqueue_to_dlq(record, error, adapter_key, context=context)

        assert entry.metadata is not None
        assert entry.metadata["adapter_key"] == adapter_key
        assert entry.metadata["error_type"] == "ConnectionError"
        assert "Could not connect to server" in entry.metadata["error_message"]
        assert entry.metadata["context"]["request_id"] == "req-123"
        assert entry.metadata["context"]["endpoint"] == "/api/logs"

    def test_dlq_entry_from_mapping_payload(self):
        dispatcher = DispatcherWithErrorHandling()
        adapter_key = "telemetry.test"

        record = {"level": "WARN", "message": "Warning message", "code": 123}

        error = TimeoutError("Request timed out")
        entry = dispatcher.enqueue_to_dlq(record, error, adapter_key)

        assert entry.payload == record
        assert entry.metadata["error_type"] == "TimeoutError"

    def test_dlq_statistics_available(self):
        dispatcher = DispatcherWithErrorHandling()

        record = LogRecord(record_id="test-1", payload={"level": "ERROR"})
        error = RuntimeError("Error 1")
        dispatcher.enqueue_to_dlq(record, error, "adapter1")

        record = LogRecord(record_id="test-2", payload={"level": "ERROR"})
        error = RuntimeError("Error 2")
        dispatcher.enqueue_to_dlq(record, error, "adapter2")

        stats = dispatcher.get_dlq_statistics()

        assert stats["total_entries"] == 2
        assert stats["pending_entries"] == 2

    def test_get_failed_entries(self):
        dispatcher = DispatcherWithErrorHandling()

        record1 = LogRecord(record_id="test-1", payload={"level": "ERROR"})
        entry1 = dispatcher.enqueue_to_dlq(record1, RuntimeError("Error"), "adapter1")

        record2 = LogRecord(record_id="test-2", payload={"level": "ERROR"})
        entry2 = dispatcher.enqueue_to_dlq(record2, RuntimeError("Error"), "adapter2")

        dispatcher.discard_dlq_entry(entry1.entry_id)

        failed = dispatcher.get_failed_entries()
        pending = dispatcher.get_pending_entries()

        assert len(failed) == 0
        assert len(pending) == 1
        assert pending[0].entry_id == entry2.entry_id

    def test_dlq_metrics_in_evidence(self):
        dispatcher = DispatcherWithErrorHandling()

        record = LogRecord(record_id="test-1", payload={"level": "ERROR"})
        error = RuntimeError("Test error")
        dispatcher.enqueue_to_dlq(record, error, "adapter1")

        evidence = dispatcher.collect_error_handling_evidence()

        assert "dlq_statistics" in evidence
        assert evidence["dlq_statistics"]["total_entries"] == 1
        assert evidence["dlq_failed_count"] == 0
        assert evidence["dlq_pending_count"] == 1

    def test_circuit_breaker_and_dlq_together(self):
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

        def failing_task() -> Mapping[str, Any]:
            raise RuntimeError("Adapter failure")

        results1, errors1 = dispatcher.execute_with_circuit_breaker(adapter_key, [failing_task])
        assert len(errors1) == 1
        assert dispatcher.is_dispatch_allowed(adapter_key)

        results2, errors2 = dispatcher.execute_with_circuit_breaker(adapter_key, [failing_task])
        assert len(errors2) == 1
        assert not dispatcher.is_dispatch_allowed(adapter_key)

        results3, errors3 = dispatcher.execute_with_circuit_breaker(adapter_key, [failing_task])
        assert len(results3) == 0
        assert len(errors3) == 1
        assert isinstance(errors3[0], CircuitBreakerOpenError)

        record = LogRecord(record_id="test-cb", payload={"level": "ERROR"})
        error = errors3[0]
        entry = dispatcher.enqueue_to_dlq(record, error, adapter_key)

        assert entry is not None
        assert entry.metadata["error_type"] == "CircuitBreakerOpenError"

    def test_clear_dlq(self):
        dispatcher = DispatcherWithErrorHandling()

        for i in range(3):
            record = LogRecord(record_id=f"test-{i}", payload={"level": "ERROR"})
            error = RuntimeError(f"Error {i}")
            dispatcher.enqueue_to_dlq(record, error, "adapter1")

        stats = dispatcher.get_dlq_statistics()
        assert stats["total_entries"] == 3

        count = dispatcher.clear_dlq()
        assert count == 3

        stats = dispatcher.get_dlq_statistics()
        assert stats["total_entries"] == 0


class TestDLQErrorClassification:
    def test_circuit_open_classification(self):
        dispatcher = DispatcherWithErrorHandling()

        record = LogRecord(record_id="test-1", payload={"level": "ERROR"})
        error = CircuitBreakerOpenError(
            circuit_name="test-adapter",
            state=dispatcher.get_circuit_state("test-adapter"),
        )
        entry = dispatcher.enqueue_to_dlq(record, error, "test-adapter")

        assert entry.error_code == "CIRCUIT_OPEN"

    def test_timeout_classification(self):
        dispatcher = DispatcherWithErrorHandling()

        record = LogRecord(record_id="test-1", payload={"level": "ERROR"})
        error = TimeoutError("Request timed out after 30s")
        entry = dispatcher.enqueue_to_dlq(record, error, "test-adapter")

        assert entry.error_code == "TIMEOUT"

    def test_connection_error_classification(self):
        dispatcher = DispatcherWithErrorHandling()

        record = LogRecord(record_id="test-1", payload={"level": "ERROR"})
        error = ConnectionError("Connection refused by server")
        entry = dispatcher.enqueue_to_dlq(record, error, "test-adapter")

        assert entry.error_code == "CONNECTION_ERROR"

    def test_auth_error_classification(self):
        dispatcher = DispatcherWithErrorHandling()

        record = LogRecord(record_id="test-1", payload={"level": "ERROR"})
        error = PermissionError("Permission denied - invalid API key")
        entry = dispatcher.enqueue_to_dlq(record, error, "test-adapter")

        assert entry.error_code == "AUTH_ERROR"

    def test_generic_error_classification(self):
        dispatcher = DispatcherWithErrorHandling()

        record = LogRecord(record_id="test-1", payload={"level": "ERROR"})
        error = ValueError("Invalid input provided")
        entry = dispatcher.enqueue_to_dlq(record, error, "test-adapter")

        assert entry.error_code == "ERROR_VALUEERROR"
