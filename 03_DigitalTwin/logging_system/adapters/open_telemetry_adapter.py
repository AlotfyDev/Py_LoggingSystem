from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
import json
import logging
from typing import Any, Mapping

from ..ports.open_telemetry_adapter_port import OpenTelemetryAdapterPort


@dataclass(frozen=True)
class OpenTelemetryAdapter(OpenTelemetryAdapterPort):
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
        # Transport and exporter wiring remains external to this generic subsystem;
        # this adapter keeps the emission boundary stable and vendor-agnostic.
        logger.info(serialized)

    def capability_profile(self) -> Mapping[str, Any]:
        return {
            "adapter_key": "telemetry.opentelemetry",
            "otel_semconv_profile": "otel.log.v1",
            "propagation_format": "w3c_tracecontext",
            "failure_mode": "raise",
        }
