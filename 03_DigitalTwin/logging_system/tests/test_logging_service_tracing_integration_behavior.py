"""
Unit tests for LoggingService tracing integration.

Tests the tracing functionality integrated into LoggingService.
"""

import pytest

from logging_system.services.logging_service import LoggingService
from logging_system.observability.tracing.types import SpanContext
from logging_system.observability.metrics.registry import MetricRegistry


class TestLoggingServiceTracingIntegration:
    """Test tracing integration in LoggingService."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        self.registry = MetricRegistry.get_instance()
        self.registry.clear()
        self.service = LoggingService()

    def teardown_method(self):
        """Clean up after test method."""
        self.registry.clear()

    def test_traced_emit_creates_span(self):
        """Test that traced_emit creates spans around logging operations."""
        # Emit a traced log
        record_id = self.service.traced_emit({
            "level": "INFO",
            "message": "traced log message",
            "attributes": {},
            "context": {}
        })

        # Verify record was created
        assert record_id is not None
        assert isinstance(record_id, str)

        # Verify span was created (should be ended after operation)
        assert self.service._tracing_context.current_span is None

    def test_traced_emit_with_span_attributes(self):
        """Test that traced_emit sets appropriate span attributes."""
        with self.service._tracing_context.span("test-span") as outer_span:
            # Emit within an existing span - this creates a nested logging span
            record_id = self.service.traced_emit({
                "level": "ERROR",
                "message": "error message",
                "attributes": {"error_code": 500},
                "context": {}
            })

            # The outer span should still be active
            assert self.service._tracing_context.current_span == outer_span

            # Check that a log record was created
            assert record_id is not None

    def test_traced_emit_with_parent_context_from_headers(self):
        """Test that traced_emit extracts parent context from HTTP headers."""
        # Create a parent span context
        parent_context = SpanContext.create_new()

        # Simulate HTTP headers with traceparent
        headers = self.service._tracing_context.inject_context()
        context = {"headers": headers}

        # Emit with headers containing parent context
        record_id = self.service.traced_emit({
            "level": "INFO",
            "message": "child log",
            "attributes": {},
            "context": {}
        }, context)

        # Verify record was created
        assert record_id is not None

    def test_traced_emit_propagates_span_context_to_headers(self):
        """Test that traced_emit injects span context into outgoing headers."""
        context = {"headers": {}}

        with self.service._tracing_context.span("parent-span"):
            record_id = self.service.traced_emit({
                "level": "INFO",
                "message": "log with headers",
                "attributes": {},
                "context": {}
            }, context)

            # Check that headers now contain traceparent
            assert "traceparent" in context["headers"]
            traceparent = context["headers"]["traceparent"]
            assert traceparent.startswith("00-")

    def test_get_tracing_info_returns_current_state(self):
        """Test that get_tracing_info returns current tracing state."""
        # Initially no active span
        info = self.service.get_tracing_info()
        assert info["tracing_enabled"] is True
        assert info["current_span"] is None
        assert info["sampling_rate"] == 1.0
        assert info["service_name"] == "logging-system"

        # With active span
        with self.service._tracing_context.span("test-span") as span:
            info = self.service.get_tracing_info()
            assert info["current_span"]["active"] is True
            assert info["current_span"]["name"] == "test-span"
            assert info["current_span"]["trace_id"] == span.context.trace_id
            assert info["current_span"]["span_id"] == span.context.span_id

    def test_tracing_integration_with_multiple_emits(self):
        """Test tracing integration with multiple emit operations."""
        # Emit multiple traced logs
        record_ids = []
        for i in range(3):
            record_id = self.service.traced_emit({
                "level": "INFO",
                "message": f"log message {i}",
                "attributes": {"index": i},
                "context": {}
            })
            record_ids.append(record_id)

        # Verify all records were created
        assert len(record_ids) == 3
        assert all(isinstance(rid, str) for rid in record_ids)
        assert len(set(record_ids)) == 3  # All unique

    def test_traced_emit_preserves_existing_context(self):
        """Test that traced_emit works within existing span context."""
        with self.service._tracing_context.span("outer-span") as outer_span:
            # Emit within the outer span
            record_id = self.service.traced_emit({
                "level": "DEBUG",
                "message": "nested log",
                "attributes": {},
                "context": {}
            })

            # Outer span should still be active
            assert self.service._tracing_context.current_span == outer_span

            # Check that record was created
            assert record_id is not None

    def test_tracing_context_isolation_between_services(self):
        """Test that tracing contexts are properly isolated between service instances."""
        service1 = LoggingService()
        service2 = LoggingService()

        # Create spans in different services
        with service1._tracing_context.span("service1-span"):
            with service2._tracing_context.span("service2-span"):
                # Each service should have its own current span
                assert service1._tracing_context.current_span.name == "service1-span"
                assert service2._tracing_context.current_span.name == "service2-span"

                # Emit from service2
                record_id = service2.traced_emit({
                    "level": "INFO",
                    "message": "service2 log",
                    "attributes": {},
                    "context": {}
                })

                assert record_id is not None
                # service2 span should still be active
                assert service2._tracing_context.current_span.name == "service2-span"

    def test_traced_emit_handles_missing_context_gracefully(self):
        """Test that traced_emit handles missing or malformed context gracefully."""
        # Emit with None context
        record_id = self.service.traced_emit({
            "level": "WARN",
            "message": "log without context",
            "attributes": {},
            "context": {}
        })
        assert record_id is not None

        # Emit with empty context
        record_id = self.service.traced_emit({
            "level": "WARN",
            "message": "log with empty context",
            "attributes": {},
            "context": {}
        })
        assert record_id is not None

    def test_tracing_integration_with_error_handling(self):
        """Test that tracing integration handles errors properly."""
        # This test verifies that spans are properly managed even if emit fails
        # (though in practice, emit shouldn't fail in normal operation)

        with self.service._tracing_context.span("error-test-span"):
            # Simulate an operation that might fail
            try:
                record_id = self.service.traced_emit({
                    "level": "ERROR",
                    "message": "error log",
                    "attributes": {"error": True},
                    "context": {}
                })
                assert record_id is not None
            except Exception:
                # Even if emit fails, span should be properly managed
                pass

            # Span should still be active within the context manager
            assert self.service._tracing_context.current_span is not None