"""
Health check interfaces and contracts for Py_LoggingSystem observability.

This module defines the core interfaces that health check implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import List, Protocol

from .types import EHealthStatus, HealthCheckResult, HealthReport


class IHealthCheck(Protocol):
    """
    Protocol defining the interface for health check implementations.

    All health checks must implement this protocol to ensure consistent
    behavior across the observability system.
    """

    @property
    def name(self) -> str:
        """
        Return the unique name identifier for this health check.

        Returns:
            str: A unique, descriptive name for this health check
        """
        ...

    def check(self) -> HealthCheckResult:
        """
        Perform the health check and return the result.

        Returns:
            HealthCheckResult: The result of the health check operation
        """
        ...

    @property
    def is_critical(self) -> bool:
        """
        Indicate whether this health check is critical to system operation.

        Critical health checks can cause the overall system health to be
        marked as unhealthy even if other checks pass.

        Returns:
            bool: True if this check is critical, False otherwise
        """
        ...


class CompositeHealthCheck:
    """
    Composite health check that aggregates multiple individual health checks.

    This class combines multiple health checks and determines an overall
    health status based on the results of all constituent checks.
    """

    def __init__(self, name: str, checks: List[IHealthCheck], critical_only: bool = False):
        """
        Initialize the composite health check.

        Args:
            name: Unique name for this composite check
            checks: List of health checks to aggregate
            critical_only: If True, only consider critical checks for overall status
        """
        self._name = name
        self._checks = checks
        self._critical_only = critical_only

    @property
    def name(self) -> str:
        """Return the name of this composite health check."""
        return self._name

    @property
    def is_critical(self) -> bool:
        """Composite checks are typically critical by default."""
        return True

    def check(self) -> HealthReport:
        """
        Perform all constituent health checks and aggregate the results.

        Returns:
            HealthReport: Comprehensive report of all health check results
        """
        import time
        from datetime import datetime, timezone

        start_time = time.time()
        results = []

        # Execute all checks
        for check in self._checks:
            if not self._critical_only or check.is_critical:
                result = check.check()
                results.append(result)

        total_duration = (time.time() - start_time) * 1000  # Convert to milliseconds

        # Determine overall status
        overall_status = self._calculate_overall_status(results)

        return HealthReport(
            overall_status=overall_status,
            checks=results,
            timestamp=datetime.now(timezone.utc),
            total_duration_ms=total_duration,
        )

    def _calculate_overall_status(self, results: List[HealthCheckResult]) -> EHealthStatus:
        """
        Calculate the overall health status from individual check results.

        Logic:
        - If any critical check is UNHEALTHY → UNHEALTHY
        - If any check is UNHEALTHY → DEGRADED (unless critical_only mode)
        - If any check is DEGRADED → DEGRADED
        - Otherwise → HEALTHY

        Args:
            results: List of individual health check results

        Returns:
            EHealthStatus: The overall health status
        """
        if not results:
            return EHealthStatus.HEALTHY

        has_unhealthy_critical = any(
            result.status == EHealthStatus.UNHEALTHY and
            any(check.is_critical for check in self._checks if check.name == result.name)
            for result in results
        )

        if has_unhealthy_critical:
            return EHealthStatus.UNHEALTHY

        has_any_unhealthy = any(result.status == EHealthStatus.UNHEALTHY for result in results)
        has_any_degraded = any(result.status == EHealthStatus.DEGRADED for result in results)

        if has_any_unhealthy:
            return EHealthStatus.DEGRADED if self._critical_only else EHealthStatus.UNHEALTHY

        if has_any_degraded:
            return EHealthStatus.DEGRADED

        return EHealthStatus.HEALTHY