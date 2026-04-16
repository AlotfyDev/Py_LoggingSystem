from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _require_non_empty_str(value: Any, field_name: str) -> str:
    normalized = str(value).strip()
    if normalized == "":
        raise ValueError(f"{field_name} is required")
    return normalized


@dataclass(frozen=True)
class ProductionProfileDTO:
    profile_id: str
    config_version: str
    status: str
    description: str
    provider_ref: str
    connection_ref: str
    persistence_ref: str
    required_execution_profile_id: str
    container_backend_profile_id: str
    container_binding_id: str
    execution_binding_id: str
    adapter_key: str
    metadata: dict[str, Any]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ProductionProfileDTO":
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("metadata must be a mapping")
        return cls(
            profile_id=_require_non_empty_str(payload.get("profile_id"), "profile_id"),
            config_version=_require_non_empty_str(payload.get("config_version"), "config_version"),
            status=_require_non_empty_str(payload.get("status", "active"), "status"),
            description=str(payload.get("description", "")).strip(),
            provider_ref=_require_non_empty_str(payload.get("provider_ref"), "provider_ref"),
            connection_ref=_require_non_empty_str(payload.get("connection_ref"), "connection_ref"),
            persistence_ref=_require_non_empty_str(payload.get("persistence_ref"), "persistence_ref"),
            required_execution_profile_id=_require_non_empty_str(
                payload.get("required_execution_profile_id"),
                "required_execution_profile_id",
            ),
            container_backend_profile_id=_require_non_empty_str(
                payload.get("container_backend_profile_id"),
                "container_backend_profile_id",
            ),
            container_binding_id=_require_non_empty_str(
                payload.get("container_binding_id", "container.binding.default"),
                "container_binding_id",
            ),
            execution_binding_id=_require_non_empty_str(
                payload.get("execution_binding_id", "execution.binding.default"),
                "execution_binding_id",
            ),
            adapter_key=_require_non_empty_str(payload.get("adapter_key", "telemetry.noop"), "adapter_key"),
            metadata={str(k): v for k, v in metadata.items()},
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "config_version": self.config_version,
            "status": self.status,
            "description": self.description,
            "provider_ref": self.provider_ref,
            "connection_ref": self.connection_ref,
            "persistence_ref": self.persistence_ref,
            "required_execution_profile_id": self.required_execution_profile_id,
            "container_backend_profile_id": self.container_backend_profile_id,
            "container_binding_id": self.container_binding_id,
            "execution_binding_id": self.execution_binding_id,
            "adapter_key": self.adapter_key,
            "metadata": dict(self.metadata),
        }
