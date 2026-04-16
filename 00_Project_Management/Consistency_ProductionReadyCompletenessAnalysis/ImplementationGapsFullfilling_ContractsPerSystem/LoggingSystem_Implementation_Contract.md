# Logging System - Implementation Contract for OTelChain Parity

## Purpose
This document specifies the implementation requirements to achieve OTelChain parity for the Logging System, using the Metrics System as the reference implementation.

## Current Status
- **OTel Adapter Port:** ❌ Missing
- **OpenTelemetry Adapter:** ❌ Missing  
- **Unavailable Adapter:** ❌ Missing
- **ThreadPool Resource Client:** ✅ Present

## Required Implementations

### 1. OpenTelemetryAdapterPort Interface

**Reference:** `03.0040_Metrics/03_DigitalTwin/metrics_system/ports/open_telemetry_adapter_port.py`

**File to Create:** `03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports/open_telemetry_adapter_port.py`

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

**File to Create:** `03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters/open_telemetry_adapter.py`

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
    """OpenTelemetry adapter for Logging System."""
    
    logger_name: str = "logging_system.telemetry"

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

**File to Create:** `03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters/unavailable_open_telemetry_adapter.py`

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

## Integration Steps

### Step 1: Create Port Interface
1. Create directory: `03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports/`
2. Create file: `open_telemetry_adapter_port.py`
3. Add interface definition

### Step 2: Create Adapters
1. Create file: `adapters/open_telemetry_adapter.py`
2. Create file: `adapters/unavailable_open_telemetry_adapter.py`

### Step 3: Register in AdapterRegistry
1. Open: `adapters/adapter_registry.py`
2. Add imports for new adapters
3. Register adapters in registry initialization

### Step 4: Verify Production Profile
1. Verify: `prod.logging.otel.default` profile uses `telemetry.opentelemetry` adapter key

## Acceptance Criteria

- [ ] OpenTelemetryAdapterPort interface defined and importable
- [ ] OpenTelemetryAdapter emits signals with correct logger name
- [ ] UnavailableOpenTelemetryAdapter raises RuntimeError on emit
- [ ] Both adapters registered in AdapterRegistry
- [ ] Capability profiles return correct metadata
- [ ] Tests pass for adapter behavior

## Files to Modify

| File | Action |
|------|--------|
| `logging_system/ports/open_telemetry_adapter_port.py` | Create |
| `logging_system/adapters/open_telemetry_adapter.py` | Create |
| `logging_system/adapters/unavailable_open_telemetry_adapter.py` | Create |
| `logging_system/adapters/__init__.py` | Modify - add exports |
| `logging_system/adapters/adapter_registry.py` | Modify - register adapters |

---

*Contract Version: 1.0*  
*Reference: Metrics System (03.0040_Metrics)*  
*Target: Logging System (03.0020_LoggingSystem)*
