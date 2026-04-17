"""
Unit tests for HealthEndpoint in Py_LoggingSystem.

Tests the health endpoint implementation with /health, /ready, /live endpoints.
"""

import pytest
from unittest.mock import Mock, patch

from logging_system.observability.health.endpoint import HealthEndpoint
from logging_system.observability.health.types import EHealthStatus, HealthCheckResult


class MockHealthCheck:
    """Mock health check for testing."""

    def __init__(self, name: str, status: EHealthStatus, is_critical: bool = True, message: str = "OK"):
        self.name = name
        self._status = status
        self._is_critical = is_critical
        self._message = message

    @property
    def is_critical(self) -> bool:
        return self._is_critical

    def check(self) -> HealthCheckResult:
        from datetime import datetime, timezone
        return HealthCheckResult(
            name=self.name,
            status=self._status,
            message=self._message,
            timestamp=datetime.now(timezone.utc),
            duration_ms=10.0,
            details={"mock": True}
        )


class TestHealthEndpoint:
    """Test the HealthEndpoint implementation."""

    def test_get_health_all_healthy(self):
        """Test /health endpoint when all checks are healthy."""
        checks = [
            MockHealthCheck("adapter_check", EHealthStatus.HEALTHY, True),
            MockHealthCheck("container_check", EHealthStatus.HEALTHY, True),
            MockHealthCheck("dlq_check", EHealthStatus.HEALTHY, False),
        ]

        endpoint = HealthEndpoint(checks)
        result = endpoint.get_health()

        assert result["status"] == "healthy"
        assert len(result["checks"]) == 3
        assert all(check["status"] == "healthy" for check in result["checks"])
        assert result["check_count"] == 3
        assert "total_duration_ms" in result
        assert "timestamp" in result

    def test_get_health_with_degraded(self):
        """Test /health endpoint with some degraded checks."""
        checks = [
            MockHealthCheck("adapter_check", EHealthStatus.HEALTHY, True),
            MockHealthCheck("container_check", EHealthStatus.DEGRADED, True),
            MockHealthCheck("dlq_check", EHealthStatus.HEALTHY, False),
        ]

        endpoint = HealthEndpoint(checks)
        result = endpoint.get_health()

        assert result["status"] == "degraded"
        assert len(result["checks"]) == 3
        assert result["checks"][1]["status"] == "degraded"

    def test_get_health_with_unhealthy(self):
        """Test /health endpoint with unhealthy checks."""
        checks = [
            MockHealthCheck("adapter_check", EHealthStatus.HEALTHY, True),
            MockHealthCheck("container_check", EHealthStatus.UNHEALTHY, True),
            MockHealthCheck("dlq_check", EHealthStatus.HEALTHY, False),
        ]

        endpoint = HealthEndpoint(checks)
        result = endpoint.get_health()

        assert result["status"] == "unhealthy"
        assert len(result["checks"]) == 3
        assert result["checks"][1]["status"] == "unhealthy"

    def test_get_ready_all_healthy(self):
        """Test /ready endpoint when all critical checks are healthy."""
        checks = [
            MockHealthCheck("adapter_check", EHealthStatus.HEALTHY, True),
            MockHealthCheck("container_check", EHealthStatus.HEALTHY, True),
            MockHealthCheck("dlq_check", EHealthStatus.HEALTHY, False),  # Non-critical
        ]

        endpoint = HealthEndpoint(checks)
        result = endpoint.get_ready()

        assert result["status"] == "healthy"
        assert len(result["checks"]) == 2  # Only critical checks
        assert result["critical_check_count"] == 2
        assert all(check["status"] == "healthy" for check in result["checks"])

    def test_get_ready_critical_unhealthy(self):
        """Test /ready endpoint when critical checks are unhealthy."""
        checks = [
            MockHealthCheck("adapter_check", EHealthStatus.HEALTHY, True),
            MockHealthCheck("container_check", EHealthStatus.UNHEALTHY, True),
            MockHealthCheck("dlq_check", EHealthStatus.HEALTHY, False),  # Non-critical
        ]

        endpoint = HealthEndpoint(checks)
        result = endpoint.get_ready()

        assert result["status"] == "unhealthy"
        assert len(result["checks"]) == 2  # Only critical checks
        assert result["checks"][1]["status"] == "unhealthy"

    def test_get_ready_critical_degraded(self):
        """Test /ready endpoint when critical checks are degraded."""
        checks = [
            MockHealthCheck("adapter_check", EHealthStatus.HEALTHY, True),
            MockHealthCheck("container_check", EHealthStatus.DEGRADED, True),
            MockHealthCheck("dlq_check", EHealthStatus.HEALTHY, False),  # Non-critical
        ]

        endpoint = HealthEndpoint(checks)
        result = endpoint.get_ready()

        assert result["status"] == "degraded"
        assert len(result["checks"]) == 2  # Only critical checks

    def test_get_ready_no_critical_checks(self):
        """Test /ready endpoint when no critical checks are defined."""
        checks = [
            MockHealthCheck("dlq_check", EHealthStatus.HEALTHY, False),
            MockHealthCheck("cache_check", EHealthStatus.HEALTHY, False),
        ]

        endpoint = HealthEndpoint(checks)
        result = endpoint.get_ready()

        assert result["status"] == "healthy"  # Assumes ready when no critical checks
        assert len(result["checks"]) == 0
        assert result["critical_check_count"] == 0

    def test_get_live(self):
        """Test /live endpoint for basic liveness check."""
        checks = [MockHealthCheck("test", EHealthStatus.HEALTHY, True)]
        endpoint = HealthEndpoint(checks)
        result = endpoint.get_live()

        assert result["status"] == "healthy"
        assert result["message"] == "Service is alive"
        assert "timestamp" in result
        assert "process_info" in result
        assert "pid" in result["process_info"]
        assert "uptime_seconds" in result["process_info"]

    def test_get_live_without_psutil(self):
        """Test /live endpoint when psutil is not available."""
        checks = [MockHealthCheck("test", EHealthStatus.HEALTHY, True)]

        # Mock psutil import failure
        with patch.dict('sys.modules', {'psutil': None}):
            endpoint = HealthEndpoint(checks)
            result = endpoint.get_live()

            assert result["status"] == "healthy"
            assert result["process_info"]["uptime_seconds"] is None

    def test_health_check_exception_handling(self):
        """Test that health endpoint handles exceptions in individual checks."""
        # Create a check that raises an exception
        class FailingCheck:
            @property
            def name(self):
                return "failing_check"

            @property
            def is_critical(self):
                return True

            def check(self):
                raise RuntimeError("Check failed")

        checks = [
            MockHealthCheck("good_check", EHealthStatus.HEALTHY, True),
            FailingCheck()
        ]

        endpoint = HealthEndpoint(checks)
        result = endpoint.get_health()

        assert result["status"] == "unhealthy"  # Should be unhealthy due to failed check
        assert len(result["checks"]) == 2
        assert result["checks"][0]["status"] == "healthy"
        assert result["checks"][1]["status"] == "unhealthy"
        assert "Check failed" in result["checks"][1]["message"]

    def test_empty_health_checks(self):
        """Test health endpoint with no health checks."""
        endpoint = HealthEndpoint([])
        result = endpoint.get_health()

        assert result["status"] == "healthy"  # Empty checks = healthy
        assert len(result["checks"]) == 0
        assert result["check_count"] == 0

    def test_determine_overall_status_logic(self):
        """Test the overall status determination logic."""
        endpoint = HealthEndpoint([])

        # Test all healthy
        results = [
            {"status": "healthy"},
            {"status": "healthy"}
        ]
        assert endpoint._determine_overall_status(results) == EHealthStatus.HEALTHY

        # Test with degraded
        results = [
            {"status": "healthy"},
            {"status": "degraded"}
        ]
        assert endpoint._determine_overall_status(results) == EHealthStatus.DEGRADED

        # Test with unhealthy (takes precedence)
        results = [
            {"status": "healthy"},
            {"status": "unhealthy"}
        ]
        assert endpoint._determine_overall_status(results) == EHealthStatus.UNHEALTHY

        # Test mixed (unhealthy takes precedence over degraded)
        results = [
            {"status": "degraded"},
            {"status": "unhealthy"}
        ]
        assert endpoint._determine_overall_status(results) == EHealthStatus.UNHEALTHY

        # Test empty results
        assert endpoint._determine_overall_status([]) == EHealthStatus.HEALTHY


class TestHealthEndpointIntegration:
    """Integration tests for HealthEndpoint with real health checks."""

    def test_full_integration_with_real_checks(self):
        """Test full integration with actual health check implementations."""
        from logging_system.observability.health.checks import (
            AdapterHealthCheck,
            ContainerHealthCheck,
            DLQHealthCheck
        )

        # Create mock dependencies
        mock_registry = Mock()
        mock_registry.get_all_adapters.return_value = {
            "test_adapter": {"status": "active"}
        }

        mock_container = Mock()
        mock_container.get_metrics.return_value = {
            'current_size': 50,
            'max_capacity': 100,
            'utilization': 0.5
        }

        mock_dlq = Mock()
        mock_dlq.get_statistics.return_value = {
            'total_entries': 10,
            'failed_count': 2,
            'pending_count': 8
        }

        # Create real health checks
        checks = [
            AdapterHealthCheck(mock_registry, "adapter_health"),
            ContainerHealthCheck(mock_container, "container_health"),
            DLQHealthCheck(mock_dlq, "dlq_health"),
        ]

        endpoint = HealthEndpoint(checks)

        # Test /health endpoint
        health_result = endpoint.get_health()
        assert health_result["status"] == "healthy"
        assert len(health_result["checks"]) == 3

        # Test /ready endpoint (only critical checks)
        ready_result = endpoint.get_ready()
        assert ready_result["status"] == "healthy"
        assert len(ready_result["checks"]) == 2  # Adapter and container are critical

        # Test /live endpoint
        live_result = endpoint.get_live()
        assert live_result["status"] == "healthy"