"""
Unit tests for DLQHealthCheck in Py_LoggingSystem.

Tests the DLQ health check implementation for monitoring dead letter queue statistics.
"""

import pytest
from unittest.mock import Mock

from logging_system.observability.health.checks import DLQHealthCheck
from logging_system.observability.health.types import EHealthStatus


class MockDLQ:
    """Mock DLQ for testing."""

    def __init__(self, total_entries=0, failed_count=0, pending_count=0):
        self.total_entries = total_entries
        self.failed_count = failed_count
        self.pending_count = pending_count

    def get_statistics(self):
        return {
            'total_entries': self.total_entries,
            'failed_count': self.failed_count,
            'pending_count': self.pending_count
        }


class TestDLQHealthCheck:
    """Test the DLQHealthCheck implementation."""

    def test_dlq_health_healthy(self):
        """Test DLQ health check when statistics are within normal ranges."""
        dlq = MockDLQ(total_entries=50, failed_count=10, pending_count=40)
        check = DLQHealthCheck(dlq, "test_dlq")

        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert "DLQ healthy: 50 total entries" in result.message
        assert result.details["total_entries"] == 50
        assert result.details["failed_count"] == 10
        assert result.details["pending_count"] == 40
        assert result.details["dlq_status"] == "normal"

    def test_dlq_health_degraded(self):
        """Test DLQ health check when pending messages exceed threshold."""
        dlq = MockDLQ(total_entries=1200, failed_count=50, pending_count=1150)
        check = DLQHealthCheck(dlq, "test_dlq")

        result = check.check()

        assert result.status == EHealthStatus.DEGRADED
        assert "DLQ has high pending messages: 1150" in result.message
        assert result.details["dlq_status"] == "warning"

    def test_dlq_health_unhealthy(self):
        """Test DLQ health check when failed messages exceed threshold."""
        dlq = MockDLQ(total_entries=200, failed_count=150, pending_count=50)
        check = DLQHealthCheck(dlq, "test_dlq")

        result = check.check()

        assert result.status == EHealthStatus.UNHEALTHY
        assert "DLQ has excessive failed messages: 150" in result.message
        assert result.details["dlq_status"] == "critical"

    def test_dlq_health_boundary_failed_threshold(self):
        """Test DLQ health check at exact failed threshold."""
        dlq = MockDLQ(total_entries=150, failed_count=100, pending_count=50)
        check = DLQHealthCheck(dlq, "test_dlq", failed_threshold=100)

        result = check.check()

        # Should be exactly at threshold - still healthy
        assert result.status == EHealthStatus.HEALTHY

    def test_dlq_health_boundary_pending_threshold(self):
        """Test DLQ health check at exact pending threshold."""
        dlq = MockDLQ(total_entries=1100, failed_count=50, pending_count=1000)
        check = DLQHealthCheck(dlq, "test_dlq", pending_threshold=1000)

        result = check.check()

        # Should be exactly at threshold - still healthy
        assert result.status == EHealthStatus.HEALTHY

    def test_dlq_health_custom_thresholds(self):
        """Test DLQ health check with custom thresholds."""
        dlq = MockDLQ(total_entries=50, failed_count=5, pending_count=45)

        # Set custom thresholds
        check = DLQHealthCheck(
            dlq,
            "test_dlq",
            failed_threshold=10,   # Custom failed threshold
            pending_threshold=50   # Custom pending threshold
        )

        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert result.details["failed_threshold"] == 10
        assert result.details["pending_threshold"] == 50

    def test_dlq_health_empty_dlq(self):
        """Test DLQ health check with empty DLQ."""
        dlq = MockDLQ(total_entries=0, failed_count=0, pending_count=0)
        check = DLQHealthCheck(dlq, "test_dlq")

        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert result.details["total_entries"] == 0
        assert result.details["failed_count"] == 0
        assert result.details["pending_count"] == 0

    def test_dlq_health_statistics_exception(self):
        """Test DLQ health check when statistics retrieval fails."""
        dlq = Mock()
        dlq.get_statistics.side_effect = RuntimeError("Statistics unavailable")

        check = DLQHealthCheck(dlq, "test_dlq")
        result = check.check()

        assert result.status == EHealthStatus.UNHEALTHY
        assert "Failed to check DLQ health" in result.message
        assert "Statistics unavailable" in result.details["error"]
        assert result.details["total_entries"] == 0

    def test_dlq_health_with_len_interface(self):
        """Test DLQ health check with basic __len__ interface."""
        # Create a simple object with __len__ that returns an integer
        class SimpleDLQ:
            def __len__(self):
                return 25

        dlq = SimpleDLQ()

        check = DLQHealthCheck(dlq, "len_dlq")
        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert result.details["total_entries"] == 25
        assert result.details["failed_count"] == 0
        assert result.details["pending_count"] == 25  # Fallback assumption

    def test_dlq_health_not_critical(self):
        """Test that DLQ health check is not critical by default."""
        dlq = MockDLQ(total_entries=100, failed_count=50, pending_count=50)
        check = DLQHealthCheck(dlq, "test_dlq")

        assert check.is_critical is False

        # With failed_count=50 (below threshold of 100), it should be healthy
        result = check.check()
        assert result.status == EHealthStatus.HEALTHY
        assert check.is_critical is False

    def test_dlq_health_with_stats_method(self):
        """Test DLQ health check with alternative stats() method."""
        dlq = Mock()
        dlq.get_statistics = Mock(side_effect=AttributeError("No get_statistics"))
        dlq.stats = Mock(return_value={
            'total_entries': 75,
            'failed_count': 25,
            'pending_count': 50
        })

        check = DLQHealthCheck(dlq, "stats_dlq")
        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert result.details["total_entries"] == 75
        assert result.details["failed_count"] == 25
        assert result.details["pending_count"] == 50

    def test_dlq_health_properties(self):
        """Test DLQHealthCheck property access."""
        dlq = MockDLQ()
        check = DLQHealthCheck(dlq, "custom_dlq", is_critical=True)

        assert check.name == "custom_dlq"
        assert check.is_critical is True  # Can be overridden

        # Test default values
        check_default = DLQHealthCheck(dlq)
        assert check_default.name == "dlq_health"
        assert check_default.is_critical is False  # DLQ is not critical by default

    def test_dlq_health_inheritance(self):
        """Test that DLQHealthCheck properly inherits from BaseHealthCheck."""
        dlq = MockDLQ()
        check = DLQHealthCheck(dlq)

        # Should have all BaseHealthCheck methods
        assert hasattr(check, 'check')
        assert hasattr(check, 'name')
        assert hasattr(check, 'is_critical')

        # Should be able to call check() method
        result = check.check()
        assert hasattr(result, 'status')
        assert hasattr(result, 'message')
        assert hasattr(result, 'timestamp')
        assert hasattr(result, 'duration_ms')