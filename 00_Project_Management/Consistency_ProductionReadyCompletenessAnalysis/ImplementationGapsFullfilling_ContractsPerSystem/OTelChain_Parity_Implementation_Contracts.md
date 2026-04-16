# Implementation Contracts for OTelChain Parity Enhancement

## Executive Summary

This document specifies the implementation contracts required to achieve full OTelChain parity across all five NK_System Observability subsystems. Each contract references the Metrics System as the authoritative reference implementation and specifies exactly what must be implemented, how it should be implemented, and the acceptance criteria.

The following gaps have been identified that require implementation contracts:
1. **OpenTelemetryAdapterPort** - Missing in Logging, Error Handling, Health Checker
2. **OpenTelemetryAdapter** - Missing in Logging, Error Handling, Health Checker
3. **UnavailableOpenTelemetryAdapter** - Missing in Logging, Error Handling, Health Checker
4. **ThreadPoolResourceManagementClient** - Missing in Error Handling, Tracer, Health Checker

---

## Contract 1: OpenTelemetryAdapterPort Interface

### 1.1 Purpose
Defines the protocol interface for OpenTelemetry adapters, enabling consistent OTel integration across all observability systems.

### 1.2 Reference Implementation
**Source:** `03.0040_Metrics/03_DigitalTwin/metrics_system/ports/open_telemetry_adapter_port.py`

### 1.3 Implementation Requirements

| Aspect | Specification |
|--------|--------------|
| **File Location** | `{system}/ports/open_telemetry_adapter_port.py` |
| **Decorator** | `@runtime_checkable` |
| **Base Class** | `Protocol` from `typing` |
| **Interface Name** | `OpenTelemetryAdapterPort` |

### 1.4 Required Methods

```python
@runtime_checkable
class OpenTelemetryAdapterPort(Protocol):
    def emit_signal(self, signal_name: str, payload: Mapping[str, Any]) -> None:
        """
        Emit a signal to OpenTelemetry.
        
        Args:
            signal_name: Name of the signal (e.g., "logging", "metrics", "trace")
            payload: Signal payload as key-value mapping
            
        Raises:
            RuntimeError: If OTel is unavailable or emission fails
        """
        ...
    
    def capability_profile(self) -> Mapping[str, Any]:
        """
        Return the adapter's capability profile.
        
        Returns:
            Mapping containing:
            - adapter_key: str - Unique identifier for the adapter
            - otel_semconv_profile: str - OTel semantic conventions profile
            - propagation_format: str - Trace context propagation format
            - failure_mode: str - Behavior when OTel unavailable
        """
        ...
```

### 1.5 System-Specific Adaptations

| System | logger_name in Adapter | adapter_key | otel_semconv_profile |
|--------|------------------------|-------------|---------------------|
| Logging | `"logging_system.telemetry"` | `telemetry.opentelemetry` | `otel.log.v1` |
| Error Handling | `"error_handling_system.telemetry"` | `telemetry.opentelemetry` | `otel.log.v1` |
| Health Checker | `"health_checker_system.telemetry"` | `telemetry.opentelemetry` | `otel.log.v1` |

### 1.6 Acceptance Criteria

- [ ] Interface is defined with `@runtime_checkable` decorator
- [ ] `emit_signal` method signature matches reference
- [ ] `capability_profile` method signature matches reference
- [ ] Interface is importable from `{system}.ports.open_telemetry_adapter_port`
- [ ] Interface passes runtime protocol check

---

## Contract 2: OpenTelemetryAdapter Implementation

### 2.1 Purpose
Provides the primary OpenTelemetry adapter that emits signals using the OTel protocol.

### 2.2 Reference Implementation
**Source:** `03.0040_Metrics/03_DigitalTwin/metrics_system/adapters/open_telemetry_adapter.py`

### 2.3 Implementation Requirements

| Aspect | Specification |
|--------|--------------|
| **File Location** | `{system}/adapters/open_telemetry_adapter.py` |
| **Base Class** | `@dataclass(frozen=True)` |
| **Implements** | `OpenTelemetryAdapterPort` |
| **Dependencies** | `find_spec` from `importlib.util`, `json`, `logging` |

### 2.4 Required Implementation

```python
from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
import json
import logging
from typing import Any, Mapping

from ..ports.open_telemetry_adapter_port import OpenTelemetryAdapterPort


@dataclass(frozen=True)
class OpenTelemetryAdapter(OpenTelemetryAdapterPort):
    """OpenTelemetry adapter for {system_name}."""
    
    # System-specific logger name
    logger_name: str = "{system}.telemetry"

    def emit_signal(self, signal_name: str, payload: Mapping[str, Any]) -> None:
        """
        Emit a signal to OpenTelemetry.
        
        Args:
            signal_name: Name of the signal
            payload: Signal payload
            
        Raises:
            RuntimeError: If opentelemetry package is not available
        """
        if find_spec("opentelemetry") is None:
            raise RuntimeError("opentelemetry package is not available")
        
        logger = logging.getLogger(self.logger_name)
        serialized = json.dumps(
            {
                "signal_name": signal_name,
                "payload": payload,
            },
            sort_keys=True,
            default=str,
        )
        logger.info(serialized)

    def capability_profile(self) -> Mapping[str, Any]:
        """
        Return the adapter's capability profile.
        
        Returns:
            OTel capability profile mapping
        """
        return {
            "adapter_key": "telemetry.opentelemetry",
            "otel_semconv_profile": "otel.log.v1",
            "propagation_format": "w3c_tracecontext",
            "failure_mode": "raise",
        }
```

### 2.5 System-Specific Values

Replace the following placeholders:

| Placeholder | Logging | Error Handling | Health Checker |
|-------------|---------|----------------|----------------|
| `{system}` | logging_system | error_handling_system | health_checker_system |
| `{system_name}` | Logging | Error Handling | Health Checker |

### 2.6 Acceptance Criteria

- [ ] Class is decorated with `@dataclass(frozen=True)`
- [ ] Implements `OpenTelemetryAdapterPort`
- [ ] Checks for opentelemetry package availability using `find_spec`
- [ ] Raises `RuntimeError` if opentelemetry is not available
- [ ] Serializes payload to JSON with signal_name
- [ ] Logs via Python standard logging
- [ ] Returns correct capability_profile
- [ ] Adapter is registered in AdapterRegistry with key `telemetry.opentelemetry`

---

## Contract 3: UnavailableOpenTelemetryAdapter Implementation

### 3.1 Purpose
Provides a fail-closed fallback adapter when OpenTelemetry is unavailable, ensuring graceful degradation.

### 3.2 Reference Implementation
**Source:** `03.0040_Metrics/03_DigitalTwin/metrics_system/adapters/unavailable_open_telemetry_adapter.py`

### 3.3 Implementation Requirements

| Aspect | Specification |
|--------|--------------|
| **File Location** | `{system}/adapters/unavailable_open_telemetry_adapter.py` |
| **Base Class** | `@dataclass(frozen=True)` |
| **Implements** | `OpenTelemetryAdapterPort` |

### 3.4 Required Implementation

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..ports.open_telemetry_adapter_port import OpenTelemetryAdapterPort


@dataclass(frozen=True)
class UnavailableOpenTelemetryAdapter(OpenTelemetryAdapterPort):
    """
    Fallback adapter when OpenTelemetry is unavailable.
    
    This adapter provides fail-closed behavior, raising an error
    when OTel is not available rather than silently dropping signals.
    """
    
    reason: str = "opentelemetry package is not available"

    def emit_signal(self, signal_name: str, payload: Mapping[str, Any]) -> None:
        """
        Raise RuntimeError to indicate unavailability.
        
        Args:
            signal_name: Name of the signal (unused)
            payload: Signal payload (unused)
            
        Raises:
            RuntimeError: Always, indicating OTel is unavailable
        """
        raise RuntimeError(self.reason)

    def capability_profile(self) -> Mapping[str, Any]:
        """
        Return capability profile indicating unavailability.
        
        Returns:
            Profile with failure_mode set to adapter_unavailable
        """
        return {
            "adapter_key": "telemetry.opentelemetry",
            "otel_semconv_profile": "otel.log.v1",
            "propagation_format": "w3c_tracecontext",
            "failure_mode": "adapter_unavailable",
        }
```

### 3.5 Acceptance Criteria

- [ ] Class is decorated with `@dataclass(frozen=True)`
- [ ] Implements `OpenTelemetryAdapterPort`
- [ ] `emit_signal` raises `RuntimeError` with reason
- [ ] Returns correct capability_profile with `failure_mode: adapter_unavailable`
- [ ] Adapter is registered in AdapterRegistry as fallback

---

## Contract 4: ThreadPoolResourceManagementClient Implementation

### 4.1 Purpose
Provides async execution capabilities via ThreadPoolExecutor for high-throughput scenarios.

### 4.2 Reference Implementation
**Source:** `03.0040_Metrics/03_DigitalTwin/metrics_system/resource_management/adapters/thread_pool_resource_management_client.py`

### 4.3 Implementation Requirements

| Aspect | Specification |
|--------|--------------|
| **File Location** | `{system}/resource_management/adapters/thread_pool_resource_management_client.py` |
| **Base Class** | `@dataclass` (not frozen - manages resources) |
| **Dependencies** | `ThreadPoolExecutor`, `Future` from `concurrent.futures`, `RLock` from `threading` |

### 4.4 Required Implementation Structure

```python
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Callable, Mapping
from uuid import uuid4

from ...models.utc_now_iso import utc_now_iso


@dataclass
class ThreadPoolResourceManagementClient:
    """Async resource management client with thread pool execution."""
    
    # State fields
    _container_leases_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    _execution_leases_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    _execution_profiles_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    _executors_by_profile_id: dict[str, ThreadPoolExecutor] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)
    _default_container_lease_ttl_seconds: int = 3600
    _default_execution_lease_ttl_seconds: int = 300

    def __post_init__(self) -> None:
        """Initialize default execution profiles."""
        if len(self._execution_profiles_by_id) > 0:
            return
        # System-specific execution profiles
        self._execution_profiles_by_id = {
            "exec.{system}.local.default": {
                "execution_profile_id": "exec.{system}.local.default",
                "scope_support": ["in_process"],
                "queue_model": "bounded_fifo",
                "queue_bounds": {"max_items": 5000},
                "scheduling_policy": {
                    "kind": "fixed_priority",
                    "priority_bands": ["error_fatal", "warn", "info_debug_trace"],
                },
                "thread_safety_mode": "single_writer_per_partition",
                "backpressure_policy": {
                    "action": "drop_oldest",
                    "severity_overrides": {"fatal": "block", "error": "retry_with_jitter"},
                },
                "lease_policy": {"required": True, "ttl_seconds": 300, "renewable": True},
                "worker_pool": {"max_workers": 4},
            },
            # Add Redis/distributed profile as needed
        }

    def close(self) -> None:
        """Shutdown all thread pools."""
        with self._lock:
            executors = list(self._executors_by_profile_id.values())
            self._executors_by_profile_id.clear()
        for executor in executors:
            executor.shutdown(wait=True, cancel_futures=False)

    # Container Lease Methods
    def request_container_lease(self, *, logger_instance_id: str, container_binding_id: str, container_backend_profile_id: str) -> Mapping[str, Any]: ...
    def validate_container_lease(self, container_lease_id: str) -> bool: ...
    def get_container_lease(self, container_lease_id: str) -> Mapping[str, Any]: ...
    def release_container_lease(self, container_lease_id: str) -> None: ...

    # Execution Lease Methods
    def request_ex, *, logger_instanceecution_lease(self_id: str, execution_binding_id: str, required_execution_profile_id: str) -> Mapping[str, Any]: ...
    def validate_execution_lease(self, execution_lease_id: str) -> bool: ...
    def get_execution_lease(self, execution_lease_id: str) -> Mapping[str, Any]: ...
    def release_execution_lease(self, execution_lease_id: str) -> None: ...

    # Execution Profile Methods
    def get_execution_profile(self, execution_profile_id: str) -> Mapping[str, Any]: ...

    # Async Execution Methods
    def execute_dispatch_tasks(self, *, execution_lease_id: str, required_execution_profile_id: str, tasks: list[Callable[[], Any]]) -> list[Any]: ...
    
    def _get_or_create_executor(self, *, profile_id: str, profile: Mapping[str, Any]) -> ThreadPoolExecutor: ...
```

### 4.5 System-Specific Values

Replace the following placeholders:

| Placeholder | Logging | Error Handling | Tracer | Health Checker |
|-------------|---------|----------------|--------|----------------|
| `{system}` | logging | error_handling | tracer | health_checker |

### 4.6 Execution Profile Configuration

Each system should define at least these profiles:

1. **Local Profile** (`exec.{system}.local.default`)
   - `scope_support`: `["in_process"]`
   - `thread_safety_mode`: `"single_writer_per_partition"`
   - `worker_pool.max_workers`: 4

2. **Distributed Profile** (optional)
   - `scope_support`: `["inter_process", "distributed"]`
   - `thread_safety_mode`: `"thread_safe_locked"`
   - `worker_pool.max_workers`: 8

### 4.7 Acceptance Criteria

- [ ] Implements all container lease methods
- [ ] Implements all execution lease methods
- [ ] Implements `execute_dispatch_tasks` for async execution
- [ ] Thread-safe with `RLock` for state management
- [ ] Proper executor lifecycle management with `close()` method
- [ ] System-specific execution profiles in `__post_init__`
- [ ] Validation of lease expiration
- [ ] Queue bounds checking in dispatch

---

## Contract 5: Adapter Registry Integration

### 5.1 Purpose
Ensure OTel adapters are properly registered in the system's AdapterRegistry.

### 5.2 Implementation Requirements

Each system must register the following adapters:

| Adapter Key | Primary Adapter | Fallback Adapter |
|-------------|----------------|------------------|
| `telemetry.opentelemetry` | OpenTelemetryAdapter | UnavailableOpenTelemetryAdapter |

### 5.3 Registration Pattern

```python
# In service __post_init__ or adapter initialization
self._adapter_registry.register(
    "telemetry.opentelemetry",
    OpenTelemetryAdapter(),
    overwrite=False,
)

# Fallback registration
self._adapter_registry.register(
    "telemetry.opentelemetry.unavailable",
    UnavailableOpenTelemetryAdapter(),
    overwrite=False,
)
```

---

## Implementation Priority Matrix

| Priority | Contract | Systems to Update | Estimated Effort |
|----------|----------|-------------------|------------------|
| **HIGH** | OpenTelemetryAdapterPort | Logging, Error Handling, Health Checker | 1 day |
| **HIGH** | OpenTelemetryAdapter | Logging, Error Handling, Health Checker | 1 day |
| **HIGH** | UnavailableOpenTelemetryAdapter | Logging, Error Handling, Health Checker | 0.5 day |
| **MEDIUM** | ThreadPoolResourceManagementClient | Error Handling, Tracer, Health Checker | 2 days |

---

## References

- **Reference Implementation:** Metrics System (`03.0040_Metrics`)
- **OTel Semantic Conventions:** `otel.log.v1`
- **W3C Trace Context:** `w3c_tracecontext`

---

*Contract Version: 1.0*  
*Generated: 2026-03-11*  
*Reference: Metrics System (03.0040_Metrics)*
