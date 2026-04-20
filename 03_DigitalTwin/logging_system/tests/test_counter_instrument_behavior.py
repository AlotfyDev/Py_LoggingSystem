"""
Unit tests for Counter instrument in Py_LoggingSystem.

Tests the Counter instrument functionality and integration with the registry.
"""

import pytest
from concurrent.futures import ThreadPoolExecutor

from logging_system.observability.metrics.instruments import Counter
from logging_system.observability.metrics.registry import MetricRegistry


class TestCounter:
    """Test the Counter instrument."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def teardown_method(self):
        """Clean up after test method."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def test_counter_basic_increment(self):
        """Test basic counter increment operations."""
        counter = Counter("test_counter", "Test counter", "requests")

        # Initial value should be accessible
        assert counter.name == "test_counter"
        assert counter.description == "Test counter"
        assert counter.unit == "requests"

        # Increment by default (1)
        counter.increment()
        assert counter.get_value() == 1

        # Increment by specific amount
        counter.increment(5)
        assert counter.get_value() == 6

        # Multiple increments
        counter.increment(10)
        counter.increment(4)
        assert counter.get_value() == 20

    def test_counter_with_labels(self):
        """Test counter with labels support."""
        # Counter with default labels
        counter = Counter(
            "http_requests",
            "HTTP requests",
            "requests",
            labels={"method": "GET"}
        )

        # Increment with default labels
        counter.increment()
        assert counter.get_value() == 1

        # Increment with additional labels (should create separate metric)
        counter.increment(5, labels={"status": "200"})
        # Note: get_value() with different labels won't find the original
        # This tests that different label combinations are handled

    def test_counter_thread_safety(self):
        """Test that counter operations are thread-safe."""
        counter = Counter("thread_counter", "Thread-safe counter")

        def increment_worker():
            for _ in range(100):
                counter.increment()

        # Run increments in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for _ in range(4):
                futures.append(executor.submit(increment_worker))

            # Wait for all to complete
            for future in futures:
                future.result()

        # Should have 400 total increments
        assert counter.get_value() == 400

    def test_counter_negative_increment(self):
        """Test that negative increment amounts are rejected."""
        counter = Counter("test_counter", "Test counter")

        with pytest.raises(ValueError, match="Counter increment amount must be positive"):
            counter.increment(-1)

        with pytest.raises(ValueError, match="Counter increment amount must be positive"):
            counter.increment(0)

    def test_counter_zero_increment(self):
        """Test that zero increment amounts are rejected."""
        counter = Counter("test_counter", "Test counter")

        with pytest.raises(ValueError, match="Counter increment amount must be positive"):
            counter.increment(0)

    def test_counter_registry_integration(self):
        """Test that counter properly integrates with the registry."""
        counter = Counter("registry_test", "Registry integration test", "ops")

        # Increment counter
        counter.increment(42)

        # Check registry directly
        registry = MetricRegistry.get_instance()
        metrics = registry.collect()

        # Should have our counter
        counter_metrics = [m for m in metrics if m.metadata.name == "registry_test"]
        assert len(counter_metrics) == 1

        metric = counter_metrics[0]
        assert metric.value == 42
        assert metric.metadata.type.name == "COUNTER"
        assert metric.metadata.unit == "ops"

    def test_counter_multiple_instances_same_name(self):
        """Test that multiple counter instances with same name share state."""
        counter1 = Counter("shared_counter", "Shared counter")
        counter2 = Counter("shared_counter", "Shared counter")  # Same name

        # Both should share the same registry entry
        counter1.increment(10)
        assert counter1.get_value() == 10

        counter2.increment(5)
        assert counter2.get_value() == 15  # Should see counter1's increments
        assert counter1.get_value() == 15  # Should see counter2's increments

    def test_counter_initialization(self):
        """Test counter initialization with various parameters."""
        # Minimal counter
        counter1 = Counter("minimal")
        assert counter1.name == "minimal"
        assert counter1.description == ""
        assert counter1.unit is None

        # Full counter
        counter2 = Counter(
            name="full",
            description="Full counter",
            unit="items",
            labels={"env": "test"}
        )
        assert counter2.name == "full"
        assert counter2.description == "Full counter"
        assert counter2.unit == "items"

    def test_counter_empty_labels(self):
        """Test counter with empty/None labels."""
        counter = Counter("no_labels", "No labels counter")

        counter.increment()
        assert counter.get_value() == 1

        # Should work with None labels parameter
        counter.increment(5, labels=None)
        assert counter.get_value() == 6


class TestCounterIntegration:
    """Integration tests for Counter with registry."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def teardown_method(self):
        """Clean up after test method."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def test_counter_collect_integration(self):
        """Test counter integration with registry collect."""
        counter = Counter("collect_test", "Collect integration", "calls")

        # Make some increments
        counter.increment(5)
        counter.increment(10)
        counter.increment(3)

        # Collect all metrics
        registry = MetricRegistry.get_instance()
        all_metrics = registry.collect()

        # Find our counter
        counter_metrics = [m for m in all_metrics if m.metadata.name == "collect_test"]
        assert len(counter_metrics) == 1

        metric = counter_metrics[0]
        assert metric.value == 18  # 5 + 10 + 3
        assert metric.metadata.description == "Collect integration"
        assert metric.metadata.unit == "calls"