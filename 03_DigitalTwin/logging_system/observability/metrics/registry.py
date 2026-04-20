"""
Metric registry for Py_LoggingSystem observability.

This module provides a centralized registry for managing metrics throughout
the logging system, with thread-safe operations and collection capabilities.
"""

import threading
import time
from typing import Dict, List, Optional

from .types import (
    EMetricType,
    MetricMetadata,
    MetricValue,
    CounterValue,
    GaugeValue,
    HistogramValue,
)


class MetricRegistry:
    """
    Centralized registry for metrics collection and management.

    This singleton registry provides thread-safe operations for creating,
    updating, and collecting metrics throughout the logging system.
    It follows OpenTelemetry patterns for metric management.

    Thread Safety:
        All operations are thread-safe using internal locking.
    """

    _instance: Optional['MetricRegistry'] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize the metric registry. Use get_instance() instead."""
        self._metrics: Dict[str, MetricValue] = {}
        self._registry_lock = threading.RLock()

    def _get_metric_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """
        Generate a unique key for a metric based on name and labels.

        Args:
            name: Metric name
            labels: Metric labels

        Returns:
            Unique key for the metric
        """
        if not labels:
            return name

        # Sort labels for consistent key generation
        sorted_labels = sorted(labels.items())
        label_str = ",".join(f"{k}={v}" for k, v in sorted_labels)
        return f"{name}{{{label_str}}}"

    @classmethod
    def get_instance(cls) -> 'MetricRegistry':
        """
        Get the singleton instance of the metric registry.

        Returns:
            MetricRegistry: The singleton registry instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def counter(
        self,
        name: str,
        description: str = "",
        unit: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        initial_value: int = 0
    ) -> CounterValue:
        """
        Create or update a counter metric.

        Counters represent monotonically increasing values.

        Args:
            name: Metric name (must be unique)
            description: Human-readable description
            unit: Unit of measurement (e.g., "requests", "bytes")
            labels: Key-value labels for dimensional metrics
            initial_value: Initial counter value (default: 0)

        Returns:
            CounterValue: The counter metric value

        Raises:
            ValueError: If initial_value is negative
        """
        if initial_value < 0:
            raise ValueError("Counter initial value must be non-negative")

        metadata = MetricMetadata(
            name=name,
            type=EMetricType.COUNTER,
            description=description,
            unit=unit,
            labels=labels
        )

        key = self._get_metric_key(name, labels)

        with self._registry_lock:
            if key in self._metrics:
                # Update existing counter
                existing = self._metrics[key]
                if isinstance(existing, CounterValue):
                    # For existing counters, increment by initial_value if > 0, otherwise return existing
                    if initial_value > 0:
                        new_value = existing.value + initial_value
                        updated_counter = CounterValue(
                            metadata=metadata,
                            timestamp=self._get_current_timestamp(),
                            value=new_value
                        )
                        self._metrics[key] = updated_counter
                        return updated_counter
                    else:
                        return existing
                else:
                    raise ValueError(f"Metric '{key}' already exists with different type")

            # Create new counter
            counter = CounterValue(
                metadata=metadata,
                timestamp=self._get_current_timestamp(),
                value=initial_value
            )
            self._metrics[key] = counter
            return counter

    def gauge_set(
        self,
        name: str,
        value: float,
        description: str = "",
        unit: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> GaugeValue:
        """
        Create or update a gauge metric by setting its value.

        Gauges represent point-in-time measurements.

        Args:
            name: Metric name (must be unique)
            value: The gauge value to set
            description: Human-readable description
            unit: Unit of measurement (e.g., "bytes", "celsius")
            labels: Key-value labels for dimensional metrics

        Returns:
            GaugeValue: The gauge metric value
        """
        metadata = MetricMetadata(
            name=name,
            type=EMetricType.GAUGE,
            description=description,
            unit=unit,
            labels=labels
        )

        key = self._get_metric_key(name, labels)

        with self._registry_lock:
            gauge = GaugeValue(
                metadata=metadata,
                timestamp=self._get_current_timestamp(),
                value=value
            )
            self._metrics[key] = gauge
            return gauge

    def gauge_inc(
        self,
        name: str,
        amount: float = 1.0,
        description: str = "",
        unit: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> GaugeValue:
        """
        Create or increment a gauge metric.

        Args:
            name: Metric name (must be unique)
            amount: Amount to increment (can be negative to decrement)
            description: Human-readable description
            unit: Unit of measurement
            labels: Key-value labels for dimensional metrics

        Returns:
            GaugeValue: The updated gauge metric value
        """
        key = self._get_metric_key(name, labels)

        with self._registry_lock:
            if key in self._metrics:
                existing = self._metrics[key]
                if isinstance(existing, GaugeValue):
                    new_gauge = existing.update(existing.value + amount)
                    self._metrics[key] = new_gauge
                    return new_gauge
                else:
                    raise ValueError(f"Metric '{key}' already exists with different type")

            # Create new gauge with the increment amount
            metadata = MetricMetadata(
                name=name,
                type=EMetricType.GAUGE,
                description=description,
                unit=unit,
                labels=labels
            )

            gauge = GaugeValue(
                metadata=metadata,
                timestamp=self._get_current_timestamp(),
                value=amount
            )
            self._metrics[key] = gauge
            return gauge

    def histogram_observe(
        self,
        name: str,
        value: float,
        buckets: Optional[List[float]] = None,
        description: str = "",
        unit: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> HistogramValue:
        """
        Create or update a histogram metric by observing a value.

        Args:
            name: Metric name (must be unique)
            value: Value to observe
            buckets: Bucket boundaries (default: [0.1, 1.0, 10.0])
            description: Human-readable description
            unit: Unit of measurement
            labels: Key-value labels for dimensional metrics

        Returns:
            HistogramValue: The updated histogram metric value
        """
        if buckets is None:
            buckets = [0.1, 1.0, 10.0]

        metadata = MetricMetadata(
            name=name,
            type=EMetricType.HISTOGRAM,
            description=description,
            unit=unit,
            labels=labels
        )

        key = self._get_metric_key(name, labels)

        with self._registry_lock:
            if key in self._metrics:
                existing = self._metrics[key]
                if isinstance(existing, HistogramValue):
                    # Verify bucket configuration matches
                    if existing.buckets != buckets:
                        raise ValueError(f"Histogram '{key}' bucket configuration mismatch")
                    new_histogram = existing.observe(value)
                    self._metrics[key] = new_histogram
                    return new_histogram
                else:
                    raise ValueError(f"Metric '{key}' already exists with different type")

            # Create new histogram
            histogram = HistogramValue(
                metadata=metadata,
                timestamp=self._get_current_timestamp(),
                value=0.0,  # Histogram value is not used directly
                count=0,
                sum=0.0,
                buckets=buckets,
                bucket_counts=[0] * (len(buckets) + 1)
            )
            # Observe the first value
            histogram = histogram.observe(value)
            self._metrics[key] = histogram
            return histogram

    def collect(self) -> List[MetricValue]:
        """
        Collect all current metric values.

        This method returns a snapshot of all metrics currently registered.
        It's typically called by metric exporters or monitoring systems.

        Returns:
            List[MetricValue]: All current metric values
        """
        with self._registry_lock:
            return list(self._metrics.values())

    def get_metric(self, name: str) -> Optional[MetricValue]:
        """
        Get a specific metric by name.

        Args:
            name: Metric name

        Returns:
            MetricValue or None: The metric value if found
        """
        with self._registry_lock:
            return self._metrics.get(name)

    def clear(self) -> None:
        """
        Clear all metrics from the registry.

        This is primarily intended for testing purposes.
        """
        with self._registry_lock:
            self._metrics.clear()

    def _get_current_timestamp(self):
        """Get the current timestamp for metric values."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)


# Module-level convenience functions for easy access
def counter(name: str, description: str = "", unit: Optional[str] = None,
           labels: Optional[Dict[str, str]] = None, initial_value: int = 0) -> CounterValue:
    """Module-level counter function."""
    return MetricRegistry.get_instance().counter(name, description, unit, labels, initial_value)


def gauge_set(name: str, value: float, description: str = "", unit: Optional[str] = None,
              labels: Optional[Dict[str, str]] = None) -> GaugeValue:
    """Module-level gauge set function."""
    return MetricRegistry.get_instance().gauge_set(name, value, description, unit, labels)


def gauge_inc(name: str, amount: float = 1.0, description: str = "",
              unit: Optional[str] = None, labels: Optional[Dict[str, str]] = None) -> GaugeValue:
    """Module-level gauge increment function."""
    return MetricRegistry.get_instance().gauge_inc(name, amount, description, unit, labels)


def histogram_observe(name: str, value: float, buckets: Optional[List[float]] = None,
                     description: str = "", unit: Optional[str] = None,
                     labels: Optional[Dict[str, str]] = None) -> HistogramValue:
    """Module-level histogram observe function."""
    return MetricRegistry.get_instance().histogram_observe(name, value, buckets, description, unit, labels)


def collect() -> List[MetricValue]:
    """Module-level collect function."""
    return MetricRegistry.get_instance().collect()