from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..ports.open_telemetry_adapter_port import OpenTelemetryAdapterPort


@dataclass(frozen=True)
class NoOpAdapter(OpenTelemetryAdapterPort):
    def emit_signal(self, signal_name: str, payload: Mapping[str, Any]) -> None:
        return None

    def capability_profile(self) -> Mapping[str, Any]:
        return {
            "adapter_key": "telemetry.noop",
            "otel_semconv_profile": "none",
            "propagation_format": "none",
            "failure_mode": "drop",
        }
