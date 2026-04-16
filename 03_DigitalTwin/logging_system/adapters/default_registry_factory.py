from __future__ import annotations

from importlib.util import find_spec

from .adapter_registry import AdapterRegistry
from .no_op_adapter import NoOpAdapter
from .open_telemetry_adapter import OpenTelemetryAdapter
from .unavailable_open_telemetry_adapter import UnavailableOpenTelemetryAdapter


def build_default_adapter_registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register("telemetry.noop", NoOpAdapter())
    if find_spec("opentelemetry") is None:
        registry.register(
            "telemetry.opentelemetry",
            UnavailableOpenTelemetryAdapter("opentelemetry package is not available"),
        )
    else:
        registry.register("telemetry.opentelemetry", OpenTelemetryAdapter())
    return registry
