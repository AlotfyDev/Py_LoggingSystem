"""
Unit tests for ContainerHealthCheck in Py_LoggingSystem.

Tests the container health check implementation for monitoring queue capacity.
"""

import pytest
from collections import deque
from unittest.mock import Mock

from logging_system.observability.health.checks import ContainerHealthCheck
from logging_system.observability.health.types import EHealthStatus


class MockContainer:
    """Mock container for testing."""

    def __init__(self, current_size=0, max_capacity=100):
        self.current_size = current_size
        self.max_capacity = max_capacity

    def get_metrics(self):
        utilization = self.current_size / self.max_capacity if self.max_capacity > 0 else 0.0
        return {
            'current_size': self.current_size,
            'max_capacity': self.max_capacity,
            'utilization': utilization
        }


class TestContainerHealthCheck:
    """Test the ContainerHealthCheck implementation."""

    def test_container_health_healthy(self):
        """Test container health check when utilization is low (healthy)."""
        container = MockContainer(current_size=30, max_capacity=100)  # 30% utilization
        check = ContainerHealthCheck(container, "test_container")

        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert "Container healthy: 30.0% utilization" in result.message
        assert result.details["current_size"] == 30
        assert result.details["max_capacity"] == 100
        assert result.details["utilization"] == 0.3
        assert result.details["utilization_percent"] == 30.0
        assert result.details["available_capacity"] == 70
        assert result.details["capacity_status"] == "normal"

    def test_container_health_degraded(self):
        """Test container health check when utilization is high (degraded)."""
        container = MockContainer(current_size=85, max_capacity=100)  # 85% utilization
        check = ContainerHealthCheck(container, "test_container")

        result = check.check()

        assert result.status == EHealthStatus.DEGRADED
        assert "Container approaching capacity: 85.0% utilization" in result.message
        assert result.details["capacity_status"] == "warning"

    def test_container_health_unhealthy(self):
        """Test container health check when utilization is critical (unhealthy)."""
        container = MockContainer(current_size=98, max_capacity=100)  # 98% utilization
        check = ContainerHealthCheck(container, "test_container")

        result = check.check()

        assert result.status == EHealthStatus.UNHEALTHY
        assert "Container critically full: 98.0% utilization" in result.message
        assert result.details["capacity_status"] == "critical"

    def test_container_health_boundary_degraded(self):
        """Test container health check at exact degraded threshold."""
        container = MockContainer(current_size=80, max_capacity=100)  # 80% utilization
        check = ContainerHealthCheck(container, "test_container", degraded_threshold=0.8)

        result = check.check()

        assert result.status == EHealthStatus.DEGRADED
        assert "approaching capacity" in result.message

    def test_container_health_boundary_unhealthy(self):
        """Test container health check at exact unhealthy threshold."""
        container = MockContainer(current_size=95, max_capacity=100)  # 95% utilization
        check = ContainerHealthCheck(container, "test_container", unhealthy_threshold=0.95)

        result = check.check()

        assert result.status == EHealthStatus.UNHEALTHY
        assert "critically full" in result.message

    def test_container_health_custom_thresholds(self):
        """Test container health check with custom thresholds."""
        container = MockContainer(current_size=75, max_capacity=100)  # 75% utilization

        # Set custom thresholds
        check = ContainerHealthCheck(
            container,
            "test_container",
            degraded_threshold=0.7,  # 70%
            unhealthy_threshold=0.9  # 90%
        )

        result = check.check()

        assert result.status == EHealthStatus.DEGRADED  # 75% > 70%
        assert result.details["degraded_threshold"] == 0.7
        assert result.details["unhealthy_threshold"] == 0.9

    def test_container_health_empty_container(self):
        """Test container health check with empty container."""
        container = MockContainer(current_size=0, max_capacity=100)
        check = ContainerHealthCheck(container, "test_container")

        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert result.details["current_size"] == 0
        assert result.details["utilization"] == 0.0
        assert result.details["available_capacity"] == 100

    def test_container_health_full_container(self):
        """Test container health check with full container."""
        container = MockContainer(current_size=100, max_capacity=100)
        check = ContainerHealthCheck(container, "test_container")

        result = check.check()

        assert result.status == EHealthStatus.UNHEALTHY
        assert result.details["utilization"] == 1.0
        assert result.details["available_capacity"] == 0

    def test_container_health_with_deque_interface(self):
        """Test container health check with collections.deque style interface."""
        # Create a deque with maxlen
        container = deque(maxlen=50)
        for i in range(10):  # 20% full
            container.append(f"item_{i}")

        check = ContainerHealthCheck(container, "deque_container")
        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert result.details["current_size"] == 10
        assert result.details["max_capacity"] == 50
        assert result.details["utilization"] == 0.2

    def test_container_health_with_len_interface(self):
        """Test container health check with basic __len__ interface."""
        # Simple list as container (no maxlen, unlimited capacity)
        container = [1, 2, 3, 4, 5]  # 5 items

        check = ContainerHealthCheck(container, "list_container")
        result = check.check()

        assert result.status == EHealthStatus.HEALTHY
        assert result.details["current_size"] == 5
        assert result.details["max_capacity"] == float('inf')
        assert result.details["utilization"] == 0.0  # No capacity limit

    def test_container_health_metrics_exception(self):
        """Test container health check when metrics retrieval fails."""
        container = Mock()
        container.get_metrics.side_effect = RuntimeError("Metrics unavailable")

        check = ContainerHealthCheck(container, "test_container")
        result = check.check()

        assert result.status == EHealthStatus.UNHEALTHY
        assert "Failed to check container health" in result.message
        assert "Metrics unavailable" in result.details["error"]
        assert result.details["current_size"] == 0
        assert result.details["max_capacity"] == 0

    def test_container_health_zero_capacity(self):
        """Test container health check with zero capacity."""
        container = MockContainer(current_size=0, max_capacity=0)

        check = ContainerHealthCheck(container, "test_container")
        result = check.check()

        # Should handle division by zero gracefully
        assert result.status == EHealthStatus.HEALTHY
        assert result.details["utilization"] == 0.0

    def test_container_health_properties(self):
        """Test ContainerHealthCheck property access."""
        container = MockContainer()
        check = ContainerHealthCheck(container, "custom_name", is_critical=False)

        assert check.name == "custom_name"
        assert check.is_critical is False

        # Test default values
        check_default = ContainerHealthCheck(container)
        assert check_default.name == "container_health"
        assert check_default.is_critical is True

    def test_container_health_inheritance(self):
        """Test that ContainerHealthCheck properly inherits from BaseHealthCheck."""
        container = MockContainer()
        check = ContainerHealthCheck(container)

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