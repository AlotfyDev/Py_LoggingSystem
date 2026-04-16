from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock

from ..ports.open_telemetry_adapter_port import OpenTelemetryAdapterPort


@dataclass
class AdapterRegistry:
    _adapters_by_key: dict[str, OpenTelemetryAdapterPort] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def register(self, adapter_key: str, adapter: OpenTelemetryAdapterPort, *, overwrite: bool = False) -> None:
        key = adapter_key.strip()
        if key == "":
            raise ValueError("adapter_key is required")
        with self._lock:
            if not overwrite and key in self._adapters_by_key:
                raise KeyError(f"Adapter key already registered: {key}")
            self._adapters_by_key[key] = adapter

    def resolve(self, adapter_key: str) -> OpenTelemetryAdapterPort:
        key = adapter_key.strip()
        if key == "":
            raise ValueError("adapter_key is required")
        with self._lock:
            selected = self._adapters_by_key.get(key)
            if selected is not None:
                return selected
        raise KeyError(f"Adapter key is not registered: {key}")

    def list_keys(self) -> list[str]:
        with self._lock:
            return sorted(self._adapters_by_key.keys())

    def has(self, adapter_key: str) -> bool:
        key = adapter_key.strip()
        if key == "":
            return False
        with self._lock:
            return key in self._adapters_by_key
