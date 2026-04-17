"""
Unit tests for Prometheus exporter in Py_LoggingSystem.

Tests the PrometheusExporter functionality and format validation.
"""

import pytest

from logging_system.observability.metrics.exporters.prometheus import PrometheusExporter
from logging_system.observability.metrics.registry import MetricRegistry
from logging_system.observability.metrics.instruments import Counter, Gauge, Histogram


class TestPrometheusExporter:
    """Test the Prometheus exporter."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        self.registry = MetricRegistry.get_instance()
        self.registry.clear()
        self.exporter = PrometheusExporter(self.registry)

    def teardown_method(self):
        """Clean up after test method."""
        self.registry.clear()

    def test_prometheus_export_counters(self):
        """Test exporting counters in Prometheus format."""
        # Create a counter
        counter = Counter("test_counter", "Test counter", "requests")

        # Increment counter
        counter.increment(5)
        counter.increment(3, labels={"endpoint": "/api"})

        # Export
        output = self.exporter.export()

        # Verify format
        lines = output.strip().split('\n')

        # Should have TYPE and HELP
        assert "# TYPE test_counter counter" in lines
        assert "# HELP test_counter Test counter" in lines

        # Should have counter values
        assert "test_counter 5" in lines
        assert 'test_counter{endpoint="/api"} 3' in lines

    def test_prometheus_export_gauges(self):
        """Test exporting gauges in Prometheus format."""
        # Create a gauge
        gauge = Gauge("test_gauge", "Test gauge", "bytes")

        # Set gauge values
        gauge.set(1024)
        gauge.set(2048, labels={"region": "us-west"})

        # Export
        output = self.exporter.export()

        # Verify format
        lines = output.strip().split('\n')

        # Should have TYPE and HELP
        assert "# TYPE test_gauge gauge" in lines
        assert "# HELP test_gauge Test gauge" in lines

        # Should have gauge values
        assert "test_gauge 1024" in lines
        assert 'test_gauge{region="us-west"} 2048' in lines

    def test_prometheus_export_histograms(self):
        """Test exporting histograms in Prometheus format."""
        # Create a histogram
        histogram = Histogram("test_histogram", "Test histogram", "seconds",
                            buckets=[1.0, 5.0, 10.0])

        # Observe values
        histogram.observe(0.5)
        histogram.observe(3.0)
        histogram.observe(7.0)
        histogram.observe(15.0)

        # Export
        output = self.exporter.export()

        # Verify format
        lines = output.strip().split('\n')

        # Should have TYPE and HELP
        assert "# TYPE test_histogram histogram" in lines
        assert "# HELP test_histogram Test histogram" in lines

        # Should have bucket lines
        assert 'test_histogram_bucket{le="1.0"} 1' in lines
        assert 'test_histogram_bucket{le="5.0"} 2' in lines
        assert 'test_histogram_bucket{le="10.0"} 3' in lines
        assert 'test_histogram_bucket{le="+Inf"} 4' in lines

        # Should have count and sum
        assert "test_histogram_count 4" in lines
        assert "test_histogram_sum 25.5" in lines

    def test_prometheus_format_valid(self):
        """Test that exported format is valid Prometheus text format."""
        # Create various metrics
        counter = Counter("requests_total", "Total requests", "requests")
        gauge = Gauge("memory_usage", "Memory usage", "bytes")
        histogram = Histogram("request_duration", "Request duration", "seconds")

        counter.increment(100)
        gauge.set(1024 * 1024)
        histogram.observe(0.1)
        histogram.observe(0.5)

        output = self.exporter.export()

        # Basic validation - should not be empty and contain expected elements
        assert output
        assert "# TYPE" in output
        assert "# HELP" in output
        assert "requests_total 100" in output
        assert "memory_usage 1048576" in output
        assert "request_duration_count 2" in output

    def test_prometheus_labels_escaping(self):
        """Test that labels are properly escaped in Prometheus format."""
        counter = Counter("test_counter", "Test counter")

        # Test various label values that need escaping
        counter.increment(1, labels={"path": '/api/v1/users'})
        counter.increment(1, labels={"method": 'POST'})
        counter.increment(1, labels={'special': 'value"with"quotes'})

        output = self.exporter.export()

        # Check that quotes and special characters are escaped
        assert 'path="/api/v1/users"' in output
        assert 'method="POST"' in output
        # Quotes should be escaped
        assert 'special="value\\"with\\"quotes"' in output

    def test_prometheus_empty_registry(self):
        """Test exporting when registry is empty."""
        output = self.exporter.export()

        # Should return empty string or just newline
        assert output == "\n" or output == ""

    def test_prometheus_multiple_metrics_same_name(self):
        """Test exporting multiple metrics with same name but different labels."""
        counter = Counter("api_requests", "API requests", "requests")

        # Different label combinations
        counter.increment(10, labels={"endpoint": "/users", "method": "GET"})
        counter.increment(5, labels={"endpoint": "/users", "method": "POST"})
        counter.increment(3, labels={"endpoint": "/orders"})

        output = self.exporter.export()
        lines = output.strip().split('\n')

        # Should have TYPE and HELP once
        type_count = sum(1 for line in lines if "# TYPE api_requests counter" in line)
        help_count = sum(1 for line in lines if "# HELP api_requests API requests" in line)
        assert type_count == 1
        assert help_count == 1

        # Should have three metric lines
        metric_lines = [line for line in lines if line.startswith("api_requests") and not line.startswith("#")]
        assert len(metric_lines) == 3

        assert 'api_requests{endpoint="/orders"} 3' in metric_lines
        assert 'api_requests{endpoint="/users",method="GET"} 10' in metric_lines
        assert 'api_requests{endpoint="/users",method="POST"} 5' in metric_lines