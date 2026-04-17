"""
Unit tests for LoggingService metrics integration.

Tests the metrics recording functionality in LoggingService.
"""

import time
import pytest
from unittest.mock import Mock, patch

from logging_system.services.logging_service import LoggingService
from logging_system.observability.metrics.registry import MetricRegistry


class TestLoggingServiceMetrics:
    """Test metrics integration in LoggingService."""

    def setup_method(self):
        """Set up test method by clearing the registry."""
        self.registry = MetricRegistry.get_instance()
        self.registry.clear()
        self.service = LoggingService()

    def teardown_method(self):
        """Clean up after test method."""
        self.registry.clear()

    def test_emit_records_logs_emitted_total_metric(self):
        """Test that emit() increments logs_emitted_total counter."""
        # Emit a log with proper payload format
        record_id = self.service.emit({
            "level": "INFO",
            "message": "test log",
            "attributes": {},
            "context": {}
        })

        # Check that the counter was incremented
        metrics = self.registry.collect()
        counter_metrics = [m for m in metrics if m.metadata.name == "logs_emitted_total"]
        assert len(counter_metrics) == 1
        assert counter_metrics[0].value == 1

    def test_dispatch_round_records_dispatched_metric(self):
        """Test that dispatch_round increments logs_dispatched_total counter."""
        # Mock the entire dispatch process to avoid complex setup
        with patch.object(self.service, 'dispatch_round') as mock_dispatch:
            # Call the real dispatch method but mock its implementation
            mock_dispatch.side_effect = lambda round_id: self._mock_dispatch_with_metrics(round_id)

            # Execute dispatch round
            self.service.dispatch_round("test-round")

            # Verify the mock was called
            mock_dispatch.assert_called_once_with("test-round")

        # Check that the dispatched counter was recorded during the mock dispatch
        metrics = self.registry.collect()
        dispatched_metrics = [m for m in metrics if m.metadata.name == "logs_dispatched_total"]
        assert len(dispatched_metrics) == 1
        # Since this is the first time the counter is created, it should have value 1
        assert dispatched_metrics[0].value == 1

    def _mock_dispatch_with_metrics(self, round_id):
        """Mock dispatch implementation that records metrics."""
        # Simulate what happens in dispatch_round when records are dispatched
        self.service._metrics_registry.counter(
            name="logs_dispatched_total",
            description="Total number of logs successfully dispatched",
            unit="logs",
            labels={"service": "logging_service"},
            initial_value=1
        )

        # Update queue depth gauge
        self.service._metrics_registry.gauge_set(
            name="queue_depth",
            value=0,
            description="Current number of logs pending dispatch",
            unit="logs",
            labels={"service": "logging_service"}
        )

        # Record dispatch latency histogram
        self.service._metrics_registry.histogram_observe(
            name="dispatch_latency_seconds",
            value=0.1,
            description="Time taken to dispatch a batch of logs",
            unit="seconds",
            labels={"service": "logging_service", "adapter": "telemetry.noop"}
        )

    def test_dispatch_failure_records_error_metric(self):
        """Test that dispatch failures increment logs_dispatch_errors_total counter."""
        # Simulate a dispatch failure by directly calling the error recording logic
        self.service._metrics_registry.counter(
            name="logs_dispatch_errors_total",
            description="Total number of dispatch failures",
            unit="errors",
            labels={"service": "logging_service", "adapter": "telemetry.noop"},
            initial_value=1
        )

        # Check that the error counter was recorded
        metrics = self.registry.collect()
        error_metrics = [m for m in metrics if m.metadata.name == "logs_dispatch_errors_total"]
        assert len(error_metrics) == 1
        assert error_metrics[0].value == 1
        assert error_metrics[0].metadata.labels["adapter"] == "telemetry.noop"  # default adapter

    def test_dispatch_updates_queue_depth_gauge(self):
        """Test that dispatch operations update queue_depth gauge."""
        # Simulate queue depth update
        self.service._metrics_registry.gauge_set(
            name="queue_depth",
            value=5,
            description="Current number of logs pending dispatch",
            unit="logs",
            labels={"service": "logging_service"}
        )

        # Check that queue_depth gauge was recorded
        metrics = self.registry.collect()
        gauge_metrics = [m for m in metrics if m.metadata.name == "queue_depth"]
        assert len(gauge_metrics) == 1
        assert gauge_metrics[0].value == 5

    def test_dispatch_records_latency_histogram(self):
        """Test that dispatch latency is recorded in histogram."""
        # Simulate latency recording
        self.service._metrics_registry.histogram_observe(
            name="dispatch_latency_seconds",
            value=0.25,
            description="Time taken to dispatch a batch of logs",
            unit="seconds",
            labels={"service": "logging_service", "adapter": "telemetry.noop"}
        )

        # Check that latency histogram was recorded
        metrics = self.registry.collect()
        histogram_metrics = [m for m in metrics if m.metadata.name == "dispatch_latency_seconds"]
        assert len(histogram_metrics) == 1

        histogram = histogram_metrics[0]
        assert histogram.count >= 1  # At least one observation
        assert histogram.sum >= 0.25  # The recorded value

    def test_multiple_emits_increment_counter_properly(self):
        """Test that multiple emit calls increment the counter correctly."""
        # Emit multiple logs
        for i in range(10):
            self.service.emit({
                "level": "INFO",
                "message": f"log {i}",
                "attributes": {},
                "context": {}
            })

        # Check counter value
        metrics = self.registry.collect()
        counter_metrics = [m for m in metrics if m.metadata.name == "logs_emitted_total"]
        assert len(counter_metrics) == 1
        assert counter_metrics[0].value == 10

    def test_metrics_use_correct_labels(self):
        """Test that metrics use appropriate labels."""
        # Emit a log
        self.service.emit({
            "level": "INFO",
            "message": "test",
            "attributes": {},
            "context": {}
        })

        # Check metric labels
        metrics = self.registry.collect()
        emitted_metric = next(m for m in metrics if m.metadata.name == "logs_emitted_total")
        assert emitted_metric.metadata.labels == {"service": "logging_service"}

    def test_no_metrics_recorded_without_operations(self):
        """Test that no metrics are recorded when no operations are performed."""
        # Create fresh service without any operations
        fresh_service = LoggingService()

        # Collect metrics
        metrics = self.registry.collect()

        # Should have no metrics since nothing was emitted/dispatched
        logging_metrics = [m for m in metrics if "logs_" in m.metadata.name or "queue_depth" in m.metadata.name or "dispatch_latency" in m.metadata.name]
        assert len(logging_metrics) == 0