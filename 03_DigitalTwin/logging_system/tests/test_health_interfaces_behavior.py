"""
Unit tests for health check interfaces in Py_LoggingSystem.

Tests the IHealthCheck protocol and CompositeHealthCheck implementation.
"""

import pytest
from datetime import datetime, timezone
from typing import List

from logging_system.observability.health.interfaces import (
    IHealthCheck,
    CompositeHealthCheck,
)
from logging_system.observability.health.types import (
    EHealthStatus,
    HealthCheckResult,
    HealthReport,
)


class MockHealthCheck:
    """Mock implementation of IHealthCheck for testing."""

    def __init__(self, name: str, status: EHealthStatus, is_critical: bool = False):
        self._name = name
        self._status = status
        self._is_critical = is_critical

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_critical(self) -> bool:
        return self._is_critical

    def check(self) -> HealthCheckResult:
        return HealthCheckResult(
            name=self._name,
            status=self._status,
            message=f"Mock check result for {self._name}",
            timestamp=datetime.now(timezone.utc),
            duration_ms=10.0,
            details={"mock": True},
        )


class TestIHealthCheck:
    """Test the IHealthCheck protocol contract."""

    def test_health_check_interface_contract(self):
        """Test that IHealthCheck defines the required interface."""
        # Create a mock implementation
        check = MockHealthCheck("test_check", EHealthStatus.HEALTHY)

        # Verify protocol compliance
        assert hasattr(check, 'name')
        assert hasattr(check, 'check')
        assert hasattr(check, 'is_critical')

        # Test the interface
        assert check.name == "test_check"
        assert check.is_critical is False

        result = check.check()
        assert isinstance(result, HealthCheckResult)
        assert result.name == "test_check"
        assert result.status == EHealthStatus.HEALTHY


class TestCompositeHealthCheck:
    """Test the CompositeHealthCheck implementation."""

    def test_composite_all_healthy(self):
        """Test composite check when all constituent checks are healthy."""
        checks = [
            MockHealthCheck("check1", EHealthStatus.HEALTHY),
            MockHealthCheck("check2", EHealthStatus.HEALTHY),
            MockHealthCheck("check3", EHealthStatus.HEALTHY),
        ]

        composite = CompositeHealthCheck("all_healthy", checks)
        report = composite.check()

        assert isinstance(report, HealthReport)
        assert report.overall_status == EHealthStatus.HEALTHY
        assert len(report.checks) == 3
        assert all(check.status == EHealthStatus.HEALTHY for check in report.checks)

    def test_composite_one_unhealthy(self):
        """Test composite check when one check is unhealthy."""
        checks = [
            MockHealthCheck("check1", EHealthStatus.HEALTHY),
            MockHealthCheck("check2", EHealthStatus.UNHEALTHY),
            MockHealthCheck("check3", EHealthStatus.HEALTHY),
        ]

        composite = CompositeHealthCheck("one_unhealthy", checks)
        report = composite.check()

        assert isinstance(report, HealthReport)
        assert report.overall_status == EHealthStatus.UNHEALTHY
        assert len(report.checks) == 3

    def test_composite_mixed_status(self):
        """Test composite check with mixed healthy/degraded status."""
        checks = [
            MockHealthCheck("check1", EHealthStatus.HEALTHY),
            MockHealthCheck("check2", EHealthStatus.DEGRADED),
            MockHealthCheck("check3", EHealthStatus.HEALTHY),
        ]

        composite = CompositeHealthCheck("mixed_status", checks)
        report = composite.check()

        assert isinstance(report, HealthReport)
        assert report.overall_status == EHealthStatus.DEGRADED
        assert len(report.checks) == 3

    def test_composite_with_critical_check(self):
        """Test composite check behavior with critical unhealthy check."""
        checks = [
            MockHealthCheck("check1", EHealthStatus.HEALTHY, is_critical=False),
            MockHealthCheck("check2", EHealthStatus.UNHEALTHY, is_critical=True),
            MockHealthCheck("check3", EHealthStatus.HEALTHY, is_critical=False),
        ]

        composite = CompositeHealthCheck("critical_unhealthy", checks)
        report = composite.check()

        assert isinstance(report, HealthReport)
        assert report.overall_status == EHealthStatus.UNHEALTHY  # Critical check fails
        assert len(report.checks) == 3

    def test_composite_critical_only_mode(self):
        """Test composite check in critical-only mode."""
        checks = [
            MockHealthCheck("check1", EHealthStatus.HEALTHY, is_critical=False),
            MockHealthCheck("check2", EHealthStatus.UNHEALTHY, is_critical=False),
            MockHealthCheck("check3", EHealthStatus.HEALTHY, is_critical=True),
        ]

        composite = CompositeHealthCheck("critical_only", checks, critical_only=True)
        report = composite.check()

        assert isinstance(report, HealthReport)
        assert report.overall_status == EHealthStatus.HEALTHY  # Only critical check executed
        assert len(report.checks) == 1  # Only the critical check
        assert report.checks[0].name == "check3"

    def test_composite_empty_checks(self):
        """Test composite check with no constituent checks."""
        composite = CompositeHealthCheck("empty", [])
        report = composite.check()

        assert isinstance(report, HealthReport)
        assert report.overall_status == EHealthStatus.HEALTHY
        assert len(report.checks) == 0

    def test_composite_properties(self):
        """Test composite check property access."""
        checks = [MockHealthCheck("test", EHealthStatus.HEALTHY)]
        composite = CompositeHealthCheck("test_composite", checks)

        assert composite.name == "test_composite"
        assert composite.is_critical is True  # Composites are critical by default