from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class OpenTelemetryAdapterPort(Protocol):
    def emit_signal(self, signal_name: str, payload: Mapping[str, Any]) -> None:
        ...

    def capability_profile(self) -> Mapping[str, Any]:
        ...
