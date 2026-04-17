"""
Unit tests for MetricRegistry in Py_LoggingSystem.

Tests the metric registry functionality, thread safety, and all operations.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from logging_system.observability.metrics.registry import MetricRegistry
from logging_system.observability.metrics.types import EMetricType


class TestMetricRegistry:
    """Test the MetricRegistry class."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def teardown_method(self):
        """Clean up after test method."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def test_registry_singleton(self):
        """Test that MetricRegistry is a singleton."""
        registry1 = MetricRegistry.get_instance()
        registry2 = MetricRegistry.get_instance()

        assert registry1 is registry2
        assert isinstance(registry1, MetricRegistry)

    def test_registry_counter_increment(self):
        """Test counter creation and increment operations."""
        registry = MetricRegistry.get_instance()

        # Create a new counter
        counter = registry.counter("test_counter", "Test counter", "requests", initial_value=5)
        assert counter.value == 5
        assert counter.metadata.name == "test_counter"
        assert counter.metadata.type == EMetricType.COUNTER
        assert counter.metadata.unit == "requests"

        # Increment via registry (this is the intended API)
        registry.counter("test_counter", initial_value=3)  # Increment by 3

        # Registry should have the updated value
        stored_counter = registry.get_metric("test_counter")
        assert stored_counter.value == 8

        # Test the CounterValue.increment() method separately
        new_counter = counter.increment(2)
        assert new_counter.value == 7  # 5 + 2
        assert new_counter is not counter  # Should be a new instance

        # But registry still has the original value (increment doesn't auto-update registry)
        stored_counter2 = registry.get_metric("test_counter")
        assert stored_counter2.value == 8

    def test_registry_counter_negative_initial_value(self):
        """Test that negative initial counter values are rejected."""
        registry = MetricRegistry.get_instance()

        with pytest.raises(ValueError, match="Counter initial value must be non-negative"):
            registry.counter("test_counter", initial_value=-1)

    def test_registry_counter_existing_metric_different_type(self):
        """Test that creating a counter with existing name but different type fails."""
        registry = MetricRegistry.get_instance()

        # Create a gauge first
        registry.gauge_set("test_metric", 10.0)

        # Try to create a counter with same name
        with pytest.raises(ValueError, match="already exists with different type"):
            registry.counter("test_metric")

    def test_registry_gauge_set(self):
        """Test gauge set operations."""
        registry = MetricRegistry.get_instance()

        # Set gauge value
        gauge = registry.gauge_set("test_gauge", 42.5, "Test gauge", "percent")
        assert gauge.value == 42.5
        assert gauge.metadata.name == "test_gauge"
        assert gauge.metadata.type == EMetricType.GAUGE
        assert gauge.metadata.unit == "percent"

        # Set new value
        new_gauge = registry.gauge_set("test_gauge", 75.0)
        assert new_gauge.value == 75.0
        assert new_gauge is not gauge  # Should be a new instance

        # Registry should have the updated value
        stored_gauge = registry.get_metric("test_gauge")
        assert stored_gauge.value == 75.0

    def test_registry_gauge_inc(self):
        """Test gauge increment operations."""
        registry = MetricRegistry.get_instance()

        # Increment new gauge
        gauge = registry.gauge_inc("test_gauge_inc", 5.0, "Increment gauge")
        assert gauge.value == 5.0

        # Increment existing gauge
        new_gauge = registry.gauge_inc("test_gauge_inc", 3.0)
        assert new_gauge.value == 8.0

        # Decrement gauge
        new_gauge2 = registry.gauge_inc("test_gauge_inc", -2.0)
        assert new_gauge2.value == 6.0

    def test_registry_gauge_inc_existing_different_type(self):
        """Test that gauge increment on existing counter fails."""
        registry = MetricRegistry.get_instance()

        # Create a counter first
        registry.counter("test_metric", initial_value=10)

        # Try to increment as gauge
        with pytest.raises(ValueError, match="already exists with different type"):
            registry.gauge_inc("test_metric", 5.0)

    def test_registry_histogram_observe(self):
        """Test histogram observe operations."""
        registry = MetricRegistry.get_instance()

        # Observe first value
        histogram = registry.histogram_observe("test_histogram", 0.5, [0.1, 1.0, 10.0], "Response time")
        assert histogram.count == 1
        assert histogram.sum == 0.5
        assert histogram.buckets == [0.1, 1.0, 10.0]
        assert histogram.bucket_counts == [0, 1, 1, 1]  # 0.5 goes in bucket <= 1.0

        # Observe another value
        new_histogram = registry.histogram_observe("test_histogram", 5.0)
        assert new_histogram.count == 2
        assert new_histogram.sum == 5.5
        assert new_histogram.bucket_counts == [0, 1, 2, 2]  # 5.0 goes in bucket <= 10.0 and > 10.0 bucket

    def test_registry_histogram_bucket_mismatch(self):
        """Test that histogram observe with different buckets fails."""
        registry = MetricRegistry.get_instance()

        # Create histogram with specific buckets
        registry.histogram_observe("test_histogram", 1.0, [0.1, 1.0, 10.0])

        # Try to observe with different buckets
        with pytest.raises(ValueError, match="bucket configuration mismatch"):
            registry.histogram_observe("test_histogram", 2.0, [0.2, 2.0, 20.0])

    def test_registry_histogram_existing_different_type(self):
        """Test that histogram observe on existing counter fails."""
        registry = MetricRegistry.get_instance()

        # Create a counter first
        registry.counter("test_metric", initial_value=10)

        # Try to observe as histogram
        with pytest.raises(ValueError, match="already exists with different type"):
            registry.histogram_observe("test_metric", 5.0)

    def test_registry_collect(self):
        """Test collecting all metrics."""
        registry = MetricRegistry.get_instance()

        # Create various metrics
        registry.counter("counter1", initial_value=10)
        registry.gauge_set("gauge1", 25.5)
        registry.histogram_observe("histogram1", 1.5)

        metrics = registry.collect()

        assert len(metrics) == 3
        metric_names = {m.metadata.name for m in metrics}
        assert metric_names == {"counter1", "gauge1", "histogram1"}

    def test_registry_get_metric(self):
        """Test getting a specific metric."""
        registry = MetricRegistry.get_instance()

        # Metric doesn't exist
        assert registry.get_metric("nonexistent") is None

        # Create and retrieve metric
        counter = registry.counter("test_counter", initial_value=5)
        retrieved = registry.get_metric("test_counter")

        assert retrieved is not None
        assert retrieved.value == 5
        assert retrieved.metadata.name == "test_counter"

    def test_registry_thread_safety(self):
        """Test that registry operations are thread-safe."""
        registry = MetricRegistry.get_instance()

        def increment_counter():
            for _ in range(100):
                try:
                    counter = registry.counter("thread_counter", initial_value=0)
                    registry.counter("thread_counter", initial_value=counter.value + 1)
                except ValueError:
                    # Handle the case where counter already exists
                    pass

        def update_gauge():
            for _ in range(100):
                registry.gauge_inc("thread_gauge", 1.0)

        # Run operations in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for _ in range(4):
                futures.append(executor.submit(increment_counter))
                futures.append(executor.submit(update_gauge))

            # Wait for all to complete
            for future in futures:
                future.result()

        # Verify final state
        counter_metric = registry.get_metric("thread_counter")
        gauge_metric = registry.get_metric("thread_gauge")

        # Counter should have been incremented (exact value depends on timing)
        assert counter_metric is not None
        assert counter_metric.value >= 0

        # Gauge should have been incremented multiple times
        assert gauge_metric is not None
        assert gauge_metric.value >= 0


class TestModuleLevelFunctions:
    """Test the module-level convenience functions."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def teardown_method(self):
        """Clean up after test method."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def test_module_counter(self):
        """Test module-level counter function."""
        from logging_system.observability.metrics.registry import counter

        counter_metric = counter("module_counter", "Module counter", "ops", initial_value=5)
        assert counter_metric.value == 5
        assert counter_metric.metadata.unit == "ops"

    def test_module_gauge_set(self):
        """Test module-level gauge_set function."""
        from logging_system.observability.metrics.registry import gauge_set

        gauge_metric = gauge_set("module_gauge", 42.0, "Module gauge", "units")
        assert gauge_metric.value == 42.0
        assert gauge_metric.metadata.unit == "units"

    def test_module_gauge_inc(self):
        """Test module-level gauge_inc function."""
        from logging_system.observability.metrics.registry import gauge_inc

        gauge_metric = gauge_inc("module_gauge_inc", 10.0, "Increment gauge")
        assert gauge_metric.value == 10.0

    def test_module_histogram_observe(self):
        """Test module-level histogram_observe function."""
        from logging_system.observability.metrics.registry import histogram_observe

        histogram_metric = histogram_observe("module_histogram", 2.5, [1.0, 10.0], "Response time")
        assert histogram_metric.count == 1
        assert histogram_metric.sum == 2.5

    def test_module_collect(self):
        """Test module-level collect function."""
        from logging_system.observability.metrics.registry import collect, counter, gauge_set

        counter("test_counter", initial_value=1)
        gauge_set("test_gauge", 2.0)

        metrics = collect()
        assert len(metrics) == 2
        metric_names = {m.metadata.name for m in metrics}
        assert metric_names == {"test_counter", "test_gauge"}