"""
Metric instruments for Py_LoggingSystem observability.

This module provides high-level instrument classes that provide convenient
APIs for recording metrics, while internally using the metric registry.
"""

import threading
from typing import Dict, Optional

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

        # Create the initial metric in the registry
        self._registry.counter(
            name=name,
            description=description,
            unit=unit,
            labels=self._default_labels,
            initial_value=0
        )

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
            initial_value=amount  # This will increment existing counter
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