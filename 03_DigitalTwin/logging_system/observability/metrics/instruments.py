"""
Metric instruments for Py_LoggingSystem observability.

This module provides high-level instrument classes that provide convenient
APIs for recording metrics, while internally using the metric registry.
"""

import threading
from typing import Dict, List, Optional

from .registry import MetricRegistry
from .types import EMetricType, MetricMetadata


class Counter:
    """
    Counter instrument for recording monotonically increasing values.

    Counters are used to track cumulative counts such as the number of
    requests served, errors occurred, or bytes transferred.

    This instrument provides a convenient API while internally using
    the metric registry for storage and thread safety.
    """

    def __init__(self,
                 name: str,
                 description: str = "",
                 unit: Optional[str] = None,
                 labels: Optional[Dict[str, str]] = None):
        """
        Initialize a counter instrument.

        Args:
            name: Metric name (must be unique)
            description: Human-readable description
            unit: Unit of measurement (e.g., "requests", "bytes")
            labels: Default labels to apply to all measurements
        """
        self._name = name
        self._description = description
        self._unit = unit
        self._default_labels = labels or {}
        self._registry = MetricRegistry.get_instance()

        # Note: Counter is lazily initialized on first increment() call
        # This avoids creating empty counters in the registry

    def increment(self, amount: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment the counter by the specified amount.

        Args:
            amount: Amount to increment (must be positive)
            labels: Additional labels to merge with default labels

        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError("Counter increment amount must be positive")

        # Merge default labels with provided labels
        merged_labels = {**self._default_labels}
        if labels:
            merged_labels.update(labels)

        # Use registry to increment (create if needed with merged labels)
        self._registry.counter(
            name=self._name,
            description=self._description,
            unit=self._unit,
            labels=merged_labels,
            initial_value=amount
        )

    def get_value(self, labels: Optional[Dict[str, str]] = None) -> int:
        """
        Get the current value of the counter.

        Note: This method is primarily for testing. In production,
        metrics are typically collected via the registry's collect() method.

        Args:
            labels: Labels to identify the specific counter instance

        Returns:
            Current counter value
        """
        merged_labels = {**self._default_labels}
        if labels:
            merged_labels.update(labels)

        # Create a temporary metadata to match the stored metric
        temp_metadata = MetricMetadata(
            name=self._name,
            type=EMetricType.COUNTER,
            description=self._description,
            unit=self._unit,
            labels=merged_labels
        )

        # Find matching metric in registry
        for metric in self._registry.collect():
            if (metric.metadata.name == self._name and
                metric.metadata.labels == merged_labels and
                isinstance(metric, type(metric))):  # CounterValue
                return metric.value

        return 0  # Not found

    @property
    def name(self) -> str:
        """Get the metric name."""
        return self._name

    @property
    def description(self) -> str:
        """Get the metric description."""
        return self._description

    @property
    def unit(self) -> Optional[str]:
        """Get the metric unit."""
        return self._unit


class Gauge:
    """
    Gauge instrument for recording point-in-time measurements.

    Gauges represent values that can go up or down, typically used for
    current measurements such as memory usage, queue size, temperature,
    or any instantaneous value.

    This instrument provides a convenient API while internally using
    the metric registry for storage and thread safety.
    """

    def __init__(self,
                 name: str,
                 description: str = "",
                 unit: Optional[str] = None,
                 labels: Optional[Dict[str, str]] = None,
                 initial_value: float = 0.0):
        """
        Initialize a gauge instrument.

        Args:
            name: Metric name (must be unique)
            description: Human-readable description
            unit: Unit of measurement (e.g., "bytes", "celsius", "percent")
            labels: Default labels to apply to all measurements
            initial_value: Initial gauge value
        """
        self._name = name
        self._description = description
        self._unit = unit
        self._default_labels = labels or {}
        self._registry = MetricRegistry.get_instance()

        # Set initial value
        self.set(initial_value)

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Set the gauge to a specific value.

        Args:
            value: The value to set
            labels: Additional labels to merge with default labels
        """
        # Merge default labels with provided labels
        merged_labels = {**self._default_labels}
        if labels:
            merged_labels.update(labels)

        # Use registry to set gauge value
        self._registry.gauge_set(
            name=self._name,
            value=value,
            description=self._description,
            unit=self._unit,
            labels=merged_labels
        )

    def increment(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Increment the gauge by the specified amount.

        Args:
            amount: Amount to increment (can be negative to decrement)
            labels: Additional labels to merge with default labels
        """
        # Merge default labels with provided labels
        merged_labels = {**self._default_labels}
        if labels:
            merged_labels.update(labels)

        # Use registry to increment gauge value
        self._registry.gauge_inc(
            name=self._name,
            amount=amount,
            description=self._description,
            unit=self._unit,
            labels=merged_labels
        )

    def decrement(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Decrement the gauge by the specified amount.

        Args:
            amount: Amount to decrement
            labels: Additional labels to merge with default labels
        """
        # Decrement is just incrementing by negative amount
        self.increment(-amount, labels)

    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """
        Get the current value of the gauge.

        Note: This method is primarily for testing. In production,
        metrics are typically collected via the registry's collect() method.

        Args:
            labels: Labels to identify the specific gauge instance

        Returns:
            Current gauge value
        """
        merged_labels = {**self._default_labels}
        if labels:
            merged_labels.update(labels)

        # Find matching metric in registry
        for metric in self._registry.collect():
            if (metric.metadata.name == self._name and
                metric.metadata.labels == merged_labels and
                isinstance(metric, type(metric))):  # GaugeValue
                return metric.value

        return 0.0  # Not found

    @property
    def name(self) -> str:
        """Get the metric name."""
        return self._name

    @property
    def description(self) -> str:
        """Get the metric description."""
        return self._description

    @property
    def unit(self) -> Optional[str]:
        """Get the metric unit."""
        return self._unit


class Histogram:
    """
    Histogram instrument for recording value distributions.

    Histograms track the distribution of values, including count, sum,
    and bucketed counts for percentile calculations. They are typically
    used for measuring latencies, request sizes, or other distributions.

    This instrument provides a convenient API while internally using
    the metric registry for storage and thread safety.
    """

    # Default bucket boundaries following Prometheus conventions
    DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]

    def __init__(self,
                 name: str,
                 description: str = "",
                 unit: Optional[str] = None,
                 labels: Optional[Dict[str, str]] = None,
                 buckets: Optional[List[float]] = None):
        """
        Initialize a histogram instrument.

        Args:
            name: Metric name (must be unique)
            description: Human-readable description
            unit: Unit of measurement (e.g., "seconds", "bytes")
            labels: Default labels to apply to all measurements
            buckets: Bucket boundaries (default: standard Prometheus buckets)
        """
        self._name = name
        self._description = description
        self._unit = unit
        self._default_labels = labels or {}
        self._buckets = buckets or self.DEFAULT_BUCKETS.copy()
        self._registry = MetricRegistry.get_instance()

        # Validate buckets are sorted
        if self._buckets != sorted(self._buckets):
            raise ValueError("Histogram buckets must be sorted in ascending order")

        # Note: Histogram is lazily initialized on first observe() call
        # This avoids creating empty histograms in the registry

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """
        Observe a value in the histogram.

        Args:
            value: Value to observe
            labels: Additional labels to merge with default labels
        """
        # Merge default labels with provided labels
        merged_labels = {**self._default_labels}
        if labels:
            merged_labels.update(labels)

        # Use registry to observe value in histogram
        # Registry handles initialization on first observation
        self._registry.histogram_observe(
            name=self._name,
            value=value,
            buckets=self._buckets,
            description=self._description,
            unit=self._unit,
            labels=merged_labels
        )

    def get_summary(self, labels: Optional[Dict[str, str]] = None) -> Optional[Dict[str, any]]:
        """
        Get a summary of the histogram data.

        Note: This method is primarily for testing. In production,
        metrics are typically collected via the registry's collect() method.

        Args:
            labels: Labels to identify the specific histogram instance

        Returns:
            Dictionary with histogram summary or None if not found
        """
        merged_labels = {**self._default_labels}
        if labels:
            merged_labels.update(labels)

        # Find matching metric in registry
        for metric in self._registry.collect():
            if (metric.metadata.name == self._name and
                metric.metadata.labels == merged_labels and
                hasattr(metric, 'buckets')):  # HistogramValue
                return {
                    'count': metric.count,
                    'sum': metric.sum,
                    'min': metric.min,
                    'max': metric.max,
                    'average': metric.sum / metric.count if metric.count > 0 else 0,
                    'buckets': metric.buckets,
                    'bucket_counts': metric.bucket_counts,
                    'p50': metric.percentile(50.0),
                    'p95': metric.percentile(95.0),
                    'p99': metric.percentile(99.0)
                }

        return None  # Not found

    @property
    def name(self) -> str:
        """Get the metric name."""
        return self._name

    @property
    def description(self) -> str:
        """Get the metric description."""
        return self._description

    @property
    def unit(self) -> Optional[str]:
        """Get the metric unit."""
        return self._unit

    @property
    def buckets(self) -> List[float]:
        """Get the histogram bucket boundaries."""
        return self._buckets.copy()
