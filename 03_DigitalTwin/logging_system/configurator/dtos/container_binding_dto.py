from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ContainerBindingDTO:
    binding_id: str
    container_binding_id: str
    container_backend_profile_id: str
    container_lease_id: str | None
    binding_metadata: dict[str, Any]
    config_version: str

    @classmethod
    def from_mapping(cls, binding_id: str, payload: Mapping[str, Any]) -> "ContainerBindingDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("container binding configuration payload must be a mapping")
        version = str(payload.get("config_version", "")).strip()
        if not version:
            raise ValueError("container binding configuration requires non-empty config_version")

        container_binding_id = str(payload.get("container_binding_id", "")).strip()
        if not container_binding_id:
            raise ValueError("container binding configuration requires container_binding_id")

        backend_profile = str(payload.get("container_backend_profile_id", "")).strip()
        if not backend_profile:
            raise ValueError("container binding configuration requires container_backend_profile_id")

        lease_value = payload.get("container_lease_id")
        lease_id: str | None = None
        if lease_value is not None:
            lease_id = str(lease_value).strip() or None

        binding_metadata = payload.get("binding_metadata", {})
        if not isinstance(binding_metadata, Mapping):
            raise ValueError("container binding configuration requires binding_metadata mapping")

        return cls(
            binding_id=str(binding_id),
            container_binding_id=container_binding_id,
            container_backend_profile_id=backend_profile,
            container_lease_id=lease_id,
            binding_metadata=dict(binding_metadata),
            config_version=version,
        )

    @classmethod
    def from_existing(cls, binding_id: str, payload: Mapping[str, Any]) -> "ContainerBindingDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("container binding payload must be a mapping")
        source: Mapping[str, Any]
        if "container_binding" in payload and isinstance(payload["container_binding"], Mapping):
            source = payload["container_binding"]
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
            "container_binding": {
                "container_binding_id": self.container_binding_id,
                "container_backend_profile_id": self.container_backend_profile_id,
                "container_lease_id": self.container_lease_id,
                "binding_metadata": dict(self.binding_metadata),
            },
        }

    def to_mapping(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "container_binding_id": self.container_binding_id,
            "container_backend_profile_id": self.container_backend_profile_id,
            "container_lease_id": self.container_lease_id,
            "binding_metadata": dict(self.binding_metadata),
        }
