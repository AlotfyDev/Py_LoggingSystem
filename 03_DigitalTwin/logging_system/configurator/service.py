from __future__ import annotations

from typing import Any, Mapping

from .dtos.adapter_binding_dto import AdapterBindingDTO
from .dtos.connection_catalog_entry_dto import ConnectionCatalogEntryDTO
from .dtos.container_binding_dto import ContainerBindingDTO
from .dtos.execution_binding_dto import ExecutionBindingDTO
from .dtos.persistence_catalog_entry_dto import PersistenceCatalogEntryDTO
from .dtos.policy_dto import PolicyDTO
from .dtos.previewer_profile_dto import PreviewerProfileDTO
from .dtos.provider_catalog_entry_dto import ProviderCatalogEntryDTO
from .dtos.retention_dto import RetentionDTO
from .dtos.schema_dto import SchemaDTO
from .dtos.production_profile_dto import ProductionProfileDTO
from .mappers.configuration_mapper import (
    adapter_binding_from_existing,
    connection_catalog_entry_from_existing,
    container_binding_from_existing,
    execution_binding_from_existing,
    persistence_catalog_entry_from_existing,
    policy_from_existing,
    previewer_profile_from_existing,
    provider_catalog_entry_from_existing,
    retention_from_existing,
    schema_from_existing,
    production_profile_from_existing,
)
from .validators.configuration_validator import (
    ensure_identifier,
    ensure_payload_mapping,
    ensure_supported_config_type,
)


class ConfiguratorService:
    def __init__(self, owner: Any) -> None:
        self._owner = owner

    def create_configuration(self, config_type: str, config_id: str, config_payload: Mapping[str, Any]) -> None:
        normalized_type = ensure_supported_config_type(config_type)
        key = ensure_identifier(config_id, "config_id")
        payload = ensure_payload_mapping(config_payload)

        if normalized_type == "schema":
            dto = SchemaDTO.from_mapping(schema_id=key, payload=payload)
            self._owner.create_schema(key, dto.to_schema_payload())
            return
        if normalized_type == "policy":
            dto = PolicyDTO.from_mapping(policy_id=key, payload=payload)
            self._owner.create_policy(key, dto.to_policy_payload())
            return
        if normalized_type == "retention":
            dto = RetentionDTO.from_mapping(profile_id=key, payload=payload)
            self._owner.create_policy(key, dto.to_policy_payload())
            return
        if normalized_type == "previewer_profile":
            dto = PreviewerProfileDTO.from_mapping(profile_id=key, payload=payload)
            self._owner.create_runtime_profile(key, dto.to_profile_payload())
            return
        if normalized_type == "adapter_binding":
            dto = AdapterBindingDTO.from_mapping(binding_id=key, payload=payload)
            self._owner.create_policy(key, dto.to_policy_payload())
            return
        if normalized_type == "container_binding":
            dto = ContainerBindingDTO.from_mapping(binding_id=key, payload=payload)
            self._owner.create_policy(key, dto.to_policy_payload())
            return
        if normalized_type == "execution_binding":
            dto = ExecutionBindingDTO.from_mapping(binding_id=key, payload=payload)
            self._owner.create_policy(key, dto.to_policy_payload())
            return
        if normalized_type == "provider_catalog_entry":
            dto = ProviderCatalogEntryDTO.from_mapping(provider_id=key, payload=payload)
            self._owner.create_provider_catalog_entry(key, dto.to_catalog_payload())
            return
        if normalized_type == "connection_catalog_entry":
            dto = ConnectionCatalogEntryDTO.from_mapping(connector_profile_id=key, payload=payload)
            self._owner.create_connection_catalog_entry(key, dto.to_catalog_payload())
            return
        if normalized_type == "persistence_catalog_entry":
            dto = PersistenceCatalogEntryDTO.from_mapping(persistence_profile_id=key, payload=payload)
            self._owner.create_persistence_catalog_entry(key, dto.to_catalog_payload())
            return
        if normalized_type == "production_profile":
            dto = ProductionProfileDTO.from_mapping(profile_id=key, payload=payload)
            self._owner.create_production_profile(key, dto.to_profile_payload())
            return
        raise RuntimeError(f"unsupported config_type: {normalized_type}")

    def get_configuration(self, config_type: str, config_id: str) -> Mapping[str, Any]:
        normalized_type = ensure_supported_config_type(config_type)
        key = ensure_identifier(config_id, "config_id")

        if normalized_type == "schema":
            return schema_from_existing(key, self._owner.get_schema(key))
        if normalized_type == "policy":
            return policy_from_existing(key, self._owner.get_policy(key))
        if normalized_type == "retention":
            return retention_from_existing(key, self._owner.get_policy(key))
        if normalized_type == "previewer_profile":
            return previewer_profile_from_existing(key, self._owner.get_runtime_profile(key))
        if normalized_type == "adapter_binding":
            return adapter_binding_from_existing(key, self._owner.get_policy(key))
        if normalized_type == "container_binding":
            return container_binding_from_existing(key, self._owner.get_policy(key))
        if normalized_type == "execution_binding":
            return execution_binding_from_existing(key, self._owner.get_policy(key))
        if normalized_type == "provider_catalog_entry":
            return provider_catalog_entry_from_existing(key, self._owner.get_provider_catalog_entry(key))
        if normalized_type == "connection_catalog_entry":
            return connection_catalog_entry_from_existing(key, self._owner.get_connection_catalog_entry(key))
        if normalized_type == "persistence_catalog_entry":
            return persistence_catalog_entry_from_existing(key, self._owner.get_persistence_catalog_entry(key))
        if normalized_type == "production_profile":
            return production_profile_from_existing(key, self._owner.get_production_profile(key))
        raise RuntimeError(f"unsupported config_type: {normalized_type}")

    def update_configuration(self, config_type: str, config_id: str, config_payload: Mapping[str, Any]) -> None:
        normalized_type = ensure_supported_config_type(config_type)
        key = ensure_identifier(config_id, "config_id")
        payload = ensure_payload_mapping(config_payload)

        if normalized_type == "schema":
            dto = SchemaDTO.from_mapping(schema_id=key, payload=payload)
            self._owner.update_schema(key, dto.to_schema_payload())
            return
        if normalized_type == "policy":
            dto = PolicyDTO.from_mapping(policy_id=key, payload=payload)
            self._owner.update_policy(key, dto.to_policy_payload())
            return
        if normalized_type == "retention":
            dto = RetentionDTO.from_mapping(profile_id=key, payload=payload)
            self._owner.update_policy(key, dto.to_policy_payload())
            return
        if normalized_type == "previewer_profile":
            dto = PreviewerProfileDTO.from_mapping(profile_id=key, payload=payload)
            self._owner.update_runtime_profile(key, dto.to_profile_payload())
            return
        if normalized_type == "adapter_binding":
            dto = AdapterBindingDTO.from_mapping(binding_id=key, payload=payload)
            self._owner.update_policy(key, dto.to_policy_payload())
            return
        if normalized_type == "container_binding":
            dto = ContainerBindingDTO.from_mapping(binding_id=key, payload=payload)
            self._owner.update_policy(key, dto.to_policy_payload())
            return
        if normalized_type == "execution_binding":
            dto = ExecutionBindingDTO.from_mapping(binding_id=key, payload=payload)
            self._owner.update_policy(key, dto.to_policy_payload())
            return
        if normalized_type == "provider_catalog_entry":
            dto = ProviderCatalogEntryDTO.from_mapping(provider_id=key, payload=payload)
            self._owner.update_provider_catalog_entry(key, dto.to_catalog_payload())
            return
        if normalized_type == "connection_catalog_entry":
            dto = ConnectionCatalogEntryDTO.from_mapping(connector_profile_id=key, payload=payload)
            self._owner.update_connection_catalog_entry(key, dto.to_catalog_payload())
            return
        if normalized_type == "persistence_catalog_entry":
            dto = PersistenceCatalogEntryDTO.from_mapping(persistence_profile_id=key, payload=payload)
            self._owner.update_persistence_catalog_entry(key, dto.to_catalog_payload())
            return
        if normalized_type == "production_profile":
            dto = ProductionProfileDTO.from_mapping(profile_id=key, payload=payload)
            self._owner.update_production_profile(key, dto.to_profile_payload())
            return
        raise RuntimeError(f"unsupported config_type: {normalized_type}")

    def delete_configuration(self, config_type: str, config_id: str) -> None:
        normalized_type = ensure_supported_config_type(config_type)
        key = ensure_identifier(config_id, "config_id")

        if normalized_type == "schema":
            self._owner.delete_schema(key)
            return
        if normalized_type in {"policy", "retention", "adapter_binding", "container_binding", "execution_binding"}:
            self._owner.delete_policy(key)
            return
        if normalized_type == "previewer_profile":
            self._owner.delete_runtime_profile(key)
            return
        if normalized_type == "provider_catalog_entry":
            self._owner.delete_provider_catalog_entry(key)
            return
        if normalized_type == "connection_catalog_entry":
            self._owner.delete_connection_catalog_entry(key)
            return
        if normalized_type == "persistence_catalog_entry":
            self._owner.delete_persistence_catalog_entry(key)
            return
        if normalized_type == "production_profile":
            self._owner.delete_production_profile(key)
            return
        raise RuntimeError(f"unsupported config_type: {normalized_type}")

    def list_configuration_ids(self, config_type: str) -> list[str]:
        normalized_type = ensure_supported_config_type(config_type)
        if normalized_type == "schema":
            return self._owner.list_schema_ids()
        if normalized_type in {"policy", "retention", "adapter_binding", "container_binding", "execution_binding"}:
            return self._owner.list_policy_ids()
        if normalized_type == "previewer_profile":
            return self._owner.list_runtime_profile_ids()
        if normalized_type == "provider_catalog_entry":
            return self._owner.list_provider_catalog_entries()
        if normalized_type == "connection_catalog_entry":
            return self._owner.list_connection_catalog_entries()
        if normalized_type == "persistence_catalog_entry":
            return self._owner.list_persistence_catalog_entries()
        if normalized_type == "production_profile":
            return self._owner.list_production_profile_ids()
        raise RuntimeError(f"unsupported config_type: {normalized_type}")

    def apply_configuration(self, config_type: str, config_id: str) -> Mapping[str, Any]:
        normalized_type = ensure_supported_config_type(config_type)
        key = ensure_identifier(config_id, "config_id")

        if normalized_type == "schema":
            self._owner.activate_content_schema(key)
            return {"applied": True, "config_type": normalized_type, "config_id": key}

        if normalized_type == "policy":
            _ = self._owner.get_policy(key)
            return {"applied": True, "config_type": normalized_type, "config_id": key}

        if normalized_type == "retention":
            dto = RetentionDTO.from_existing(profile_id=key, payload=self._owner.get_policy(key))
            self._owner.configure_retention_and_eviction(
                max_records=dto.max_records,
                max_record_age_seconds=dto.max_record_age_seconds,
            )
            return {"applied": True, "config_type": normalized_type, "config_id": key}

        if normalized_type == "previewer_profile":
            dto = PreviewerProfileDTO.from_existing(profile_id=key, payload=self._owner.get_runtime_profile(key))
            self._owner.configure_previewer_profile(dto.profile_payload)
            return {"applied": True, "config_type": normalized_type, "config_id": key}

        if normalized_type == "adapter_binding":
            dto = AdapterBindingDTO.from_existing(binding_id=key, payload=self._owner.get_policy(key))
            self._owner.bind_adapter(dto.adapter_key)
            return {
                "applied": True,
                "config_type": normalized_type,
                "config_id": key,
                "adapter_key": dto.adapter_key,
            }

        if normalized_type == "container_binding":
            dto = ContainerBindingDTO.from_existing(binding_id=key, payload=self._owner.get_policy(key))
            status = self._owner.bind_container_assignment(
                container_binding_id=dto.container_binding_id,
                container_backend_profile_id=dto.container_backend_profile_id,
                container_lease_id=dto.container_lease_id,
            )
            return {
                "applied": True,
                "config_type": normalized_type,
                "config_id": key,
                "container_assignment": dict(status),
            }

        if normalized_type == "execution_binding":
            dto = ExecutionBindingDTO.from_existing(binding_id=key, payload=self._owner.get_policy(key))
            status = self._owner.bind_execution_assignment(
                execution_binding_id=dto.execution_binding_id,
                required_execution_profile_id=dto.required_execution_profile_id,
                execution_lease_id=dto.execution_lease_id,
                queue_policy_id=dto.queue_policy_id,
                thread_safety_mode=dto.thread_safety_mode,
            )
            return {
                "applied": True,
                "config_type": normalized_type,
                "config_id": key,
                "execution_assignment": dict(status),
            }

        if normalized_type == "provider_catalog_entry":
            _ = self._owner.get_provider_catalog_entry(key)
            integrity = self._owner.validate_provider_catalog_integrity()
            if not bool(integrity.get("pass_fail", False)):
                raise RuntimeError("provider_catalog_integrity_failed_during_apply")
            return {
                "applied": True,
                "config_type": normalized_type,
                "config_id": key,
                "catalog_integrity": dict(integrity),
            }

        if normalized_type == "connection_catalog_entry":
            _ = self._owner.get_connection_catalog_entry(key)
            integrity = self._owner.validate_provider_catalog_integrity()
            if not bool(integrity.get("pass_fail", False)):
                raise RuntimeError("provider_catalog_integrity_failed_during_apply")
            return {
                "applied": True,
                "config_type": normalized_type,
                "config_id": key,
                "catalog_integrity": dict(integrity),
            }

        if normalized_type == "persistence_catalog_entry":
            _ = self._owner.get_persistence_catalog_entry(key)
            integrity = self._owner.validate_provider_catalog_integrity()
            if not bool(integrity.get("pass_fail", False)):
                raise RuntimeError("provider_catalog_integrity_failed_during_apply")
            return {
                "applied": True,
                "config_type": normalized_type,
                "config_id": key,
                "catalog_integrity": dict(integrity),
            }

        if normalized_type == "production_profile":
            activation = self._owner.activate_production_profile(key)
            return {
                "applied": True,
                "config_type": normalized_type,
                "config_id": key,
                "activation": dict(activation),
            }

        raise RuntimeError(f"unsupported config_type: {normalized_type}")
