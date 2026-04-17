"""
Unit tests for AdapterHealthCheck in Py_LoggingSystem.

Tests the adapter health check implementation for monitoring logging adapters.
"""

import pytest
from unittest.mock import Mock, MagicMock

from logging_system.observability.health.checks import AdapterHealthCheck
from logging_system.observability.health.types import EHealthStatus


class TestAdapterHealthCheck:
    """Test the AdapterHealthCheck implementation."""

    def test_adapter_health_all_available(self):
        """Test adapter health check when all adapters are available."""
        # Create mock adapter registry
        mock_registry = Mock()
        mock_registry.get_all_adapters.return_value = {
            "telemetry": {"type": "opentelemetry", "status": "active"},
            "console": {"type": "console", "status": "active"},
            "file": {"type": "file", "status": "active"}
        }

        check = AdapterHealthCheck(mock_registry, "test_adapter_health")
        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert "All 3 adapters are healthy" in result.message
        assert result.details["adapter_count"] == 3
        assert result.details["healthy_count"] == 3
        assert result.details["unhealthy_count"] == 0
        assert len(result.details["healthy_adapters"]) == 3
        assert len(result.details["unhealthy_adapters"]) == 0

    def test_adapter_health_none_available(self):
        """Test adapter health check when no adapters are available."""
        # Create mock adapter registry with no adapters
        mock_registry = Mock()
        mock_registry.get_all_adapters.return_value = {}

        check = AdapterHealthCheck(mock_registry, "test_adapter_health")
        result = check.check()

        assert result.status == EHealthStatus.UNHEALTHY
        assert "No logging adapters available" in result.message
        assert result.details["adapter_count"] == 0
        assert result.details["healthy_count"] == 0
        assert result.details["unhealthy_count"] == 0
        assert len(result.details["adapters"]) == 0

    def test_adapter_health_partial(self):
        """Test adapter health check with mixed adapter availability."""
        # Create mock adapter registry with some adapters
        mock_registry = Mock()
        mock_registry.get_all_adapters.return_value = {
            "telemetry": {"type": "opentelemetry", "status": "active"},
            "console": {"type": "console", "status": "active"}
        }

        # Mock the adapter availability check to make one unavailable
        check = AdapterHealthCheck(mock_registry, "test_adapter_health")

        # Override the _is_adapter_available method for testing
        original_method = check._is_adapter_available
        def mock_is_available(adapter_name, adapter_info):
            if adapter_name == "console":
                return False  # Make console adapter unavailable
            return original_method(adapter_name, adapter_info)

        check._is_adapter_available = mock_is_available

        result = check.check()

        assert result.status == EHealthStatus.DEGRADED
        assert "2 adapters healthy, 1 degraded" in result.message
        assert result.details["adapter_count"] == 2
        assert result.details["healthy_count"] == 1
        assert result.details["unhealthy_count"] == 1
        assert "telemetry" in result.details["healthy_adapters"]
        assert "console" in result.details["unhealthy_adapters"]

    def test_adapter_health_with_list_adapters_interface(self):
        """Test adapter health check with list_adapters interface."""
        # Some registries might have list_adapters instead of get_all_adapters
        mock_registry = Mock()
        mock_registry.get_all_adapters.side_effect = AttributeError("No get_all_adapters method")
        mock_registry.list_adapters.return_value = ["telemetry", "console"]

        check = AdapterHealthCheck(mock_registry, "test_adapter_health")
        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert "All 2 adapters are healthy" in result.message
        assert result.details["adapter_count"] == 2

    def test_adapter_health_registry_exception(self):
        """Test adapter health check when registry access fails."""
        # Create mock adapter registry that raises exception
        mock_registry = Mock()
        mock_registry.get_all_adapters.side_effect = RuntimeError("Registry connection failed")
        # Also make list_adapters fail to ensure we hit the exception case
        mock_registry.list_adapters = None  # Remove the method

        check = AdapterHealthCheck(mock_registry, "test_adapter_health")
        result = check.check()

        # Since _get_registered_adapters catches the exception and returns empty dict,
        # this should behave like the "no adapters" case
        assert result.status == EHealthStatus.UNHEALTHY
        assert "No logging adapters available" in result.message
        assert result.details["adapter_count"] == 0

    def test_adapter_health_check_properties(self):
        """Test AdapterHealthCheck property access."""
        mock_registry = Mock()
        check = AdapterHealthCheck(mock_registry, "custom_name", is_critical=False)

        assert check.name == "custom_name"
        assert check.is_critical is False

        # Test default values
        check_default = AdapterHealthCheck(mock_registry)
        assert check_default.name == "adapter_health"
        assert check_default.is_critical is True

    def test_adapter_health_check_inheritance(self):
        """Test that AdapterHealthCheck properly inherits from BaseHealthCheck."""
        mock_registry = Mock()
        check = AdapterHealthCheck(mock_registry)

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


class TestAdapterHealthCheckEdgeCases:
    """Test edge cases for AdapterHealthCheck."""

    def test_adapter_health_empty_registry_response(self):
        """Test adapter health check with empty but valid registry response."""
        mock_registry = Mock()
        mock_registry.get_all_adapters.return_value = {}

        check = AdapterHealthCheck(mock_registry)
        result = check.check()

        assert result.status == EHealthStatus.UNHEALTHY
        assert "No logging adapters available" in result.message

    def test_adapter_health_adapter_availability_exception(self):
        """Test adapter health check when adapter availability check fails."""
        mock_registry = Mock()
        mock_registry.get_all_adapters.return_value = {
            "telemetry": {"type": "opentelemetry"}
        }

        check = AdapterHealthCheck(mock_registry)

        # Mock the availability check to raise exception
        def failing_check(adapter_name, adapter_info):
            raise ValueError("Availability check failed")

        check._is_adapter_available = failing_check

        result = check.check()

        assert result.status == EHealthStatus.UNHEALTHY
        assert result.details["unhealthy_count"] == 1
        assert result.details["healthy_count"] == 0
        assert "telemetry" in result.details["unhealthy_adapters"]

    def test_adapter_health_mixed_adapter_types(self):
        """Test adapter health check with different adapter types."""
        mock_registry = Mock()
        mock_registry.get_all_adapters.return_value = {
            "opentelemetry": {"type": "opentelemetry", "endpoint": "localhost:4317"},
            "console": {"type": "console", "level": "INFO"},
            "file": {"type": "file", "path": "/var/log/app.log"},
            "memory": {"type": "memory", "max_entries": 1000}
        }

        check = AdapterHealthCheck(mock_registry, "mixed_adapters")
        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert result.details["adapter_count"] == 4
        assert len(result.details["adapters"]) == 4
        assert set(result.details["adapters"]) == {"opentelemetry", "console", "file", "memory"}