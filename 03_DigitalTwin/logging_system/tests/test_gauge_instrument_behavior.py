"""
Unit tests for Gauge instrument in Py_LoggingSystem.

Tests the Gauge instrument functionality and integration with the registry.
"""

import pytest

from logging_system.observability.metrics.instruments import Gauge
from logging_system.observability.metrics.registry import MetricRegistry


class TestGauge:
    """Test the Gauge instrument."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def teardown_method(self):
        """Clean up after test method."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def test_gauge_set(self):
        """Test gauge set operations."""
        gauge = Gauge("test_gauge", "Test gauge", "units", initial_value=10.0)

        # Initial value should be set
        assert gauge.get_value() == 10.0

        # Set to new value
        gauge.set(25.5)
        assert gauge.get_value() == 25.5

        # Set to zero
        gauge.set(0.0)
        assert gauge.get_value() == 0.0

        # Set negative value (should be allowed for gauges)
        gauge.set(-5.2)
        assert gauge.get_value() == -5.2

    def test_gauge_increment(self):
        """Test gauge increment operations."""
        gauge = Gauge("test_gauge_inc", "Increment gauge", initial_value=5.0)

        # Increment by default (1.0)
        gauge.increment()
        assert gauge.get_value() == 6.0

        # Increment by specific amount
        gauge.increment(10.5)
        assert gauge.get_value() == 16.5

        # Increment by negative amount (decrement)
        gauge.increment(-3.0)
        assert gauge.get_value() == 13.5

        # Increment by zero
        gauge.increment(0.0)
        assert gauge.get_value() == 13.5

    def test_gauge_decrement(self):
        """Test gauge decrement operations."""
        gauge = Gauge("test_gauge_dec", "Decrement gauge", initial_value=20.0)

        # Decrement by default (1.0)
        gauge.decrement()
        assert gauge.get_value() == 19.0

        # Decrement by specific amount
        gauge.decrement(5.0)
        assert gauge.get_value() == 14.0

        # Decrement by negative amount (increment)
        gauge.decrement(-8.0)
        assert gauge.get_value() == 22.0

    def test_gauge_with_labels(self):
        """Test gauge with labels support."""
        # Gauge with default labels
        gauge = Gauge(
            "memory_usage",
            "Memory usage",
            "bytes",
            labels={"host": "server1"}
        )

        # Set value with default labels
        gauge.set(1024.0)
        assert gauge.get_value() == 1024.0

        # Set value with additional labels (should create separate metric)
        gauge.set(2048.0, labels={"region": "us-east"})
        # Note: get_value() with different labels won't find the original
        # This tests that different label combinations are handled

    def test_gauge_initialization(self):
        """Test gauge initialization with various parameters."""
        # Minimal gauge
        gauge1 = Gauge("minimal_gauge")
        assert gauge1.name == "minimal_gauge"
        assert gauge1.description == ""
        assert gauge1.unit is None
        assert gauge1.get_value() == 0.0  # Default initial value

        # Full gauge with initial value
        gauge2 = Gauge(
            name="full_gauge",
            description="Full gauge with initial value",
            unit="celsius",
            labels={"sensor": "cpu"},
            initial_value=25.5
        )
        assert gauge2.name == "full_gauge"
        assert gauge2.description == "Full gauge with initial value"
        assert gauge2.unit == "celsius"
        assert gauge2.get_value() == 25.5

    def test_gauge_registry_integration(self):
        """Test that gauge properly integrates with the registry."""
        gauge = Gauge("registry_test", "Registry integration test", "items", initial_value=42.0)

        # Modify gauge
        gauge.set(100.5)
        gauge.increment(10.0)
        gauge.decrement(5.0)

        # Check registry directly
        registry = MetricRegistry.get_instance()
        metrics = registry.collect()

        # Should have our gauge
        gauge_metrics = [m for m in metrics if m.metadata.name == "registry_test"]
        assert len(gauge_metrics) == 1

        metric = gauge_metrics[0]
        assert metric.value == 105.5  # 100.5 + 10.0 - 5.0
        assert metric.metadata.type.name == "GAUGE"
        assert metric.metadata.unit == "items"

    def test_gauge_multiple_instances_same_name(self):
        """Test that multiple gauge instances with same name share state."""
        gauge1 = Gauge("shared_gauge", "Shared gauge", initial_value=10.0)
        gauge2 = Gauge("shared_gauge", "Shared gauge")  # Same name, different initial value

        # Both should share the same registry entry
        gauge1.set(50.0)
        assert gauge1.get_value() == 50.0

        gauge2.increment(25.0)
        assert gauge2.get_value() == 75.0  # Should see gauge1's value + increment
        assert gauge1.get_value() == 75.0  # Should see gauge2's increment

    def test_gauge_empty_labels(self):
        """Test gauge with empty/None labels."""
        gauge = Gauge("no_labels_gauge", "No labels gauge", initial_value=15.0)

        gauge.set(30.0)
        assert gauge.get_value() == 30.0

        # Should work with None labels parameter
        gauge.increment(5.0, labels=None)
        assert gauge.get_value() == 35.0

        gauge.decrement(10.0, labels=None)
        assert gauge.get_value() == 25.0

    def test_gauge_operations_with_different_labels(self):
        """Test that gauge operations with different labels create separate metrics."""
        gauge = Gauge("multi_label_gauge", "Multi-label gauge")

        # Set value with one set of labels
        gauge.set(100.0, labels={"env": "prod"})
        # Note: get_value() only looks for exact label match, so we can't easily test
        # the separate metrics here, but the registry will have them

        # Check registry has the metric
        registry = MetricRegistry.get_instance()
        metrics = registry.collect()
        gauge_metrics = [m for m in metrics if m.metadata.name == "multi_label_gauge"]
        assert len(gauge_metrics) >= 1

    def test_gauge_properties(self):
        """Test gauge property access."""
        gauge = Gauge("property_test", "Property test", "widgets", {"type": "counter"})

        assert gauge.name == "property_test"
        assert gauge.description == "Property test"
        assert gauge.unit == "widgets"


class TestGaugeIntegration:
    """Integration tests for Gauge with registry."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def teardown_method(self):
        """Clean up after test method."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def test_gauge_collect_integration(self):
        """Test gauge integration with registry collect."""
        gauge = Gauge("collect_test", "Collect integration", "degrees", initial_value=20.0)

        # Make some modifications
        gauge.set(25.0)
        gauge.increment(5.0)
        gauge.decrement(3.0)

        # Collect all metrics
        registry = MetricRegistry.get_instance()
        all_metrics = registry.collect()

        # Find our gauge
        gauge_metrics = [m for m in all_metrics if m.metadata.name == "collect_test"]
        assert len(gauge_metrics) == 1

        metric = gauge_metrics[0]
        assert metric.value == 27.0  # 25.0 + 5.0 - 3.0
        assert metric.metadata.description == "Collect integration"
        assert metric.metadata.unit == "degrees"