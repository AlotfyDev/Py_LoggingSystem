"""
Health endpoint implementation for Py_LoggingSystem observability.

This module provides HTTP endpoint handlers for health checking, following
Kubernetes and cloud-native health check patterns with /health, /ready, and /live.
"""

import time
from typing import Dict, List, Optional

from .interfaces import IHealthCheck
from .types import EHealthStatus, HealthReport


class HealthEndpoint:
    """
    HTTP endpoint handler for health checks following cloud-native patterns.

    Provides three standard health check endpoints:
    - /health: Comprehensive health check of all components
    - /ready: Readiness check for critical components only
    - /live: Liveness check (basic process health)

    This follows Kubernetes and cloud-native health check conventions.
    """

    def __init__(self, health_checks: List[IHealthCheck]):
        """
        Initialize the health endpoint with a list of health checks.

        Args:
            health_checks: List of health checks to monitor
        """
        self._health_checks = health_checks

    def get_health(self) -> Dict[str, any]:
        """
        Comprehensive health check endpoint (/health).

        Executes all health checks and returns aggregated results.
        This is typically used by load balancers and monitoring systems
        to determine if the service should receive traffic.

        Returns:
            Dict containing:
            - status: Overall health status ("healthy", "degraded", "unhealthy")
            - checks: Individual check results
            - timestamp: When the check was performed
            - duration_ms: Total time taken for all checks
        """
        start_time = time.time()
        check_results = []

        # Execute all health checks
        for check in self._health_checks:
            try:
                result = check.check()
                check_results.append({
                    "name": result.name,
                    "status": result.status.value,
                    "message": result.message,
                    "duration_ms": result.duration_ms,
                    "timestamp": result.timestamp.isoformat(),
                    "details": result.details,
                    "is_critical": check.is_critical
                })
            except Exception as exc:
                # If a health check fails completely, report it as unhealthy
                check_results.append({
                    "name": check.name,
                    "status": EHealthStatus.UNHEALTHY.value,
                    "message": f"Health check failed: {str(exc)}",
                    "duration_ms": 0.0,
                    "timestamp": self._get_current_timestamp().isoformat(),
                    "details": {"error": str(exc), "error_type": type(exc).__name__},
                    "is_critical": check.is_critical
                })

        total_duration = (time.time() - start_time) * 1000

        # Determine overall status
        overall_status = self._determine_overall_status(check_results)

        return {
            "status": overall_status.value,
            "checks": check_results,
            "timestamp": self._get_current_timestamp().isoformat(),
            "total_duration_ms": total_duration,
            "check_count": len(check_results)
        }

    def get_ready(self) -> Dict[str, any]:
        """
        Readiness check endpoint (/ready).

        Checks only critical health components to determine if the service
        is ready to receive traffic. This is used by orchestrators like
        Kubernetes to decide when to route traffic to the service.

        Returns:
            Dict containing readiness status and critical check results
        """
        start_time = time.time()
        critical_checks = [check for check in self._health_checks if check.is_critical]
        check_results = []

        # Execute only critical health checks
        for check in critical_checks:
            try:
                result = check.check()
                check_results.append({
                    "name": result.name,
                    "status": result.status.value,
                    "message": result.message,
                    "duration_ms": result.duration_ms,
                    "timestamp": result.timestamp.isoformat(),
                    "details": result.details
                })
            except Exception as exc:
                check_results.append({
                    "name": check.name,
                    "status": EHealthStatus.UNHEALTHY.value,
                    "message": f"Critical health check failed: {str(exc)}",
                    "duration_ms": 0.0,
                    "timestamp": self._get_current_timestamp().isoformat(),
                    "details": {"error": str(exc), "error_type": type(exc).__name__}
                })

        total_duration = (time.time() - start_time) * 1000

        # For readiness, any unhealthy critical check means not ready
        has_unhealthy_critical = any(
            result["status"] == EHealthStatus.UNHEALTHY.value
            for result in check_results
        )

        if not critical_checks:
            # No critical checks defined, assume ready
            overall_status = EHealthStatus.HEALTHY
        elif has_unhealthy_critical:
            overall_status = EHealthStatus.UNHEALTHY
        else:
            # Check if any critical checks are degraded
            has_degraded_critical = any(
                result["status"] == EHealthStatus.DEGRADED.value
                for result in check_results
            )
            overall_status = EHealthStatus.DEGRADED if has_degraded_critical else EHealthStatus.HEALTHY

        return {
            "status": overall_status.value,
            "checks": check_results,
            "timestamp": self._get_current_timestamp().isoformat(),
            "total_duration_ms": total_duration,
            "critical_check_count": len(critical_checks)
        }

    def get_live(self) -> Dict[str, any]:
        """
        Liveness check endpoint (/live).

        Performs a basic liveness check to determine if the process is running.
        This is used by orchestrators to determine if the service needs to be restarted.

        Returns:
            Dict containing basic liveness status
        """
        return {
            "status": EHealthStatus.HEALTHY.value,
            "message": "Service is alive",
            "timestamp": self._get_current_timestamp().isoformat(),
            "process_info": {
                "pid": self._get_process_id(),
                "uptime_seconds": self._get_process_uptime()
            }
        }

    def _determine_overall_status(self, check_results: List[Dict[str, any]]) -> EHealthStatus:
        """
        Determine the overall health status from individual check results.

        Logic follows standard health check aggregation:
        - UNHEALTHY if any check is unhealthy
        - DEGRADED if any check is degraded (but none unhealthy)
        - HEALTHY if all checks are healthy

        Args:
            check_results: List of individual check result dictionaries

        Returns:
            EHealthStatus: Overall health status
        """
        if not check_results:
            return EHealthStatus.HEALTHY

        has_unhealthy = any(result["status"] == EHealthStatus.UNHEALTHY.value for result in check_results)
        has_degraded = any(result["status"] == EHealthStatus.DEGRADED.value for result in check_results)

        if has_unhealthy:
            return EHealthStatus.UNHEALTHY
        elif has_degraded:
            return EHealthStatus.DEGRADED
        else:
            return EHealthStatus.HEALTHY

    def _get_current_timestamp(self):
        """Get the current timestamp."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)

    def _get_process_id(self) -> Optional[int]:
        """Get the current process ID."""
        import os
        try:
            return os.getpid()
        except Exception:
            return None

    def _get_process_uptime(self) -> Optional[float]:
        """Get the process uptime in seconds."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return time.time() - process.create_time()
        except Exception:
            # If psutil is not available or fails, return None
            return None