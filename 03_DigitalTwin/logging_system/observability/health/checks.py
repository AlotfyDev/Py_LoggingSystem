"""
Concrete health check implementations for Py_LoggingSystem observability.

This module contains specific health check classes that monitor different
components of the logging system, including adapters, containers, and other
critical infrastructure components.
"""

from typing import Any, Dict, List

from .base import BaseHealthCheck
from .types import EHealthStatus


class AdapterHealthCheck(BaseHealthCheck):
    """
    Health check for logging adapters.

    This health check monitors the availability and status of logging adapters
    in the adapter registry. It ensures that the system has at least one
    functional adapter for log dispatching.
    """

    def __init__(self, adapter_registry, name: str = "adapter_health", is_critical: bool = True):
        """
        Initialize the adapter health check.

        Args:
            adapter_registry: The adapter registry to monitor
            name: Name for this health check (default: "adapter_health")
            is_critical: Whether this check is critical (default: True)
        """
        super().__init__(name, is_critical)
        self._adapter_registry = adapter_registry

    def _perform_health_check(self) -> tuple[EHealthStatus, str, Dict[str, Any] | None]:
        """
        Perform the adapter health check.

        Checks the adapter registry for available adapters and their status.

        Returns:
            tuple: (status, message, details)
                - status: EHealthStatus indicating adapter health
                - message: Human-readable status message
                - details: Dictionary with adapter information
        """
        try:
            # Get all adapters from the registry
            adapters = self._get_registered_adapters()
            adapter_count = len(adapters)

            # Check individual adapter status
            healthy_adapters = []
            unhealthy_adapters = []

            for adapter_name, adapter_info in adapters.items():
                try:
                    if self._is_adapter_available(adapter_name, adapter_info):
                        healthy_adapters.append(adapter_name)
                    else:
                        unhealthy_adapters.append(adapter_name)
                except Exception:
                    # If we can't determine adapter availability, consider it unhealthy
                    unhealthy_adapters.append(adapter_name)

            healthy_count = len(healthy_adapters)
            unhealthy_count = len(unhealthy_adapters)

            # Determine overall status
            if adapter_count == 0:
                status = EHealthStatus.UNHEALTHY
                message = "No logging adapters available - system cannot dispatch logs"
            elif healthy_count == 0:
                status = EHealthStatus.UNHEALTHY
                message = f"All {adapter_count} adapters are unavailable - critical failure"
            elif unhealthy_count > 0:
                status = EHealthStatus.DEGRADED
                message = f"{healthy_count}/{adapter_count} adapters healthy, {unhealthy_count} degraded"
            else:
                status = EHealthStatus.HEALTHY
                message = f"All {adapter_count} adapters are healthy and available"

            details = {
                "adapter_count": adapter_count,
                "healthy_adapters": healthy_adapters,
                "unhealthy_adapters": unhealthy_adapters,
                "healthy_count": healthy_count,
                "unhealthy_count": unhealthy_count,
                "adapters": list(adapters.keys())
            }

            return status, message, details

        except Exception as exc:
            return (
                EHealthStatus.UNHEALTHY,
                f"Failed to check adapter health: {str(exc)}",
                {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "adapter_count": 0,
                    "healthy_count": 0,
                    "unhealthy_count": 0,
                    "healthy_adapters": [],
                    "unhealthy_adapters": [],
                    "adapters": []
                }
            )

    def _get_registered_adapters(self) -> Dict[str, Any]:
        """
        Get all registered adapters from the registry.

        Returns:
            Dict[str, Any]: Dictionary of adapter names to adapter information
        """
        # This is a simplified implementation - in reality, this would
        # query the actual adapter registry interface
        try:
            # Try to get adapters from the registry using different interfaces
            if hasattr(self._adapter_registry, 'get_all_adapters'):
                return self._adapter_registry.get_all_adapters()
            elif hasattr(self._adapter_registry, 'list_adapters'):
                adapters = self._adapter_registry.list_adapters()
                return {name: {} for name in adapters}
            else:
                # Fallback: assume registry has some iterable interface
                adapters = {}
                # This would need to be implemented based on actual registry interface
                return adapters
        except AttributeError:
            # If the method doesn't exist, try alternative interfaces
            try:
                if hasattr(self._adapter_registry, 'list_adapters'):
                    adapters = self._adapter_registry.list_adapters()
                    return {name: {} for name in adapters}
            except Exception:
                pass
            # If we can't access the registry, return empty dict
            return {}
        except Exception:
            # If we can't access the registry, return empty dict
            return {}

    def _is_adapter_available(self, adapter_name: str, adapter_info: Any) -> bool:
        """
        Check if a specific adapter is available and functional.

        Args:
            adapter_name: Name of the adapter
            adapter_info: Adapter information/configuration

        Returns:
            bool: True if adapter is available, False otherwise
        """
        try:
            # This is a simplified check - in reality, this might involve:
            # - Connection testing for network adapters
            # - File system checks for file-based adapters
            # - Memory checks for in-memory adapters
            # - Authentication checks for authenticated adapters

            # For now, assume all registered adapters are available
            # This would be enhanced based on actual adapter types
            return True

        except Exception:
            # If we can't determine adapter status, consider it unavailable
            return False


class ContainerHealthCheck(BaseHealthCheck):
    """
    Health check for logging system containers and queues.

    This health check monitors queue depth and capacity to ensure the logging
    system can handle the current load without overflowing or becoming unresponsive.
    """

    def __init__(self,
                 container,
                 name: str = "container_health",
                 is_critical: bool = True,
                 degraded_threshold: float = 0.8,
                 unhealthy_threshold: float = 0.95):
        """
        Initialize the container health check.

        Args:
            container: The container/queue to monitor
            name: Name for this health check (default: "container_health")
            is_critical: Whether this check is critical (default: True)
            degraded_threshold: Queue utilization threshold for DEGRADED status (default: 0.8)
            unhealthy_threshold: Queue utilization threshold for UNHEALTHY status (default: 0.95)
        """
        super().__init__(name, is_critical)
        self._container = container
        self._degraded_threshold = degraded_threshold
        self._unhealthy_threshold = unhealthy_threshold

    def _perform_health_check(self) -> tuple[EHealthStatus, str, Dict[str, Any] | None]:
        """
        Perform the container health check.

        Monitors queue depth, capacity, and utilization to assess container health.

        Returns:
            tuple: (status, message, details)
                - status: EHealthStatus indicating container health
                - message: Human-readable status message
                - details: Dictionary with container metrics
        """
        try:
            # Get container metrics
            metrics = self._get_container_metrics()

            current_size = metrics.get('current_size', 0)
            max_capacity = metrics.get('max_capacity', 0)
            utilization = metrics.get('utilization', 0.0)

            # Determine status based on utilization thresholds
            if utilization >= self._unhealthy_threshold:
                status = EHealthStatus.UNHEALTHY
                message = f"Container critically full: {utilization:.1%} utilization ({current_size}/{max_capacity})"
            elif utilization >= self._degraded_threshold:
                status = EHealthStatus.DEGRADED
                message = f"Container approaching capacity: {utilization:.1%} utilization ({current_size}/{max_capacity})"
            else:
                status = EHealthStatus.HEALTHY
                message = f"Container healthy: {utilization:.1%} utilization ({current_size}/{max_capacity})"

            # Add threshold information
            details = dict(metrics)
            details.update({
                "degraded_threshold": self._degraded_threshold,
                "unhealthy_threshold": self._unhealthy_threshold,
                "utilization_percent": utilization * 100,
                "available_capacity": max_capacity - current_size,
                "capacity_status": "critical" if utilization >= self._unhealthy_threshold
                               else "warning" if utilization >= self._degraded_threshold
                               else "normal"
            })

            return status, message, details

        except Exception as exc:
            return (
                EHealthStatus.UNHEALTHY,
                f"Failed to check container health: {str(exc)}",
                {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "current_size": 0,
                    "max_capacity": 0,
                    "utilization": 0.0,
                    "utilization_percent": 0.0,
                    "available_capacity": 0
                }
            )

    def _get_container_metrics(self) -> Dict[str, Any]:
        """
        Get metrics from the container.

        Returns:
            Dict[str, Any]: Container metrics including size, capacity, and utilization

        Raises:
            Exception: If container metrics cannot be retrieved
        """
        # Try different container interfaces
        if hasattr(self._container, 'get_metrics'):
            return self._container.get_metrics()
        elif hasattr(self._container, 'size') and hasattr(self._container, 'maxlen'):
            # Collections.deque style container
            current_size = self._container.size() if callable(getattr(self._container, 'size')) else len(self._container)
            max_capacity = self._container.maxlen or float('inf')
            utilization = current_size / max_capacity if max_capacity != float('inf') else 0.0
            return {
                'current_size': current_size,
                'max_capacity': max_capacity,
                'utilization': utilization
            }
        elif hasattr(self._container, '__len__') and hasattr(self._container, 'maxlen'):
            # Another deque-like interface
            current_size = len(self._container)
            max_capacity = self._container.maxlen or float('inf')
            utilization = current_size / max_capacity if max_capacity != float('inf') else 0.0
            return {
                'current_size': current_size,
                'max_capacity': max_capacity,
                'utilization': utilization
            }
        else:
            # Fallback: assume basic container with __len__
            current_size = len(self._container) if hasattr(self._container, '__len__') else 0
            # Assume unlimited capacity if no maxlen
            max_capacity = float('inf')
            utilization = 0.0
            return {
                'current_size': current_size,
                'max_capacity': max_capacity,
                'utilization': utilization
            }