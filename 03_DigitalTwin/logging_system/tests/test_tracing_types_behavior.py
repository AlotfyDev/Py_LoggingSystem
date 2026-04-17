"""
Unit tests for distributed tracing types in Py_LoggingSystem.

Tests the core tracing types: ESpanKind, ESpanStatus, SpanContext, Span, and TraceConfig.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from logging_system.observability.tracing.types import (
    ESpanKind,
    ESpanStatus,
    SpanContext,
    Span,
    TraceConfig
)


class TestSpanKind:
    """Test ESpanKind enum."""

    def test_span_kind_enum_values(self):
        """Test that all expected span kind values are present."""
        expected_values = {
            "INTERNAL": "internal",
            "SERVER": "server",
            "CLIENT": "client",
            "PRODUCER": "producer",
            "CONSUMER": "consumer"
        }

        assert len(ESpanKind) == 5

        for enum_member, expected_value in expected_values.items():
            assert hasattr(ESpanKind, enum_member)
            assert getattr(ESpanKind, enum_member).value == expected_value

    def test_span_kind_string_representation(self):
        """Test string representation of span kinds."""
        assert str(ESpanKind.INTERNAL) == "ESpanKind.INTERNAL"
        assert ESpanKind.SERVER.value == "server"
        assert ESpanKind.CLIENT.value == "client"


class TestSpanStatus:
    """Test ESpanStatus enum."""

    def test_span_status_enum_values(self):
        """Test that all expected span status values are present."""
        expected_values = {
            "UNSET": "unset",
            "OK": "ok",
            "ERROR": "error"
        }

        assert len(ESpanStatus) == 3

        for enum_member, expected_value in expected_values.items():
            assert hasattr(ESpanStatus, enum_member)
            assert getattr(ESpanStatus, enum_member).value == expected_value

    def test_span_status_string_representation(self):
        """Test string representation of span statuses."""
        assert str(ESpanStatus.OK) == "ESpanStatus.OK"
        assert ESpanStatus.ERROR.value == "error"
        assert ESpanStatus.UNSET.value == "unset"


class TestSpanContext:
    """Test SpanContext frozen dataclass."""

    def test_span_context_creation(self):
        """Test basic SpanContext creation."""
        context = SpanContext(
            trace_id="12345678-1234-5678-9012-123456789012",
            span_id="87654321-4321-8765-2109-876543210987"
        )

        assert context.trace_id == "12345678-1234-5678-9012-123456789012"
        assert context.span_id == "87654321-4321-8765-2109-876543210987"
        assert context.trace_flags == 0
        assert context.trace_state == {}

    def test_span_context_with_flags_and_state(self):
        """Test SpanContext with trace flags and state."""
        trace_state = {"vendor1": "value1", "vendor2": "value2"}

        context = SpanContext(
            trace_id="trace-123",
            span_id="span-456",
            trace_flags=1,
            trace_state=trace_state
        )

        assert context.trace_flags == 1
        assert context.trace_state == trace_state

    def test_span_context_validation(self):
        """Test SpanContext validation."""
        # Empty trace_id
        with pytest.raises(ValueError, match="trace_id must be a non-empty string"):
            SpanContext(trace_id="", span_id="span-123")

        # Empty span_id
        with pytest.raises(ValueError, match="span_id must be a non-empty string"):
            SpanContext(trace_id="trace-123", span_id="")

        # Invalid trace_flags
        with pytest.raises(ValueError, match="trace_flags must be a non-negative integer"):
            SpanContext(trace_id="trace-123", span_id="span-123", trace_flags=-1)

        # Invalid trace_state type
        with pytest.raises(ValueError, match="trace_state must be a dictionary"):
            SpanContext(trace_id="trace-123", span_id="span-123", trace_state="invalid")

    def test_span_context_immutable(self):
        """Test that SpanContext is immutable (frozen)."""
        context = SpanContext(trace_id="trace-123", span_id="span-123")

        with pytest.raises(AttributeError):
            context.trace_id = "new-trace"

        with pytest.raises(AttributeError):
            context.trace_flags = 1

        with pytest.raises(AttributeError):
            context.span_id = "new-span"

    def test_create_new_span_context(self):
        """Test SpanContext.create_new() method."""
        context = SpanContext.create_new()

        assert isinstance(context.trace_id, str)
        assert len(context.trace_id) > 0
        assert isinstance(context.span_id, str)
        assert len(context.span_id) > 0
        assert context.trace_flags == 0
        assert context.trace_state == {}

    def test_create_new_with_trace_state(self):
        """Test SpanContext.create_new() with trace state."""
        trace_state = {"key": "value"}
        context = SpanContext.create_new(trace_state)

        assert context.trace_state == trace_state

    def test_from_parent_span_context(self):
        """Test SpanContext.from_parent() method."""
        parent = SpanContext(
            trace_id="parent-trace",
            span_id="parent-span",
            trace_flags=1,
            trace_state={"parent": "value"}
        )

        child = SpanContext.from_parent(parent)

        assert child.trace_id == parent.trace_id  # Same trace
        assert child.span_id != parent.span_id    # Different span
        assert child.trace_flags == parent.trace_flags
        assert child.trace_state == parent.trace_state  # Copy of state


class TestSpan:
    """Test Span dataclass."""

    def test_span_creation(self):
        """Test basic Span creation."""
        context = SpanContext(trace_id="trace-123", span_id="span-456")
        span = Span(context=context, name="test-span")

        assert span.context == context
        assert span.name == "test-span"
        assert span.kind == ESpanKind.INTERNAL
        assert span.status == ESpanStatus.UNSET
        assert span.attributes == {}
        assert span.events == []
        assert span.parent_span_id is None
        assert span.is_active() is True
        assert span.end_time is None

    def test_span_with_all_fields(self):
        """Test Span creation with all optional fields."""
        context = SpanContext(trace_id="trace-123", span_id="span-456")
        start_time = datetime.now(timezone.utc)

        span = Span(
            context=context,
            name="test-span",
            kind=ESpanKind.SERVER,
            status=ESpanStatus.OK,
            attributes={"key": "value"},
            parent_span_id="parent-123"
        )

        assert span.kind == ESpanKind.SERVER
        assert span.status == ESpanStatus.OK
        assert span.attributes == {"key": "value"}
        assert span.parent_span_id == "parent-123"

    def test_span_validation(self):
        """Test Span validation."""
        context = SpanContext(trace_id="trace-123", span_id="span-456")

        # Empty name
        with pytest.raises(ValueError, match="name must be a non-empty string"):
            Span(context=context, name="")

        # Invalid context
        with pytest.raises(ValueError, match="context must be a SpanContext instance"):
            Span(context="invalid", name="test")

        # Invalid kind
        with pytest.raises(ValueError, match="kind must be an ESpanKind enum value"):
            Span(context=context, name="test", kind="invalid")

        # Invalid status
        with pytest.raises(ValueError, match="status must be an ESpanStatus enum value"):
            Span(context=context, name="test", status="invalid")

        # Invalid attributes
        with pytest.raises(ValueError, match="attributes must be a dictionary"):
            Span(context=context, name="test", attributes="invalid")

    def test_span_lifecycle(self):
        """Test span lifecycle (start, active, end)."""
        context = SpanContext(trace_id="trace-123", span_id="span-456")
        span = Span(context=context, name="test-span")

        # Initially active
        assert span.is_active() is True
        assert span.end_time is None
        assert span.duration_seconds() is None

        # End span
        span.end(ESpanStatus.OK)

        assert span.is_active() is False
        assert span.end_time is not None
        assert span.status == ESpanStatus.OK
        assert span.duration_seconds() is not None
        assert span.duration_seconds() >= 0

    def test_span_end_twice_fails(self):
        """Test that ending a span twice raises an error."""
        context = SpanContext(trace_id="trace-123", span_id="span-456")
        span = Span(context=context, name="test-span")

        span.end(ESpanStatus.OK)

        with pytest.raises(RuntimeError, match="span is already ended"):
            span.end(ESpanStatus.ERROR)

    def test_span_end_without_status_uses_current(self):
        """Test ending span without status uses current status."""
        context = SpanContext(trace_id="trace-123", span_id="span-456")
        span = Span(context=context, name="test-span", status=ESpanStatus.ERROR)

        span.end()

        assert span.status == ESpanStatus.ERROR

    def test_span_add_attribute(self):
        """Test adding attributes to span."""
        context = SpanContext(trace_id="trace-123", span_id="span-456")
        span = Span(context=context, name="test-span")

        span.add_attribute("key1", "value1")
        span.add_attribute("key2", 42)

        assert span.attributes == {"key1": "value1", "key2": 42}

    def test_span_add_event(self):
        """Test adding events to span."""
        context = SpanContext(trace_id="trace-123", span_id="span-456")
        span = Span(context=context, name="test-span")

        span.add_event("event1", {"detail": "info"})
        span.add_event("event2")

        assert len(span.events) == 2
        assert span.events[0]["name"] == "event1"
        assert span.events[0]["attributes"] == {"detail": "info"}
        assert span.events[1]["name"] == "event2"
        assert span.events[1]["attributes"] == {}

        # Events should have timestamps
        assert "timestamp" in span.events[0]
        assert "timestamp" in span.events[1]

    def test_span_set_status(self):
        """Test setting span status."""
        context = SpanContext(trace_id="trace-123", span_id="span-456")
        span = Span(context=context, name="test-span")

        span.set_status(ESpanStatus.OK)
        assert span.status == ESpanStatus.OK

        span.set_status(ESpanStatus.ERROR)
        assert span.status == ESpanStatus.ERROR

    def test_span_set_invalid_status_fails(self):
        """Test that setting invalid status fails."""
        context = SpanContext(trace_id="trace-123", span_id="span-456")
        span = Span(context=context, name="test-span")

        with pytest.raises(ValueError, match="status must be an ESpanStatus enum value"):
            span.set_status("invalid")

    def test_span_to_dict(self):
        """Test converting span to dictionary."""
        context = SpanContext(
            trace_id="trace-123",
            span_id="span-456",
            trace_flags=1,
            trace_state={"key": "value"}
        )

        start_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end_time = start_time + timedelta(seconds=5)

        span = Span(
            context=context,
            name="test-span",
            kind=ESpanKind.SERVER,
            start_time=start_time,
            end_time=end_time,
            status=ESpanStatus.OK,
            attributes={"attr": "value"},
            parent_span_id="parent-123"
        )

        span.add_event("test-event", {"event_attr": "event_value"})

        result = span.to_dict()

        expected = {
            "context": {
                "trace_id": "trace-123",
                "span_id": "span-456",
                "trace_flags": 1,
                "trace_state": {"key": "value"}
            },
            "name": "test-span",
            "kind": "server",
            "start_time": "2023-01-01T12:00:00+00:00",
            "end_time": "2023-01-01T12:00:05+00:00",
            "status": "ok",
            "attributes": {"attr": "value"},
            "events": span.events,  # Will contain the actual event with timestamp
            "parent_span_id": "parent-123",
            "duration_seconds": 5.0
        }

        assert result["context"] == expected["context"]
        assert result["name"] == expected["name"]
        assert result["kind"] == expected["kind"]
        assert result["start_time"] == expected["start_time"]
        assert result["end_time"] == expected["end_time"]
        assert result["status"] == expected["status"]
        assert result["attributes"] == expected["attributes"]
        assert result["parent_span_id"] == expected["parent_span_id"]
        assert result["duration_seconds"] == expected["duration_seconds"]
        assert len(result["events"]) == 1
        assert result["events"][0]["name"] == "test-event"
        assert result["events"][0]["attributes"] == {"event_attr": "event_value"}


class TestTraceConfig:
    """Test TraceConfig dataclass."""

    def test_trace_config_creation(self):
        """Test basic TraceConfig creation."""
        config = TraceConfig()

        assert config.enabled is True
        assert config.sampling_rate == 1.0
        assert config.max_spans_per_trace == 1000
        assert config.max_attributes_per_span == 128
        assert config.max_events_per_span == 128
        assert config.export_timeout_seconds == 30.0
        assert config.service_name == "logging-system"
        assert config.service_version == "1.0.0"

    def test_trace_config_custom_values(self):
        """Test TraceConfig with custom values."""
        config = TraceConfig(
            enabled=False,
            sampling_rate=0.5,
            max_spans_per_trace=500,
            service_name="my-service",
            service_version="2.1.0"
        )

        assert config.enabled is False
        assert config.sampling_rate == 0.5
        assert config.max_spans_per_trace == 500
        assert config.service_name == "my-service"
        assert config.service_version == "2.1.0"

    def test_trace_config_validation(self):
        """Test TraceConfig validation."""
        # Invalid sampling rate
        with pytest.raises(ValueError, match="sampling_rate must be between 0.0 and 1.0"):
            TraceConfig(sampling_rate=1.5)

        with pytest.raises(ValueError, match="sampling_rate must be between 0.0 and 1.0"):
            TraceConfig(sampling_rate=-0.1)

        # Invalid max_spans_per_trace
        with pytest.raises(ValueError, match="max_spans_per_trace must be positive"):
            TraceConfig(max_spans_per_trace=0)

        # Invalid max_attributes_per_span
        with pytest.raises(ValueError, match="max_attributes_per_span must be positive"):
            TraceConfig(max_attributes_per_span=-1)

        # Invalid max_events_per_span
        with pytest.raises(ValueError, match="max_events_per_span must be positive"):
            TraceConfig(max_events_per_span=0)

        # Invalid export_timeout_seconds
        with pytest.raises(ValueError, match="export_timeout_seconds must be positive"):
            TraceConfig(export_timeout_seconds=0)

        # Invalid service_name
        with pytest.raises(ValueError, match="service_name must be a non-empty string"):
            TraceConfig(service_name="")

        # Invalid enabled type
        with pytest.raises(ValueError, match="enabled must be a boolean"):
            TraceConfig(enabled="true")

    def test_trace_config_immutable(self):
        """Test that TraceConfig is immutable (frozen)."""
        config = TraceConfig()

        with pytest.raises(AttributeError):
            config.enabled = False

        with pytest.raises(AttributeError):
            config.sampling_rate = 0.5

    def test_should_sample_enabled_full_rate(self):
        """Test should_sample when enabled with 100% sampling rate."""
        config = TraceConfig(enabled=True, sampling_rate=1.0)

        # Should always return True with 100% sampling
        assert config.should_sample() is True

    def test_should_sample_enabled_half_rate(self):
        """Test should_sample when enabled with 50% sampling rate."""
        config = TraceConfig(enabled=True, sampling_rate=0.5)

        # Should return True roughly 50% of the time over many calls
        results = [config.should_sample() for _ in range(1000)]
        true_count = sum(results)
        # Should be roughly between 450-550 (allowing for randomness)
        assert 400 <= true_count <= 600

    def test_should_sample_disabled(self):
        """Test should_sample when tracing is disabled."""
        config = TraceConfig(enabled=False, sampling_rate=1.0)

        # Should always return False when disabled
        assert config.should_sample() is False