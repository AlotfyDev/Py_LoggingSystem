"""
Health status types and data structures for Py_LoggingSystem observability.

This module defines the core types used for health checking throughout the system.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List


class EHealthStatus(Enum):
    """Enumeration of possible health statuses."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class HealthCheckResult:
    """
    Result of a single health check operation.

    This is an immutable dataclass containing the outcome of a health check.
    """

    name: str
    status: EHealthStatus
    message: str
    timestamp: datetime
    duration_ms: float
    details: Dict[str, Any]

    def is_healthy(self) -> bool:
        """Return True if this health check result indicates a healthy state."""
        return self.status == EHealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        """Convert this health check result to a dictionary representation."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "details": self.details,
        }


@dataclass
class HealthReport:
    """
    Comprehensive health report containing multiple health check results.

    This aggregates the results of all health checks performed on a system component.
    """

    overall_status: EHealthStatus
    checks: List[HealthCheckResult]
    timestamp: datetime
    total_duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert this health report to a dictionary representation."""
        return {
            "overall_status": self.overall_status.value,
            "checks": [check.to_dict() for check in self.checks],
            "timestamp": self.timestamp.isoformat(),
            "total_duration_ms": self.total_duration_ms,
            "check_count": len(self.checks),
        }