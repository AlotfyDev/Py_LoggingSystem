from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


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
    metadata: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, profile_id: str, payload: Mapping[str, Any]) -> "ProductionProfileDTO":
        normalized = {str(k): v for k, v in dict(payload).items()}
        metadata = normalized.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise TypeError("production profile metadata must be a mapping")
        return cls(
            profile_id=str(profile_id).strip(),
            config_version=str(normalized.get("config_version", "")).strip(),
            status=str(normalized.get("status", "active")).strip() or "active",
            description=str(normalized.get("description", "")).strip(),
            provider_ref=str(normalized.get("provider_ref", "")).strip(),
            connection_ref=str(normalized.get("connection_ref", "")).strip(),
            persistence_ref=str(normalized.get("persistence_ref", "")).strip(),
            required_execution_profile_id=str(normalized.get("required_execution_profile_id", "")).strip(),
            container_backend_profile_id=str(normalized.get("container_backend_profile_id", "")).strip(),
            container_binding_id=str(normalized.get("container_binding_id", "")).strip(),
            execution_binding_id=str(normalized.get("execution_binding_id", "")).strip(),
            adapter_key=str(normalized.get("adapter_key", "")).strip(),
            metadata={str(k): v for k, v in metadata.items()},
        )

    @classmethod
    def from_existing(cls, profile_id: str, payload: Mapping[str, Any]) -> "ProductionProfileDTO":
        return cls.from_mapping(profile_id=profile_id, payload=payload)

    def to_profile_payload(self) -> dict[str, Any]:
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

    def to_mapping(self) -> dict[str, Any]:
        return self.to_profile_payload()
