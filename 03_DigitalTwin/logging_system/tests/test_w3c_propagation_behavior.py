"""
Unit tests for W3C Trace Context propagation in Py_LoggingSystem.

Tests the W3CTraceContextPropagator functionality for distributed tracing.
"""

import pytest

from logging_system.observability.tracing.propagation import W3CTraceContextPropagator
from logging_system.observability.tracing.types import SpanContext


class TestW3CTraceContextPropagator:
    """Test W3C Trace Context propagator."""

    def setup_method(self):
        """Set up test method."""
        self.propagator = W3CTraceContextPropagator()

    def test_inject_creates_traceparent_header(self):
        """Test that inject_context creates proper traceparent header."""
        # Create a valid span context
        context = SpanContext(
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            span_id="00f067aa0ba902b7",
            trace_flags=1
        )

        headers = self.propagator.inject_context(context)

        assert W3CTraceContextPropagator.TRACEPARENT_HEADER in headers
        traceparent = headers[W3CTraceContextPropagator.TRACEPARENT_HEADER]

        # Should match W3C format: 00-{trace-id}-{span-id}-{flags}
        expected = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        assert traceparent == expected

    def test_inject_with_zero_flags(self):
        """Test inject_context with zero trace flags."""
        context = SpanContext(
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            span_id="00f067aa0ba902b7",
            trace_flags=0
        )

        headers = self.propagator.inject_context(context)
        traceparent = headers[W3CTraceContextPropagator.TRACEPARENT_HEADER]

        # Flags should be formatted as 2-digit hex (00)
        assert traceparent.endswith("-00")

    def test_inject_validation_invalid_trace_id(self):
        """Test that inject_context validates trace ID format."""
        context = SpanContext(
            trace_id="invalid-trace-id",  # Not 32 hex chars
            span_id="00f067aa0ba902b7"
        )

        with pytest.raises(ValueError, match="trace_id must be exactly 32 hexadecimal characters"):
            self.propagator.inject_context(context)

    def test_inject_validation_invalid_span_id(self):
        """Test that inject_context validates span ID format."""
        context = SpanContext(
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            span_id="invalid-span"  # Not 16 hex chars
        )

        with pytest.raises(ValueError, match="span_id must be exactly 16 hexadecimal characters"):
            self.propagator.inject_context(context)

    def test_inject_validation_empty_trace_id(self):
        """Test that inject_context rejects empty trace ID."""
        # Since SpanContext validates in __post_init__, we test that validation happens
        # by creating a mock SpanContext that bypasses validation
        from unittest.mock import Mock

        mock_context = Mock()
        mock_context.trace_id = ""
        mock_context.span_id = "00f067aa0ba902b7"

        with pytest.raises(ValueError, match="trace_id must be a non-empty string"):
            self.propagator.inject_context(mock_context)

    def test_inject_validation_empty_span_id(self):
        """Test that inject_context rejects empty span ID."""
        # Since SpanContext validates in __post_init__, we test that validation happens
        # by creating a mock SpanContext that bypasses validation
        from unittest.mock import Mock

        mock_context = Mock()
        mock_context.trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
        mock_context.span_id = ""

        with pytest.raises(ValueError, match="span_id must be a non-empty string"):
            self.propagator.inject_context(mock_context)

    def test_extract_valid_traceparent(self):
        """Test extracting context from valid traceparent header."""
        headers = {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        }

        context = self.propagator.extract_context(headers)

        assert context is not None
        assert context.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
        assert context.span_id == "00f067aa0ba902b7"
        assert context.trace_flags == 1
        assert context.trace_state == {}

    def test_extract_traceparent_with_zero_flags(self):
        """Test extracting context with zero flags."""
        headers = {
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00"
        }

        context = self.propagator.extract_context(headers)

        assert context is not None
        assert context.trace_flags == 0

    def test_extract_missing_header(self):
        """Test extract_context with missing traceparent header."""
        headers = {"content-type": "application/json"}

        context = self.propagator.extract_context(headers)

        assert context is None

    def test_extract_empty_headers(self):
        """Test extract_context with empty headers."""
        context = self.propagator.extract_context({})

        assert context is None

    def test_extract_invalid_traceparent_version(self):
        """Test extract_context rejects unsupported traceparent version."""
        headers = {
            "traceparent": "01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        }

        context = self.propagator.extract_context(headers)

        assert context is None

    def test_extract_invalid_traceparent_format(self):
        """Test extract_context handles malformed traceparent headers."""
        invalid_headers = [
            "traceparent",  # No value
            "",  # Empty
            "not-a-traceparent",  # Invalid format
            "00-invalid-trace-id-00f067aa0ba902b7-01",  # Invalid trace ID
            "00-4bf92f3577b34da6a3ce929d0e0e4736-invalid-span-01",  # Invalid span ID
            "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-invalid",  # Invalid flags
            "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01-extra",  # Too many parts
            "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7",  # Missing flags
        ]

        for header_value in invalid_headers:
            headers = {"traceparent": header_value}
            context = self.propagator.extract_context(headers)
            assert context is None, f"Should reject invalid header: {header_value}"

    def test_extract_case_insensitive_header_name(self):
        """Test that header name matching is case-insensitive."""
        headers = {
            "TRACEPARENT": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        }

        context = self.propagator.extract_context(headers)

        assert context is not None

    def test_extract_whitespace_handling(self):
        """Test that extract_context handles whitespace in header value."""
        headers = {
            "traceparent": "  00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01  "
        }

        context = self.propagator.extract_context(headers)

        assert context is not None
        assert context.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"

    def test_trace_id_format_validation(self):
        """Test trace ID format validation."""
        # Valid trace IDs
        valid_trace_ids = [
            "4bf92f3577b34da6a3ce929d0e0e4736",
            "00000000000000000000000000000000",
            "ffffffffffffffffffffffffffffffff",
            "1234567890abcdef1234567890abcdef"
        ]

        for trace_id in valid_trace_ids:
            assert self.propagator._is_valid_trace_id(trace_id), f"Should accept valid trace ID: {trace_id}"

        # Invalid trace IDs
        invalid_trace_ids = [
            "",  # Empty
            "4bf92f3577b34da6a3ce929d0e0e473",  # Too short
            "4bf92f3577b34da6a3ce929d0e0e47366",  # Too long
            "4bf92f3577b34da6a3ce929d0e0e473g",  # Invalid character
            "4bf92f3577b34da6a3ce929d0e0e473-",  # Invalid character
        ]

        for trace_id in invalid_trace_ids:
            assert not self.propagator._is_valid_trace_id(trace_id), f"Should reject invalid trace ID: {trace_id}"

    def test_span_id_format_validation(self):
        """Test span ID format validation."""
        # Valid span IDs
        valid_span_ids = [
            "00f067aa0ba902b7",
            "0000000000000000",
            "ffffffffffffffff",
            "1234567890abcdef"
        ]

        for span_id in valid_span_ids:
            assert self.propagator._is_valid_span_id(span_id), f"Should accept valid span ID: {span_id}"

        # Invalid span IDs
        invalid_span_ids = [
            "",  # Empty
            "00f067aa0ba902b",  # Too short
            "00f067aa0ba902b77",  # Too long
            "00f067aa0ba902bg",  # Invalid character
            "00f067aa0ba902b-",  # Invalid character
        ]

        for span_id in invalid_span_ids:
            assert not self.propagator._is_valid_span_id(span_id), f"Should reject invalid span ID: {span_id}"

    def test_generate_trace_id(self):
        """Test trace ID generation."""
        trace_id = W3CTraceContextPropagator.generate_trace_id()

        assert isinstance(trace_id, str)
        assert len(trace_id) == 32
        assert self.propagator._is_valid_trace_id(trace_id)

    def test_generate_span_id(self):
        """Test span ID generation."""
        span_id = W3CTraceContextPropagator.generate_span_id()

        assert isinstance(span_id, str)
        assert len(span_id) == 16
        assert self.propagator._is_valid_span_id(span_id)

    def test_create_new_span_context(self):
        """Test creating new span context."""
        context = W3CTraceContextPropagator.create_new_span_context()

        assert isinstance(context, SpanContext)
        assert self.propagator._is_valid_trace_id(context.trace_id)
        assert self.propagator._is_valid_span_id(context.span_id)
        assert context.trace_flags == 0
        assert context.trace_state == {}

    def test_create_child_span_context(self):
        """Test creating child span context."""
        parent = SpanContext(
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            span_id="00f067aa0ba902b7",
            trace_flags=1,
            trace_state={"key": "value"}
        )

        child = W3CTraceContextPropagator.create_child_span_context(parent)

        assert child.trace_id == parent.trace_id  # Same trace
        assert child.span_id != parent.span_id    # Different span
        assert self.propagator._is_valid_span_id(child.span_id)
        assert child.trace_flags == parent.trace_flags
        assert child.trace_state == parent.trace_state

    def test_inject_extract_roundtrip(self):
        """Test that inject -> extract preserves context."""
        original_context = SpanContext(
            trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            span_id="00f067aa0ba902b7",
            trace_flags=1,
            trace_state={"vendor": "value"}
        )

        # Inject into headers
        headers = self.propagator.inject_context(original_context)

        # Extract back from headers
        extracted_context = self.propagator.extract_context(headers)

        assert extracted_context is not None
        assert extracted_context.trace_id == original_context.trace_id
        assert extracted_context.span_id == original_context.span_id
        assert extracted_context.trace_flags == original_context.trace_flags
        # Note: trace_state is not preserved in W3C traceparent header
        assert extracted_context.trace_state == {}