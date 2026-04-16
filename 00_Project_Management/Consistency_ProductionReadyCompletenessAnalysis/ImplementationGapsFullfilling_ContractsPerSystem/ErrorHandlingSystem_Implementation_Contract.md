# Error Handling System - Implementation Contract for OTelChain and Async Parity

## Purpose
This document specifies the implementation requirements to achieve OTelChain parity and async support for the Error Handling System, using the Metrics System as the reference implementation.

## Current Status
- **OTel Adapter Port:** ❌ Missing
- **OpenTelemetry Adapter:** ❌ Missing
- **Unavailable Adapter:** ❌ Missing
- **ThreadPool Resource Client:** ❌ Missing

## Required Implementations

### 1. OpenTelemetryAdapterPort Interface

**Reference:** `03.0040_Metrics/03_DigitalTwin/metrics_system/ports/open_telemetry_adapter_port.py`

**File to Create:** `03.0030_ErrorHandlingSystem/03_DigitalTwin/error_handling_system/ports/open_telemetry_adapter_port.py`

```python
from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class OpenTelemetryAdapterPort(Protocol):
    def emit_signal(self, signal_name: str, payload: Mapping[str, Any]) -> None:
        ...

    def capability_profile(self) -> Mapping[str, Any]:
        ...
```

### 2. OpenTelemetryAdapter

**Reference:** `03.0040_Metrics/03_DigitalTwin/metrics_system/adapters/open_telemetry_adapter.py`

**File to Create:** `03.0030_ErrorHandlingSystem/03_DigitalTwin/error_handling_system/adapters/open_telemetry_adapter.py`

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
    """OpenTelemetry adapter for Error Handling System."""
    
    logger_name: str = "error_handling_system.telemetry"

    def emit_signal(self, signal_name: str, payload: Mapping[str, Any]) -> None:
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
        return {
            "adapter_key": "telemetry.opentelemetry",
            "otel_semconv_profile": "otel.log.v1",
            "propagation_format": "w3c_tracecontext",
            "failure_mode": "raise",
        }
```

### 3. UnavailableOpenTelemetryAdapter

**Reference:** `03.0040_Metrics/03_DigitalTwin/metrics_system/adapters/unavailable_open_telemetry_adapter.py`

**File to Create:** `03.0030_ErrorHandlingSystem/03_DigitalTwin/error_handling_system/adapters/unavailable_open_telemetry_adapter.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..ports.open_telemetry_adapter_port import OpenTelemetryAdapterPort


@dataclass(frozen=True)
class UnavailableOpenTelemetryAdapter(OpenTelemetryAdapterPort):
    """Fallback adapter when OpenTelemetry is unavailable."""
    
    reason: str = "opentelemetry package is not available"

    def emit_signal(self, signal_name: str, payload: Mapping[str, Any]) -> None:
        raise RuntimeError(self.reason)

    def capability_profile(self) -> Mapping[str, Any]:
        return {
            "adapter_key": "telemetry.opentelemetry",
            "otel_semconv_profile": "otel.log.v1",
            "propagation_format": "w3c_tracecontext",
            "failure_mode": "adapter_unavailable",
        }
```

### 4. ThreadPoolResourceManagementClient

**Reference:** `03.0040_Metrics/03_DigitalTwin/metrics_system/resource_management/adapters/thread_pool_resource_management_client.py`

**File to Create:** `03.0030_ErrorHandlingSystem/03_DigitalTwin/error_handling_system/resource_management/adapters/thread_pool_resource_management_client.py`

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
    """Async resource management client with thread pool execution for Error Handling."""
    
    _container_leases_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    _execution_leases_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    _execution_profiles_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    _executors_by_profile_id: dict[str, ThreadPoolExecutor] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)
    _default_container_lease_ttl_seconds: int = 3600
    _default_execution_lease_ttl_seconds: int = 300

    def __post_init__(self) -> None:
        if len(self._execution_profiles_by_id) > 0:
            return
        self._execution_profiles_by_id = {
            "exec.error_handling.local.default": {
                "execution_profile_id": "exec.error_handling.local.default",
                "scope_support": ["in_process"],
                "queue_model": "bounded_fifo",
                "queue_bounds": {"max_items": 5000},
                "scheduling_policy": {
                    "kind": "fixed_priority",
                    "priority_bands": ["fatal", "error", "warn"],
                },
                "thread_safety_mode": "single_writer_per_partition",
                "backpressure_policy": {
                    "action": "drop_oldest",
                    "severity_overrides": {"fatal": "block", "error": "retry_with_jitter"},
                },
                "lease_policy": {"required": True, "ttl_seconds": 300, "renewable": True},
                "worker_pool": {"max_workers": 4},
            },
            "exec.error_handling.distributed.redis": {
                "execution_profile_id": "exec.error_handling.distributed.redis",
                "scope_support": ["inter_process", "distributed"],
                "queue_model": "bounded_priority",
                "queue_bounds": {"max_items": 20000},
                "scheduling_policy": {
                    "kind": "weighted_fair",
                    "queue_weights": {"high": 6, "medium": 3, "low": 1},
                },
                "thread_safety_mode": "thread_safe_locked",
                "backpressure_policy": {
                    "action": "retry_with_jitter",
                    "severity_overrides": {"fatal": "block"},
                },
                "lease_policy": {"required": True, "ttl_seconds": 120, "renewable": True},
                "worker_pool": {"max_workers": 8},
            },
        }

    def close(self) -> None:
        with self._lock:
            executors = list(self._executors_by_profile_id.values())
            self._executors_by_profile_id.clear()
        for executor in executors:
            executor.shutdown(wait=True, cancel_futures=False)

    # Implement all container and execution lease methods
    # (Reference: Metrics System implementation)
```

## Integration Steps

### Step 1: Create Port Interface
1. Create directory: `error_handling_system/ports/`
2. Create file: `open_telemetry_adapter_port.py`

### Step 2: Create Adapters
1. Create file: `adapters/open_telemetry_adapter.py`
2. Create file: `adapters/unavailable_open_telemetry_adapter.py`

### Step 3: Create ThreadPool Client
1. Create directory: `resource_management/adapters/`
2. Create file: `thread_pool_resource_management_client.py`

### Step 4: Register in AdapterRegistry
1. Open: `adapters/adapter_registry.py`
2. Add imports and register adapters

### Step 5: Update Service to Use ThreadPool
1. Modify: `services/error_handling_service.py`
2. Change default resource management client to ThreadPool variant

## Acceptance Criteria

- [ ] OpenTelemetryAdapterPort interface defined
- [ ] OpenTelemetryAdapter emits signals correctly
- [ ] UnavailableOpenTelemetryAdapter fails gracefully
- [ ] ThreadPoolResourceManagementClient executes async tasks
- [ ] All adapters registered in AdapterRegistry
- [ ] Tests pass for all new components

## Files to Create/Modify

| File | Action |
|------|--------|
| `error_handling_system/ports/open_telemetry_adapter_port.py` | Create |
| `error_handling_system/adapters/open_telemetry_adapter.py` | Create |
| `error_handling_system/adapters/unavailable_open_telemetry_adapter.py` | Create |
| `error_handling_system/resource_management/adapters/thread_pool_resource_management_client.py` | Create |
| `error_handling_system/adapters/__init__.py` | Modify |
| `error_handling_system/adapters/adapter_registry.py` | Modify |
| `error_handling_system/services/error_handling_service.py` | Modify |

---

*Contract Version: 1.0*  
*Reference: Metrics System (03.0040_Metrics)*  
*Target: Error Handling System (03.0030_ErrorHandlingSystem)*
