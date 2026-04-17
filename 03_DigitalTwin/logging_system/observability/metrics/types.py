"""
Metric types and data structures for Py_LoggingSystem observability.

This module defines the core types used for metrics collection throughout the system,
following OpenTelemetry and Prometheus metric patterns.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class EMetricType(Enum):
    """Enumeration of supported metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass(frozen=True)
class MetricMetadata:
    """
    Metadata for a metric definition.

    This contains the immutable metadata that defines a metric,
    such as its name, type, description, and unit.
    """

    name: str
    type: EMetricType
    description: str
    unit: Optional[str] = None
    labels: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert this metric metadata to a dictionary representation."""
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "unit": self.unit,
            "labels": self.labels or {},
        }


@dataclass
class MetricValue:
    """
    Base class for all metric values.

    This contains the common attributes shared by all metric value types,
    including timestamp and metadata reference.
    """

    metadata: MetricMetadata
    timestamp: datetime
    value: Any

    def to_dict(self) -> Dict[str, Any]:
        """Convert this metric value to a dictionary representation."""
        return {
            "metadata": self.metadata.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
        }


@dataclass
class CounterValue(MetricValue):
    """
    Value for a counter metric.

    Counters represent monotonically increasing values, typically used for
    counting events, requests, errors, etc.
    """

    value: int  # Monotonically increasing integer

    def __post_init__(self):
        """Validate counter value is non-negative."""
        if self.value < 0:
            raise ValueError("Counter values must be non-negative")

    def increment(self, amount: int = 1) -> 'CounterValue':
        """
        Create a new CounterValue with incremented value.

        Args:
            amount: Amount to increment (default: 1)

        Returns:
            New CounterValue with incremented value
        """
        if amount < 0:
            raise ValueError("Increment amount must be non-negative")

        return CounterValue(
            metadata=self.metadata,
            timestamp=datetime.now(timezone.utc),
            value=self.value + amount
        )


@dataclass
class GaugeValue(MetricValue):
    """
    Value for a gauge metric.

    Gauges represent point-in-time measurements that can go up or down,
    typically used for current values like memory usage, queue size, etc.
    """

    value: float  # Current measurement value

    def update(self, new_value: float) -> 'GaugeValue':
        """
        Create a new GaugeValue with updated value.

        Args:
            new_value: New gauge value

        Returns:
            New GaugeValue with updated value
        """
        return GaugeValue(
            metadata=self.metadata,
            timestamp=datetime.now(timezone.utc),
            value=new_value
        )


@dataclass
class HistogramValue(MetricValue):
    """
    Value for a histogram metric.

    Histograms track the distribution of values, including count, sum,
    and bucketed counts for percentile calculations.
    """

    count: int  # Total number of observations
    sum: float  # Sum of all observed values
    buckets: List[float]  # Bucket boundaries
    bucket_counts: List[int]  # Count in each bucket
    min: Optional[float] = None  # Minimum observed value
    max: Optional[float] = None  # Maximum observed value

    def __post_init__(self):
        """Validate histogram data consistency."""
        if len(self.bucket_counts) != len(self.buckets) + 1:
            raise ValueError("bucket_counts must have one more element than buckets")

        if self.count < 0:
            raise ValueError("Count must be non-negative")

        if any(c < 0 for c in self.bucket_counts):
            raise ValueError("Bucket counts must be non-negative")

    def observe(self, value: float) -> 'HistogramValue':
        """
        Create a new HistogramValue after observing a value.

        Args:
            value: Observed value to add to the histogram

        Returns:
            New HistogramValue with updated observations
        """
        new_count = self.count + 1
        new_sum = self.sum + value
        new_min = min(self.min, value) if self.min is not None else value
        new_max = max(self.max, value) if self.max is not None else value

        # Update bucket counts
        new_bucket_counts = self.bucket_counts.copy()

        # Find the appropriate bucket
        bucket_index = 0
        for i, boundary in enumerate(self.buckets):
            if value <= boundary:
                bucket_index = i
                break
        else:
            bucket_index = len(self.buckets)

        # Increment the appropriate bucket and all higher buckets
        for i in range(bucket_index, len(new_bucket_counts)):
            new_bucket_counts[i] += 1

        return HistogramValue(
            metadata=self.metadata,
            timestamp=datetime.now(timezone.utc),
            value=self.value,  # Keep original value reference
            count=new_count,
            sum=new_sum,
            buckets=self.buckets,
            bucket_counts=new_bucket_counts,
            min=new_min,
            max=new_max
        )

    def percentile(self, p: float) -> Optional[float]:
        """
        Calculate the percentile value from the histogram using linear interpolation.
        Bucket counts are cumulative.

        Args:
            p: Percentile to calculate (0.0 to 100.0)

        Returns:
            The percentile value, or None if insufficient data
        """
        if self.count == 0 or not (0 <= p <= 100):
            return None

        if self.count == 1:
            return self.sum  # Only one observation

        # Find the bucket that contains the percentile
        target_count = (p / 100.0) * self.count

        # bucket_counts are cumulative, so find first i where bucket_counts[i] >= target_count
        for i, cumulative_count in enumerate(self.bucket_counts):
            if cumulative_count >= target_count:
                # Found the bucket containing our percentile
                if i == 0:
                    # In the first bucket (≤ buckets[0])
                    if cumulative_count == 0:
                        return self.min if self.min is not None else 0.0

                    # Linear interpolation within first bucket [0, buckets[0]]
                    bucket_start = 0.0
                    bucket_end = self.buckets[0]
                    prev_cumulative = 0
                    bucket_observations = cumulative_count - prev_cumulative

                    if bucket_observations == 0:
                        return bucket_start

                    fraction = (target_count - prev_cumulative) / bucket_observations
                    return bucket_start + fraction * (bucket_end - bucket_start)

                elif i < len(self.buckets):
                    # In a middle bucket (buckets[i-1], buckets[i]]
                    bucket_start = self.buckets[i-1]
                    bucket_end = self.buckets[i]
                    prev_cumulative = self.bucket_counts[i-1] if i > 0 else 0
                    bucket_observations = cumulative_count - prev_cumulative

                    if bucket_observations == 0:
                        return bucket_start

                    # Linear interpolation within bucket
                    fraction = (target_count - prev_cumulative) / bucket_observations
                    return bucket_start + fraction * (bucket_end - bucket_start)

                else:
                    # In the last bucket (> buckets[-1])
                    bucket_start = self.buckets[-1]
                    # For the last bucket, we don't know the upper bound
                    # Use linear interpolation assuming uniform distribution up to max
                    prev_cumulative = self.bucket_counts[-2] if len(self.bucket_counts) > 1 else 0
                    bucket_observations = cumulative_count - prev_cumulative

                    if bucket_observations == 0:
                        return bucket_start

                    # Estimate position within last bucket
                    fraction = (target_count - prev_cumulative) / bucket_observations
                    # Interpolate between bucket_start and max (or estimate)
                    bucket_end = max(self.max or bucket_start, bucket_start + 1.0)  # Conservative estimate
                    return bucket_start + fraction * (bucket_end - bucket_start)

        # Fallback: should not reach here in normal cases
        return self.max