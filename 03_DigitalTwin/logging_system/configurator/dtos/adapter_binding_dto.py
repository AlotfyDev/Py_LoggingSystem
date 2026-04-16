from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class AdapterBindingDTO:
    binding_id: str
    adapter_key: str
    binding_metadata: dict[str, Any]
    config_version: str

    @classmethod
    def from_mapping(cls, binding_id: str, payload: Mapping[str, Any]) -> "AdapterBindingDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("adapter binding configuration payload must be a mapping")
        version = str(payload.get("config_version", "")).strip()
        if not version:
            raise ValueError("adapter binding configuration requires non-empty config_version")
        adapter_key = str(payload.get("adapter_key", "")).strip()
        if not adapter_key:
            raise ValueError("adapter binding configuration requires adapter_key")
        binding_metadata = payload.get("binding_metadata", {})
        if not isinstance(binding_metadata, Mapping):
            raise ValueError("adapter binding configuration requires binding_metadata mapping")
        return cls(
            binding_id=str(binding_id),
            adapter_key=adapter_key,
            binding_metadata=dict(binding_metadata),
            config_version=version,
        )

    @classmethod
    def from_existing(cls, binding_id: str, payload: Mapping[str, Any]) -> "AdapterBindingDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("adapter binding payload must be a mapping")
        source: Mapping[str, Any]
        if "adapter_binding" in payload and isinstance(payload["adapter_binding"], Mapping):
            source = payload["adapter_binding"]
            merged = dict(source)
            if "config_version" not in merged and "config_version" in payload:
                merged["config_version"] = payload["config_version"]
            source = merged
        else:
            source = payload
        if "config_version" not in source:
            source = {**dict(source), "config_version": "legacy-unversioned"}
        return cls.from_mapping(binding_id=binding_id, payload=source)

    def to_policy_payload(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "adapter_binding": {
                "adapter_key": self.adapter_key,
                "binding_metadata": dict(self.binding_metadata),
            },
        }

    def to_mapping(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "adapter_key": self.adapter_key,
            "binding_metadata": dict(self.binding_metadata),
        }
