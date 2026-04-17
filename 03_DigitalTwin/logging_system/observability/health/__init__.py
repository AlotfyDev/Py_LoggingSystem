"""
Health checking package for Py_LoggingSystem.
Provides health status types, interfaces, and implementations.
"""

from .interfaces import IHealthCheck, CompositeHealthCheck
from .types import EHealthStatus, HealthCheckResult, HealthReport

__all__ = [
    "EHealthStatus",
    "HealthCheckResult",
    "HealthReport",
    "IHealthCheck",
    "CompositeHealthCheck",
]