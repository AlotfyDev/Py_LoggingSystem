from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..ports.open_telemetry_adapter_port import OpenTelemetryAdapterPort


@dataclass(frozen=True)
class UnavailableOpenTelemetryAdapter(OpenTelemetryAdapterPort):
    reason: str

    def emit_signal(self, signal_name: str, payload: Mapping[str, Any]) -> None:
        raise RuntimeError(self.reason)

    def capability_profile(self) -> Mapping[str, Any]:
        return {
            "adapter_key": "telemetry.opentelemetry",
            "otel_semconv_profile": "otel.log.v1",
            "propagation_format": "w3c_tracecontext",
            "failure_mode": "adapter_unavailable",
        }
