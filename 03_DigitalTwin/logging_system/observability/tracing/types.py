"""
Distributed tracing types for Py_LoggingSystem.

This module defines the core types and data structures for distributed tracing,
following OpenTelemetry and W3C Trace Context standards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class ESpanKind(Enum):
    """
    Enumeration of span kinds indicating the type of operation represented by a span.

    Based on OpenTelemetry span kinds:
    - INTERNAL: Internal operations within the application
    - SERVER: Server-side handling of a synchronous request
    - CLIENT: Client-side initiation of a synchronous request
    - PRODUCER: Producer of a message (async operation)
    - CONSUMER: Consumer of a message (async operation)
    """
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class ESpanStatus(Enum):
    """
    Enumeration of span status codes indicating the outcome of the operation.

    Based on OpenTelemetry span status:
    - OK: The operation completed successfully
    - ERROR: The operation failed with an error
    - UNSET: The status is not set (default)
    """
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass(frozen=True)
class SpanContext:
    """
    Immutable span context containing trace and span identification.

    The span context is the fundamental data structure for distributed tracing,
    containing the trace ID, span ID, and trace flags that enable correlation
    of operations across service boundaries.

    Attributes:
        trace_id: 64-bit or 128-bit unique identifier for the trace
        span_id: 64-bit unique identifier for this span within the trace
        trace_flags: 8-bit field for trace flags (sampling, etc.)
        trace_state: Vendor-specific trace state as key-value pairs
    """
    trace_id: str
    span_id: str
    trace_flags: int = 0
    trace_state: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate span context fields."""
        if not self.trace_id or not isinstance(self.trace_id, str):
            raise ValueError("trace_id must be a non-empty string")
        if not self.span_id or not isinstance(self.span_id, str):
            raise ValueError("span_id must be a non-empty string")
        if not isinstance(self.trace_flags, int) or self.trace_flags < 0:
            raise ValueError("trace_flags must be a non-negative integer")
        if not isinstance(self.trace_state, dict):
            raise ValueError("trace_state must be a dictionary")

    @classmethod
    def create_new(cls, trace_state: Optional[Dict[str, str]] = None) -> SpanContext:
        """
        Create a new span context with generated trace and span IDs.

        Args:
            trace_state: Optional vendor-specific trace state

        Returns:
            New SpanContext instance
        """
        return cls(
            trace_id=str(uuid4()),
            span_id=str(uuid4()),
            trace_flags=0,
            trace_state=trace_state or {}
        )

    @classmethod
    def from_parent(cls, parent: SpanContext) -> SpanContext:
        """
        Create a new span context as a child of the given parent context.

        Args:
            parent: Parent span context

        Returns:
            New child SpanContext instance
        """
        return cls(
            trace_id=parent.trace_id,  # Same trace
            span_id=str(uuid4()),      # New span ID
            trace_flags=parent.trace_flags,
            trace_state=parent.trace_state.copy()
        )


@dataclass
class Span:
    """
    Span data structure representing a single operation in a distributed trace.

    A span represents a single operation within a trace, containing timing information,
    metadata, and the relationship to parent spans. Spans form the building blocks
    of distributed traces.

    Attributes:
        context: Immutable span context with trace/span IDs
        name: Human-readable name for the span
        kind: Type of span (internal, server, client, etc.)
        start_time: When the span started (UTC)
        end_time: When the span ended (UTC), None if still active
        status: Current status of the span
        attributes: Key-value metadata associated with the span
        events: List of timestamped events within the span
        parent_span_id: ID of parent span, None for root spans
    """
    context: SpanContext
    name: str
    kind: ESpanKind = ESpanKind.INTERNAL
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    status: ESpanStatus = ESpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: list = field(default_factory=list)
    parent_span_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate span fields."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.context, SpanContext):
            raise ValueError("context must be a SpanContext instance")
        if not isinstance(self.kind, ESpanKind):
            raise ValueError("kind must be an ESpanKind enum value")
        if not isinstance(self.status, ESpanStatus):
            raise ValueError("status must be an ESpanStatus enum value")
        if not isinstance(self.attributes, dict):
            raise ValueError("attributes must be a dictionary")

    def is_active(self) -> bool:
        """
        Check if the span is currently active (not ended).

        Returns:
            True if span is active, False if ended
        """
        return self.end_time is None

    def end(self, status: Optional[ESpanStatus] = None) -> None:
        """
        End the span with optional status.

        Args:
            status: Final status of the span (defaults to current status)
        """
        if self.end_time is not None:
            raise RuntimeError("span is already ended")

        if status is not None:
            self.status = status

        self.end_time = datetime.now(timezone.utc)

    def add_attribute(self, key: str, value: Any) -> None:
        """
        Add an attribute to the span.

        Args:
            key: Attribute key
            value: Attribute value
        """
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a timestamped event to the span.

        Args:
            name: Event name
            attributes: Optional event attributes
        """
        event = {
            "name": name,
            "timestamp": datetime.now(timezone.utc),
            "attributes": attributes or {}
        }
        self.events.append(event)

    def set_status(self, status: ESpanStatus) -> None:
        """
        Set the status of the span.

        Args:
            status: New status
        """
        if not isinstance(status, ESpanStatus):
            raise ValueError("status must be an ESpanStatus enum value")
        self.status = status

    def duration_seconds(self) -> Optional[float]:
        """
        Calculate the duration of the span in seconds.

        Returns:
            Duration in seconds, or None if span is still active
        """
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert span to dictionary representation.

        Returns:
            Dictionary containing all span data
        """
        return {
            "context": {
                "trace_id": self.context.trace_id,
                "span_id": self.context.span_id,
                "trace_flags": self.context.trace_flags,
                "trace_state": self.context.trace_state.copy()
            },
            "name": self.name,
            "kind": self.kind.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "attributes": self.attributes.copy(),
            "events": self.events.copy(),
            "parent_span_id": self.parent_span_id,
            "duration_seconds": self.duration_seconds()
        }


@dataclass(frozen=True)
class TraceConfig:
    """
    Configuration for distributed tracing behavior.

    This configuration controls how tracing is performed, including sampling rates,
    maximum span limits, and other tracing-related settings.

    Attributes:
        enabled: Whether tracing is enabled globally
        sampling_rate: Fraction of traces to sample (0.0 to 1.0)
        max_spans_per_trace: Maximum number of spans allowed per trace
        max_attributes_per_span: Maximum number of attributes per span
        max_events_per_span: Maximum number of events per span
        export_timeout_seconds: Timeout for trace export operations
        service_name: Name of the service for trace identification
        service_version: Version of the service
    """
    enabled: bool = True
    sampling_rate: float = 1.0
    max_spans_per_trace: int = 1000
    max_attributes_per_span: int = 128
    max_events_per_span: int = 128
    export_timeout_seconds: float = 30.0
    service_name: str = "logging-system"
    service_version: str = "1.0.0"

    def __post_init__(self) -> None:
        """Validate trace configuration."""
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        if not (0.0 <= self.sampling_rate <= 1.0):
            raise ValueError("sampling_rate must be between 0.0 and 1.0")
        if self.max_spans_per_trace <= 0:
            raise ValueError("max_spans_per_trace must be positive")
        if self.max_attributes_per_span <= 0:
            raise ValueError("max_attributes_per_span must be positive")
        if self.max_events_per_span <= 0:
            raise ValueError("max_events_per_span must be positive")
        if self.export_timeout_seconds <= 0:
            raise ValueError("export_timeout_seconds must be positive")
        if not self.service_name or not isinstance(self.service_name, str):
            raise ValueError("service_name must be a non-empty string")

    def should_sample(self) -> bool:
        """
        Determine if the current trace should be sampled based on sampling rate.

        Returns:
            True if trace should be sampled, False otherwise
        """
        if not self.enabled:
            return False

        import random
        return random.random() < self.sampling_rate