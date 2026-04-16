from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from .open_telemetry_adapter_port import OpenTelemetryAdapterPort


@runtime_checkable
class AdapterRegistryPort(Protocol):
    def register(self, adapter_key: str, adapter: OpenTelemetryAdapterPort, *, overwrite: bool = False) -> None:
        ...

    def resolve(self, adapter_key: str) -> OpenTelemetryAdapterPort:
        ...

    def list_keys(self) -> Sequence[str]:
        ...

    def has(self, adapter_key: str) -> bool:
        ...
