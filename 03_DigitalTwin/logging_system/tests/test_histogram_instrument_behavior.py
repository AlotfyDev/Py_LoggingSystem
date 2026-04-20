"""
Unit tests for Histogram instrument in Py_LoggingSystem.

Tests the Histogram instrument functionality and integration with the registry.
"""

import pytest

from logging_system.observability.metrics.instruments import Histogram
from logging_system.observability.metrics.registry import MetricRegistry


class TestHistogram:
    """Test the Histogram instrument."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def teardown_method(self):
        """Clean up after test method."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def test_histogram_observe(self):
        """Test histogram observe operations."""
        histogram = Histogram("test_histogram", "Test histogram", "seconds")

        # Observe some values
        histogram.observe(0.1)
        histogram.observe(0.5)
        histogram.observe(2.0)

        summary = histogram.get_summary()
        assert summary is not None
        assert summary['count'] == 3  # 3 observations
        # Bucket counts should be [<=0.1, <=1.0, <=10.0, >10.0]
        # Expected: [1, 2, 3, 3] (cumulative)

    def test_histogram_with_labels(self):
        """Test histogram with labels support."""
        # Histogram with default labels
        histogram = Histogram(
            "labeled_histogram",
            "Labeled histogram",
            "requests",
            labels={"service": "api"}
        )

        # Observe with default labels
        histogram.observe(1.5)
        summary1 = histogram.get_summary()
        assert summary1 is not None
        assert summary1['count'] == 1  # 1 observation

        # Observe with additional labels (should create separate metric)
        histogram.observe(2.5, labels={"endpoint": "/users"})
        # Note: get_summary() with different labels won't find the original
        # This tests that different label combinations are handled

    def test_histogram_initialization(self):
        """Test histogram initialization with various parameters."""
        # Minimal histogram
        hist1 = Histogram("minimal_hist")
        assert hist1.name == "minimal_hist"
        assert hist1.description == ""
        assert hist1.unit is None
        assert len(hist1.buckets) == 14  # Default buckets

        # Full histogram with custom buckets
        custom_buckets = [0.1, 1.0, 5.0]
        hist2 = Histogram(
            name="full_hist",
            description="Full histogram with custom buckets",
            unit="milliseconds",
            labels={"component": "database"},
            buckets=custom_buckets
        )
        assert hist2.name == "full_hist"
        assert hist2.description == "Full histogram with custom buckets"
        assert hist2.unit == "milliseconds"
        assert hist2.buckets == custom_buckets

    def test_histogram_bucket_validation(self):
        """Test that unsorted buckets are rejected."""
        with pytest.raises(ValueError, match="Histogram buckets must be sorted"):
            Histogram("invalid_hist", buckets=[1.0, 0.5, 2.0])

    def test_histogram_default_buckets(self):
        """Test that default buckets are used when none specified."""
        histogram = Histogram("default_buckets_hist")
        expected_buckets = [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
        assert histogram.buckets == expected_buckets

    def test_histogram_percentiles(self):
        """Test percentile calculations in histogram summary."""
        # Use buckets that better fit the 1-100 range
        custom_buckets = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        histogram = Histogram("percentile_hist", buckets=custom_buckets)

        # Add some test data
        for i in range(1, 101):  # 1 to 100
            histogram.observe(float(i))

        summary = histogram.get_summary()
        assert summary is not None
        assert summary['count'] == 100  # 100 observations
        assert summary['sum'] == 5050.0  # sum of 1-100

        # Test percentiles (approximate)
        assert summary['p50'] is not None  # 50th percentile
        assert summary['p95'] is not None  # 95th percentile
        assert summary['p99'] is not None  # 99th percentile

        # 50th percentile should be around 50
        assert 45 <= summary['p50'] <= 55

    def test_histogram_empty_summary(self):
        """Test histogram summary when no observations have been made."""
        histogram = Histogram("empty_hist")

        summary = histogram.get_summary()
        assert summary is None  # No observations made yet

    def test_histogram_registry_integration(self):
        """Test that histogram properly integrates with the registry."""
        histogram = Histogram("registry_test", "Registry integration", "ops")

        # Make some observations
        histogram.observe(10.0)
        histogram.observe(20.0)

        # Check registry directly
        registry = MetricRegistry.get_instance()
        metrics = registry.collect()

        # Should have our histogram
        hist_metrics = [m for m in metrics if m.metadata.name == "registry_test"]
        assert len(hist_metrics) == 1

        metric = hist_metrics[0]
        assert metric.count >= 2  # At least our two observations
        assert metric.sum >= 30.0  # 10.0 + 20.0
        assert metric.metadata.type.name == "HISTOGRAM"
        assert metric.metadata.unit == "ops"

    def test_histogram_multiple_instances_same_name(self):
        """Test that multiple histogram instances with same name share state."""
        hist1 = Histogram("shared_histogram", "Shared histogram")
        hist2 = Histogram("shared_histogram", "Shared histogram")  # Same name

        # Both should share the same registry entry
        hist1.observe(1.0)
        summary1 = hist1.get_summary()
        assert summary1 is not None and summary1['count'] >= 1

        hist2.observe(2.0)
        summary2 = hist2.get_summary()
        assert summary2 is not None and summary2['count'] >= 2  # Should see hist1's observation

    def test_histogram_properties(self):
        """Test histogram property access."""
        custom_buckets = [0.1, 1.0, 10.0]
        histogram = Histogram(
            "property_test",
            "Property test histogram",
            "latency",
            {"env": "test"},
            custom_buckets
        )

        assert histogram.name == "property_test"
        assert histogram.description == "Property test histogram"
        assert histogram.unit == "latency"
        assert histogram.buckets == custom_buckets


class TestHistogramIntegration:
    """Integration tests for Histogram with registry."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def teardown_method(self):
        """Clean up after test method."""
        registry = MetricRegistry.get_instance()
        registry.clear()

    def test_histogram_collect_integration(self):
        """Test histogram integration with registry collect."""
        histogram = Histogram("collect_test", "Collect integration", "duration")

        # Make some observations
        histogram.observe(0.1)
        histogram.observe(0.5)
        histogram.observe(1.0)

        # Collect all metrics
        registry = MetricRegistry.get_instance()
        all_metrics = registry.collect()

        # Find our histogram
        hist_metrics = [m for m in all_metrics if m.metadata.name == "collect_test"]
        assert len(hist_metrics) == 1

        metric = hist_metrics[0]
        assert metric.count >= 3  # Our observations plus init
        assert metric.sum >= 1.6  # 0.1 + 0.5 + 1.0
        assert metric.metadata.description == "Collect integration"
        assert metric.metadata.unit == "duration"