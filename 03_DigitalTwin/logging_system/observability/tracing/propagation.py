"""
W3C Trace Context propagation for Py_LoggingSystem.

This module implements W3C Trace Context header propagation for distributed tracing,
following the W3C Trace Context specification for correlating traces across service boundaries.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from .types import SpanContext


class W3CTraceContextPropagator:
    """
    W3C Trace Context propagator for distributed tracing.

    This class implements the W3C Trace Context specification for propagating
    trace context across service boundaries using HTTP headers. It handles
    the traceparent header format: traceparent: 00-{trace-id}-{span-id}-{flags}

    Key features:
    - Injects trace context into HTTP headers
    - Extracts trace context from HTTP headers
    - Validates trace and span ID formats
    - Handles sampling flags
    """

    # W3C Trace Context header name
    TRACEPARENT_HEADER = "traceparent"

    # W3C Trace Context version (currently "00")
    TRACE_CONTEXT_VERSION = "00"

    # Regular expression for validating traceparent header format
    TRACEPARENT_PATTERN = re.compile(
        r"^" + TRACE_CONTEXT_VERSION + r"-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$",
        re.IGNORECASE
    )

    def inject_context(self, span_context: SpanContext) -> Dict[str, str]:
        """
        Inject span context into W3C Trace Context headers.

        Args:
            span_context: SpanContext to inject

        Returns:
            Dictionary containing traceparent header

        Raises:
            ValueError: If span context contains invalid trace/span IDs
        """
        self._validate_span_context(span_context)

        # Format: traceparent: 00-{trace-id}-{span-id}-{flags}
        traceparent = (
            f"{self.TRACE_CONTEXT_VERSION}-"
            f"{span_context.trace_id}-"
            f"{span_context.span_id}-"
            f"{span_context.trace_flags:02x}"
        )

        return {self.TRACEPARENT_HEADER: traceparent}

    def extract_context(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """
        Extract span context from W3C Trace Context headers.

        Args:
            headers: HTTP headers dictionary

        Returns:
            SpanContext if valid traceparent header found, None otherwise
        """
        # HTTP headers are case-insensitive, so check for the header in any case
        traceparent_value = None
        for header_name, header_value in headers.items():
            if header_name.lower() == self.TRACEPARENT_HEADER:
                traceparent_value = header_value
                break

        if not traceparent_value:
            return None

        return self._parse_traceparent_header(traceparent_value)

    def _validate_span_context(self, span_context: SpanContext) -> None:
        """
        Validate span context for injection.

        Args:
            span_context: SpanContext to validate

        Raises:
            ValueError: If span context is invalid
        """
        if not span_context.trace_id or not isinstance(span_context.trace_id, str):
            raise ValueError("span_context.trace_id must be a non-empty string")

        if not span_context.span_id or not isinstance(span_context.span_id, str):
            raise ValueError("span_context.span_id must be a non-empty string")

        # Validate trace ID format (32 hex characters)
        if not self._is_valid_trace_id(span_context.trace_id):
            raise ValueError(
                f"span_context.trace_id must be exactly 32 hexadecimal characters, "
                f"got: {span_context.trace_id}"
            )

        # Validate span ID format (16 hex characters)
        if not self._is_valid_span_id(span_context.span_id):
            raise ValueError(
                f"span_context.span_id must be exactly 16 hexadecimal characters, "
                f"got: {span_context.span_id}"
            )

    def _parse_traceparent_header(self, header_value: str) -> Optional[SpanContext]:
        """
        Parse W3C traceparent header value.

        Args:
            header_value: traceparent header value

        Returns:
            SpanContext if valid, None otherwise
        """
        if not isinstance(header_value, str):
            return None

        # Remove any whitespace
        header_value = header_value.strip()

        # Match against W3C format
        match = self.TRACEPARENT_PATTERN.match(header_value)
        if not match:
            return None

        trace_id, span_id, flags_hex = match.groups()
        version = self.TRACE_CONTEXT_VERSION

        # Validate that version is supported (currently only "00")
        if version != self.TRACE_CONTEXT_VERSION:
            return None

        # Convert flags from hex to int
        try:
            trace_flags = int(flags_hex, 16)
        except ValueError:
            return None

        # Validate trace and span IDs
        if not self._is_valid_trace_id(trace_id) or not self._is_valid_span_id(span_id):
            return None

        return SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            trace_flags=trace_flags,
            trace_state={}
        )

    def _is_valid_trace_id(self, trace_id: str) -> bool:
        """
        Validate trace ID format (32 hex characters).

        Args:
            trace_id: Trace ID to validate

        Returns:
            True if valid, False otherwise
        """
        if len(trace_id) != 32:
            return False

        # Check that all characters are valid hex digits (case-insensitive)
        try:
            int(trace_id, 16)
            return True
        except ValueError:
            return False

    def _is_valid_span_id(self, span_id: str) -> bool:
        """
        Validate span ID format (16 hex characters).

        Args:
            span_id: Span ID to validate

        Returns:
            True if valid, False otherwise
        """
        if len(span_id) != 16:
            return False

        # Check that all characters are valid hex digits (case-insensitive)
        try:
            int(span_id, 16)
            return True
        except ValueError:
            return False

    @classmethod
    def generate_trace_id(cls) -> str:
        """
        Generate a valid W3C trace ID (32 hex characters).

        Returns:
            New trace ID string
        """
        import uuid
        # Use UUID4 but remove dashes and take first 32 chars of hex representation
        return uuid.uuid4().hex[:32]

    @classmethod
    def generate_span_id(cls) -> str:
        """
        Generate a valid W3C span ID (16 hex characters).

        Returns:
            New span ID string
        """
        import uuid
        # Use UUID4 but take first 16 chars of hex representation
        return uuid.uuid4().hex[:16]

    @classmethod
    def create_new_span_context(cls) -> SpanContext:
        """
        Create a new span context with generated trace and span IDs.

        Returns:
            New SpanContext with valid W3C IDs
        """
        return SpanContext(
            trace_id=cls.generate_trace_id(),
            span_id=cls.generate_span_id(),
            trace_flags=0,
            trace_state={}
        )

    @classmethod
    def create_child_span_context(cls, parent: SpanContext) -> SpanContext:
        """
        Create a child span context from a parent context.

        Args:
            parent: Parent span context

        Returns:
            New child SpanContext
        """
        return SpanContext(
            trace_id=parent.trace_id,  # Same trace
            span_id=cls.generate_span_id(),  # New span ID
            trace_flags=parent.trace_flags,
            trace_state=parent.trace_state.copy()
        )