"""
Base health check implementation for Py_LoggingSystem observability.

This module provides the abstract base class that all health check implementations
should inherit from, providing common functionality and ensuring interface compliance.
"""

import time
from abc import ABC, abstractmethod
from typing import Any

from .interfaces import IHealthCheck
from .types import EHealthStatus, HealthCheckResult


class BaseHealthCheck(ABC, IHealthCheck):
    """
    Abstract base class for all health check implementations.

    This class provides common functionality for health checks including:
    - Duration tracking
    - Error handling and result formatting
    - Default critical behavior
    - Standardized result creation
    """

    def __init__(self, name: str, is_critical: bool = True):
        """
        Initialize the base health check.

        Args:
            name: Unique name identifier for this health check
            is_critical: Whether this health check is critical (default: True)
        """
        self._name = name
        self._is_critical = is_critical

    @property
    def name(self) -> str:
        """Return the unique name identifier for this health check."""
        return self._name

    @property
    def is_critical(self) -> bool:
        """
        Return whether this health check is critical to system operation.

        Returns:
            bool: True if critical (default), False otherwise
        """
        return self._is_critical

    def check(self) -> HealthCheckResult:
        """
        Perform the health check and return the result.

        This method handles timing, error handling, and result formatting
        while delegating the actual health check logic to subclasses.

        Returns:
            HealthCheckResult: The result of the health check
        """
        start_time = time.time()

        try:
            # Delegate actual health check to subclass
            status, message, details = self._perform_health_check()

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Create result
            result = HealthCheckResult(
                name=self._name,
                status=status,
                message=message,
                timestamp=self._get_current_timestamp(),
                duration_ms=duration_ms,
                details=details or {},
            )

            return result

        except Exception as exc:
            # Handle unexpected errors
            duration_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                name=self._name,
                status=EHealthStatus.UNHEALTHY,
                message=f"Health check failed unexpectedly: {str(exc)}",
                timestamp=self._get_current_timestamp(),
                duration_ms=duration_ms,
                details={"error_type": type(exc).__name__, "error_message": str(exc)},
            )

    @abstractmethod
    def _perform_health_check(self) -> tuple[EHealthStatus, str, dict[str, Any] | None]:
        """
        Perform the actual health check logic.

        This method should be implemented by subclasses to provide
        the specific health check behavior.

        Returns:
            tuple: (status, message, details)
                - status: EHealthStatus indicating health state
                - message: Human-readable status message
                - details: Optional dictionary with additional check details
        """
        ...

    def _get_current_timestamp(self):
        """Get the current timestamp for health check results."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)