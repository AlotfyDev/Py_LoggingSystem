"""
Unit tests for health status types in Py_LoggingSystem.

Tests the core health checking data structures and their behavior.
"""

import pytest
from datetime import datetime, timezone

from logging_system.observability.health.types import (
    EHealthStatus,
    HealthCheckResult,
    HealthReport,
)


class TestEHealthStatus:
    """Test the EHealthStatus enumeration."""

    def test_health_status_enum_values(self):
        """Test that EHealthStatus contains exactly the required values."""
        expected_values = {"healthy", "degraded", "unhealthy"}
        actual_values = {status.value for status in EHealthStatus}
        assert actual_values == expected_values

        # Verify all enum members exist
        assert EHealthStatus.HEALTHY.value == "healthy"
        assert EHealthStatus.DEGRADED.value == "degraded"
        assert EHealthStatus.UNHEALTHY.value == "unhealthy"


class TestHealthCheckResult:
    """Test the HealthCheckResult dataclass."""

    def test_health_check_result_creation(self):
        """Test creating a HealthCheckResult instance."""
        timestamp = datetime.now(timezone.utc)
        result = HealthCheckResult(
            name="test_check",
            status=EHealthStatus.HEALTHY,
            message="All systems operational",
            timestamp=timestamp,
            duration_ms=15.5,
            details={"response_time": 100},
        )

        assert result.name == "test_check"
        assert result.status == EHealthStatus.HEALTHY
        assert result.message == "All systems operational"
        assert result.timestamp == timestamp
        assert result.duration_ms == 15.5
        assert result.details == {"response_time": 100}

    def test_is_healthy_true(self):
        """Test is_healthy() returns True for HEALTHY status."""
        result = HealthCheckResult(
            name="healthy_check",
            status=EHealthStatus.HEALTHY,
            message="OK",
            timestamp=datetime.now(timezone.utc),
            duration_ms=10.0,
            details={},
        )

        assert result.is_healthy() is True

    def test_is_healthy_false(self):
        """Test is_healthy() returns False for non-HEALTHY statuses."""
        degraded_result = HealthCheckResult(
            name="degraded_check",
            status=EHealthStatus.DEGRADED,
            message="Warning",
            timestamp=datetime.now(timezone.utc),
            duration_ms=10.0,
            details={},
        )

        unhealthy_result = HealthCheckResult(
            name="unhealthy_check",
            status=EHealthStatus.UNHEALTHY,
            message="Error",
            timestamp=datetime.now(timezone.utc),
            duration_ms=10.0,
            details={},
        )

        assert degraded_result.is_healthy() is False
        assert unhealthy_result.is_healthy() is False

    def test_result_to_dict(self):
        """Test converting HealthCheckResult to dictionary."""
        timestamp = datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)
        result = HealthCheckResult(
            name="api_check",
            status=EHealthStatus.HEALTHY,
            message="API responding",
            timestamp=timestamp,
            duration_ms=25.7,
            details={"latency": 25.7, "status_code": 200},
        )

        result_dict = result.to_dict()

        expected = {
            "name": "api_check",
            "status": "healthy",
            "message": "API responding",
            "timestamp": "2026-04-17T12:00:00+00:00",
            "duration_ms": 25.7,
            "details": {"latency": 25.7, "status_code": 200},
        }

        assert result_dict == expected


class TestHealthReport:
    """Test the HealthReport dataclass."""

    def test_health_report_creation(self):
        """Test creating a HealthReport instance."""
        timestamp = datetime.now(timezone.utc)

        check1 = HealthCheckResult(
            name="db_check",
            status=EHealthStatus.HEALTHY,
            message="Database OK",
            timestamp=timestamp,
            duration_ms=10.0,
            details={"connections": 5},
        )

        check2 = HealthCheckResult(
            name="cache_check",
            status=EHealthStatus.DEGRADED,
            message="High latency",
            timestamp=timestamp,
            duration_ms=50.0,
            details={"latency": 150},
        )

        report = HealthReport(
            overall_status=EHealthStatus.DEGRADED,
            checks=[check1, check2],
            timestamp=timestamp,
            total_duration_ms=60.0,
        )

        assert report.overall_status == EHealthStatus.DEGRADED
        assert len(report.checks) == 2
        assert report.checks[0].name == "db_check"
        assert report.checks[1].name == "cache_check"
        assert report.timestamp == timestamp
        assert report.total_duration_ms == 60.0

    def test_report_to_dict(self):
        """Test converting HealthReport to dictionary."""
        timestamp = datetime(2026, 4, 17, 12, 30, 0, tzinfo=timezone.utc)

        check = HealthCheckResult(
            name="service_check",
            status=EHealthStatus.HEALTHY,
            message="Service operational",
            timestamp=timestamp,
            duration_ms=15.0,
            details={"uptime": "99.9%"},
        )

        report = HealthReport(
            overall_status=EHealthStatus.HEALTHY,
            checks=[check],
            timestamp=timestamp,
            total_duration_ms=15.0,
        )

        report_dict = report.to_dict()

        expected = {
            "overall_status": "healthy",
            "checks": [
                {
                    "name": "service_check",
                    "status": "healthy",
                    "message": "Service operational",
                    "timestamp": "2026-04-17T12:30:00+00:00",
                    "duration_ms": 15.0,
                    "details": {"uptime": "99.9%"},
                }
            ],
            "timestamp": "2026-04-17T12:30:00+00:00",
            "total_duration_ms": 15.0,
            "check_count": 1,
        }

        assert report_dict == expected