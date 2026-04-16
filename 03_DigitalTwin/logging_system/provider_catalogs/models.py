from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _require_non_empty_str(value: Any, field_name: str) -> str:
    normalized = str(value).strip()
    if normalized == "":
        raise ValueError(f"{field_name} is required")
    return normalized


def _require_non_empty_str_list(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) == 0:
        raise ValueError(f"{field_name} must be a non-empty list of strings")
    items: list[str] = []
    for raw in value:
        item = str(raw).strip()
        if item == "":
            raise ValueError(f"{field_name} contains empty value")
        items.append(item)
    return tuple(items)


@dataclass(frozen=True)
class ProviderCatalogEntry:
    provider_id: str
    backend_type: str
    scope_support: tuple[str, ...]
    ordering_guarantee: str
    ack_model: str
    durability_level: str
    qos_support: tuple[str, ...]
    lease_required: bool
    execution_plane_relation: str
    required_execution_profile_id: str
    backend_execution_scope: str
    supported_partition_modes: tuple[str, ...]
    connection_profile_id: str
    persistence_profile_id: str
    fail_closed_conditions: tuple[str, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ProviderCatalogEntry:
        return cls(
            provider_id=_require_non_empty_str(payload.get("provider_id"), "provider_id"),
            backend_type=_require_non_empty_str(payload.get("backend_type"), "backend_type"),
            scope_support=_require_non_empty_str_list(payload.get("scope_support"), "scope_support"),
            ordering_guarantee=_require_non_empty_str(payload.get("ordering_guarantee"), "ordering_guarantee"),
            ack_model=_require_non_empty_str(payload.get("ack_model"), "ack_model"),
            durability_level=_require_non_empty_str(payload.get("durability_level"), "durability_level"),
            qos_support=_require_non_empty_str_list(payload.get("qos_support"), "qos_support"),
            lease_required=bool(payload.get("lease_required", False)),
            execution_plane_relation=_require_non_empty_str(
                payload.get("execution_plane_relation"),
                "execution_plane_relation",
            ),
            required_execution_profile_id=_require_non_empty_str(
                payload.get("required_execution_profile_id"),
                "required_execution_profile_id",
            ),
            backend_execution_scope=_require_non_empty_str(
                payload.get("backend_execution_scope"),
                "backend_execution_scope",
            ),
            supported_partition_modes=_require_non_empty_str_list(
                payload.get("supported_partition_modes"),
                "supported_partition_modes",
            ),
            connection_profile_id=_require_non_empty_str(
                payload.get("connection_profile_id"),
                "connection_profile_id",
            ),
            persistence_profile_id=_require_non_empty_str(
                payload.get("persistence_profile_id"),
                "persistence_profile_id",
            ),
            fail_closed_conditions=_require_non_empty_str_list(
                payload.get("fail_closed_conditions"),
                "fail_closed_conditions",
            ),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "backend_type": self.backend_type,
            "scope_support": list(self.scope_support),
            "ordering_guarantee": self.ordering_guarantee,
            "ack_model": self.ack_model,
            "durability_level": self.durability_level,
            "qos_support": list(self.qos_support),
            "lease_required": self.lease_required,
            "execution_plane_relation": self.execution_plane_relation,
            "required_execution_profile_id": self.required_execution_profile_id,
            "backend_execution_scope": self.backend_execution_scope,
            "supported_partition_modes": list(self.supported_partition_modes),
            "connection_profile_id": self.connection_profile_id,
            "persistence_profile_id": self.persistence_profile_id,
            "fail_closed_conditions": list(self.fail_closed_conditions),
        }


@dataclass(frozen=True)
class ConnectionCatalogEntry:
    connector_profile_id: str
    provider_id: str
    connector_type: str
    protocol: str
    auth_modes: tuple[str, ...]
    tls_modes: tuple[str, ...]
    retry_policy: dict[str, Any]
    circuit_breaker_policy: dict[str, Any]
    session_or_lease_requirements: dict[str, Any]
    execution_plane_relation: str
    backend_execution_scope: str
    capabilities: tuple[str, ...]
    fail_closed_conditions: tuple[str, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ConnectionCatalogEntry:
        retry_policy = payload.get("retry_policy")
        if not isinstance(retry_policy, Mapping):
            raise ValueError("retry_policy must be a mapping")
        circuit_breaker_policy = payload.get("circuit_breaker_policy")
        if not isinstance(circuit_breaker_policy, Mapping):
            raise ValueError("circuit_breaker_policy must be a mapping")
        session_or_lease_requirements = payload.get("session_or_lease_requirements")
        if not isinstance(session_or_lease_requirements, Mapping):
            raise ValueError("session_or_lease_requirements must be a mapping")

        return cls(
            connector_profile_id=_require_non_empty_str(
                payload.get("connector_profile_id"),
                "connector_profile_id",
            ),
            provider_id=_require_non_empty_str(payload.get("provider_id"), "provider_id"),
            connector_type=_require_non_empty_str(payload.get("connector_type"), "connector_type"),
            protocol=_require_non_empty_str(payload.get("protocol"), "protocol"),
            auth_modes=_require_non_empty_str_list(payload.get("auth_modes"), "auth_modes"),
            tls_modes=_require_non_empty_str_list(payload.get("tls_modes"), "tls_modes"),
            retry_policy=dict(retry_policy),
            circuit_breaker_policy=dict(circuit_breaker_policy),
            session_or_lease_requirements=dict(session_or_lease_requirements),
            execution_plane_relation=_require_non_empty_str(
                payload.get("execution_plane_relation"),
                "execution_plane_relation",
            ),
            backend_execution_scope=_require_non_empty_str(
                payload.get("backend_execution_scope"),
                "backend_execution_scope",
            ),
            capabilities=_require_non_empty_str_list(payload.get("capabilities"), "capabilities"),
            fail_closed_conditions=_require_non_empty_str_list(
                payload.get("fail_closed_conditions"),
                "fail_closed_conditions",
            ),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "connector_profile_id": self.connector_profile_id,
            "provider_id": self.provider_id,
            "connector_type": self.connector_type,
            "protocol": self.protocol,
            "auth_modes": list(self.auth_modes),
            "tls_modes": list(self.tls_modes),
            "retry_policy": dict(self.retry_policy),
            "circuit_breaker_policy": dict(self.circuit_breaker_policy),
            "session_or_lease_requirements": dict(self.session_or_lease_requirements),
            "execution_plane_relation": self.execution_plane_relation,
            "backend_execution_scope": self.backend_execution_scope,
            "capabilities": list(self.capabilities),
            "fail_closed_conditions": list(self.fail_closed_conditions),
        }


@dataclass(frozen=True)
class PersistenceCatalogEntry:
    persistence_profile_id: str
    provider_id: str
    durability_level: str
    replay_capability: str
    retention_capability: dict[str, Any]
    compaction_capability: dict[str, Any]
    consistency_model: str
    ack_semantics: str
    execution_plane_relation: str
    backend_execution_scope: str
    backup_restore_support: dict[str, Any]
    eviction_policy_compatibility: tuple[str, ...]
    fail_closed_conditions: tuple[str, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> PersistenceCatalogEntry:
        retention_capability = payload.get("retention_capability")
        if not isinstance(retention_capability, Mapping):
            raise ValueError("retention_capability must be a mapping")
        compaction_capability = payload.get("compaction_capability")
        if not isinstance(compaction_capability, Mapping):
            raise ValueError("compaction_capability must be a mapping")
        backup_restore_support = payload.get("backup_restore_support")
        if not isinstance(backup_restore_support, Mapping):
            raise ValueError("backup_restore_support must be a mapping")
        return cls(
            persistence_profile_id=_require_non_empty_str(
                payload.get("persistence_profile_id"),
                "persistence_profile_id",
            ),
            provider_id=_require_non_empty_str(payload.get("provider_id"), "provider_id"),
            durability_level=_require_non_empty_str(payload.get("durability_level"), "durability_level"),
            replay_capability=_require_non_empty_str(payload.get("replay_capability"), "replay_capability"),
            retention_capability=dict(retention_capability),
            compaction_capability=dict(compaction_capability),
            consistency_model=_require_non_empty_str(payload.get("consistency_model"), "consistency_model"),
            ack_semantics=_require_non_empty_str(payload.get("ack_semantics"), "ack_semantics"),
            execution_plane_relation=_require_non_empty_str(
                payload.get("execution_plane_relation"),
                "execution_plane_relation",
            ),
            backend_execution_scope=_require_non_empty_str(
                payload.get("backend_execution_scope"),
                "backend_execution_scope",
            ),
            backup_restore_support=dict(backup_restore_support),
            eviction_policy_compatibility=_require_non_empty_str_list(
                payload.get("eviction_policy_compatibility"),
                "eviction_policy_compatibility",
            ),
            fail_closed_conditions=_require_non_empty_str_list(
                payload.get("fail_closed_conditions"),
                "fail_closed_conditions",
            ),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "persistence_profile_id": self.persistence_profile_id,
            "provider_id": self.provider_id,
            "durability_level": self.durability_level,
            "replay_capability": self.replay_capability,
            "retention_capability": dict(self.retention_capability),
            "compaction_capability": dict(self.compaction_capability),
            "consistency_model": self.consistency_model,
            "ack_semantics": self.ack_semantics,
            "execution_plane_relation": self.execution_plane_relation,
            "backend_execution_scope": self.backend_execution_scope,
            "backup_restore_support": dict(self.backup_restore_support),
            "eviction_policy_compatibility": list(self.eviction_policy_compatibility),
            "fail_closed_conditions": list(self.fail_closed_conditions),
        }
