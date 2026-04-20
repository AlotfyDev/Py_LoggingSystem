"""
Unit tests for the BaseHealthCheck abstract class in Py_LoggingSystem.

Tests the base health check functionality and common behavior.
"""

import pytest
from unittest.mock import Mock, patch

from logging_system.observability.health.base import BaseHealthCheck
from logging_system.observability.health.types import EHealthStatus, HealthCheckResult


class TestableHealthCheck(BaseHealthCheck):
    """Concrete implementation of BaseHealthCheck for testing."""

    def __init__(self, name: str, is_critical: bool = True, mock_result=None):
        super().__init__(name, is_critical)
        self.mock_result = mock_result or (EHealthStatus.HEALTHY, "OK", {"test": True})

    def _perform_health_check(self):
        return self.mock_result


class TestBaseHealthCheck:
    """Test the BaseHealthCheck abstract class."""

    def test_base_health_check_creation(self):
        """Test creating a BaseHealthCheck instance."""
        check = TestableHealthCheck("test_check")

        assert check.name == "test_check"
        assert check.is_critical is True  # Default value

    def test_custom_is_critical(self):
        """Test setting custom is_critical value."""
        critical_check = TestableHealthCheck("critical_check", is_critical=True)
        non_critical_check = TestableHealthCheck("non_critical_check", is_critical=False)

        assert critical_check.is_critical is True
        assert non_critical_check.is_critical is False

    def test_default_is_critical(self):
        """Test that default is_critical returns True."""
        check = TestableHealthCheck("default_check")

        # Test the property directly
        assert check.is_critical is True

        # Test that it can be overridden in constructor
        check_false = TestableHealthCheck("false_check", is_critical=False)
        assert check_false.is_critical is False

    def test_successful_health_check(self):
        """Test a successful health check execution."""
        check = TestableHealthCheck(
            "success_check",
            mock_result=(EHealthStatus.HEALTHY, "Service is healthy", {"uptime": "99.9%"})
        )

        result = check.check()

        assert isinstance(result, HealthCheckResult)
        assert result.name == "success_check"
        assert result.status == EHealthStatus.HEALTHY
        assert result.message == "Service is healthy"
        assert result.details == {"uptime": "99.9%"}
        assert result.duration_ms >= 0  # Should have some duration
        assert result.timestamp is not None

    def test_degraded_health_check(self):
        """Test a degraded health check execution."""
        check = TestableHealthCheck(
            "degraded_check",
            mock_result=(EHealthStatus.DEGRADED, "High latency detected", {"latency": 150})
        )

        result = check.check()

        assert result.status == EHealthStatus.DEGRADED
        assert result.message == "High latency detected"
        assert result.details == {"latency": 150}

    def test_unhealthy_health_check(self):
        """Test an unhealthy health check execution."""
        check = TestableHealthCheck(
            "unhealthy_check",
            mock_result=(EHealthStatus.UNHEALTHY, "Service down", {"error": "connection_failed"})
        )

        result = check.check()

        assert result.status == EHealthStatus.UNHEALTHY
        assert result.message == "Service down"
        assert result.details == {"error": "connection_failed"}

    def test_health_check_with_exception(self):
        """Test health check behavior when an exception occurs."""
        check = TestableHealthCheck("exception_check")

        # Mock the _perform_health_check to raise an exception
        with patch.object(check, '_perform_health_check', side_effect=RuntimeError("Test error")):
            result = check.check()

            assert result.status == EHealthStatus.UNHEALTHY
            assert "failed unexpectedly" in result.message
            assert "Test error" in result.message
            assert result.details["error_type"] == "RuntimeError"
            assert result.details["error_message"] == "Test error"
            assert result.duration_ms >= 0

    def test_health_check_duration_tracking(self):
        """Test that duration is properly tracked."""
        check = TestableHealthCheck("duration_check")

        result = check.check()

        # Duration should be a positive number
        assert isinstance(result.duration_ms, float)
        assert result.duration_ms >= 0
        assert result.duration_ms < 1000  # Should be reasonably fast

    def test_health_check_timestamp(self):
        """Test that timestamp is properly set."""
        check = TestableHealthCheck("timestamp_check")

        result = check.check()

        assert result.timestamp is not None
        assert hasattr(result.timestamp, 'isoformat')  # Should be a datetime object

    def test_health_check_no_details(self):
        """Test health check when no details are provided."""
        check = TestableHealthCheck(
            "no_details_check",
            mock_result=(EHealthStatus.HEALTHY, "OK", None)
        )

        result = check.check()

        assert result.details == {}


class TestBaseHealthCheckInheritance:
    """Test that BaseHealthCheck properly enforces the interface."""

    def test_abstract_method_enforcement(self):
        """Test that _perform_health_check is abstract and must be implemented."""
        # This should fail because we can't instantiate an abstract class
        with pytest.raises(TypeError):
            BaseHealthCheck("test")  # Should fail due to abstract method

    def test_interface_compliance(self):
        """Test that TestableHealthCheck properly implements the interface."""
        check = TestableHealthCheck("interface_test")

        # Should have all required attributes
        assert hasattr(check, 'name')
        assert hasattr(check, 'is_critical')
        assert hasattr(check, 'check')

        # Should be callable
        result = check.check()
        assert isinstance(result, HealthCheckResult)