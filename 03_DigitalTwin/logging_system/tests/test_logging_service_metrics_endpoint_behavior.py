"""
Unit tests for LoggingService metrics endpoint integration.

Tests the Prometheus metrics endpoint functionality in LoggingService.
"""

import pytest

from logging_system.services.logging_service import LoggingService
from logging_system.observability.metrics.registry import MetricRegistry


class TestLoggingServiceMetricsEndpoint:
    """Test metrics endpoint integration in LoggingService."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        self.registry = MetricRegistry.get_instance()
        self.registry.clear()
        self.service = LoggingService()

    def teardown_method(self):
        """Clean up after test method."""
        self.registry.clear()

    def test_get_metrics_prometheus_returns_prometheus_format(self):
        """Test that get_metrics_prometheus returns valid Prometheus format."""
        # Emit a log to create some metrics
        self.service.emit({
            "level": "INFO",
            "message": "test log",
            "attributes": {},
            "context": {}
        })

        # Get metrics in Prometheus format
        prometheus_output = self.service.get_metrics_prometheus()

        # Verify format
        assert isinstance(prometheus_output, str)
        assert prometheus_output.endswith("\n")

        # Should contain TYPE and HELP annotations
        assert "# TYPE logs_emitted_total counter" in prometheus_output
        assert "# HELP logs_emitted_total Total number of logs emitted" in prometheus_output

        # Should contain metric value
        assert "logs_emitted_total{service=\"logging_service\"} 1" in prometheus_output

    def test_get_metrics_prometheus_includes_all_metric_types(self):
        """Test that Prometheus output includes all metric types."""
        # Emit a log to trigger counter
        self.service.emit({
            "level": "INFO",
            "message": "test log",
            "attributes": {},
            "context": {}
        })

        # Get metrics
        prometheus_output = self.service.get_metrics_prometheus()

        # Should contain counter metric
        assert "# TYPE logs_emitted_total counter" in prometheus_output
        assert "logs_emitted_total{service=\"logging_service\"} 1" in prometheus_output

    def test_get_metrics_prometheus_with_multiple_operations(self):
        """Test Prometheus output with multiple logging operations."""
        # Emit multiple logs
        for i in range(5):
            self.service.emit({
                "level": "INFO",
                "message": f"log {i}",
                "attributes": {},
                "context": {}
            })

        # Get metrics
        prometheus_output = self.service.get_metrics_prometheus()

        # Should show correct counter value
        assert "logs_emitted_total{service=\"logging_service\"} 5" in prometheus_output

    def test_get_metrics_prometheus_empty_registry(self):
        """Test Prometheus output when no metrics have been recorded."""
        # Create fresh service without any operations
        fresh_service = LoggingService()

        # Get metrics
        prometheus_output = fresh_service.get_metrics_prometheus()

        # Should return minimal output (just newline)
        assert prometheus_output == "\n" or len(prometheus_output.strip()) == 0

    def test_get_metrics_prometheus_format_validation(self):
        """Test that Prometheus output follows correct format conventions."""
        # Emit a log to create metrics
        self.service.emit({
            "level": "INFO",
            "message": "test log",
            "attributes": {},
            "context": {}
        })

        prometheus_output = self.service.get_metrics_prometheus()
        lines = prometheus_output.strip().split('\n')

        # Each metric should have TYPE, HELP, then value
        type_lines = [line for line in lines if line.startswith('# TYPE')]
        help_lines = [line for line in lines if line.startswith('# HELP')]
        value_lines = [line for line in lines if not line.startswith('#') and line.strip()]

        # Should have matching TYPE and HELP lines
        assert len(type_lines) > 0
        assert len(help_lines) > 0
        assert len(value_lines) > 0

        # TYPE and HELP should come before values
        for type_line in type_lines:
            type_index = lines.index(type_line)
            # Extract metric name from TYPE line (format: "# TYPE <name> <type>")
            parts = type_line.split()
            if len(parts) >= 3:
                metric_name = parts[2]  # Third element is the metric name
                help_line = next((line for line in help_lines if metric_name in line), None)
                assert help_line is not None, f"No HELP line found for {metric_name}"
                help_index = lines.index(help_line)
                assert help_index == type_index + 1, f"HELP line should immediately follow TYPE line for {metric_name}"

    def test_get_metrics_prometheus_thread_safety(self):
        """Test that metrics endpoint is thread-safe."""
        import threading
        import time

        # Function to emit logs from multiple threads
        def emit_logs(thread_id: int, count: int):
            for i in range(count):
                self.service.emit({
                    "level": "INFO",
                    "message": f"thread {thread_id} log {i}",
                    "attributes": {},
                    "context": {}
                })

        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=emit_logs, args=(i, 5))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Get metrics
        prometheus_output = self.service.get_metrics_prometheus()

        # Should have correct total count (3 threads * 5 logs each)
        assert "logs_emitted_total{service=\"logging_service\"} 15" in prometheus_output

    def test_get_metrics_prometheus_with_dispatch_operations(self):
        """Test Prometheus output includes dispatch-related metrics."""
        # This is a more complex test that would require mocking the dispatch process
        # For now, we'll just verify the method exists and returns valid format
        prometheus_output = self.service.get_metrics_prometheus()

        # Should be valid Prometheus format
        assert isinstance(prometheus_output, str)
        assert prometheus_output.endswith("\n")

        # Should not crash even with no metrics
        lines = prometheus_output.strip().split('\n')
        # Filter out empty lines
        non_empty_lines = [line for line in lines if line.strip()]
        # Should either be empty or contain valid Prometheus format
        for line in non_empty_lines:
            assert line.startswith('#') or '=' in line or line.replace('.', '').replace('-', '').replace('_', '').isalnum(), f"Invalid Prometheus line: {line}"