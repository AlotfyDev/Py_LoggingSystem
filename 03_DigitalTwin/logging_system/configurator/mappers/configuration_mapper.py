from __future__ import annotations

from typing import Any, Mapping

from ..dtos.adapter_binding_dto import AdapterBindingDTO
from ..dtos.connection_catalog_entry_dto import ConnectionCatalogEntryDTO
from ..dtos.container_binding_dto import ContainerBindingDTO
from ..dtos.execution_binding_dto import ExecutionBindingDTO
from ..dtos.persistence_catalog_entry_dto import PersistenceCatalogEntryDTO
from ..dtos.policy_dto import PolicyDTO
from ..dtos.previewer_profile_dto import PreviewerProfileDTO
from ..dtos.provider_catalog_entry_dto import ProviderCatalogEntryDTO
from ..dtos.retention_dto import RetentionDTO
from ..dtos.schema_dto import SchemaDTO
from ..dtos.production_profile_dto import ProductionProfileDTO


def schema_from_existing(config_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return SchemaDTO.from_existing(schema_id=config_id, payload=payload).to_mapping()


def policy_from_existing(config_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return PolicyDTO.from_existing(policy_id=config_id, payload=payload).to_mapping()


def retention_from_existing(config_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return RetentionDTO.from_existing(profile_id=config_id, payload=payload).to_mapping()


def previewer_profile_from_existing(config_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return PreviewerProfileDTO.from_existing(profile_id=config_id, payload=payload).to_mapping()


def adapter_binding_from_existing(config_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return AdapterBindingDTO.from_existing(binding_id=config_id, payload=payload).to_mapping()


def container_binding_from_existing(config_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return ContainerBindingDTO.from_existing(binding_id=config_id, payload=payload).to_mapping()


def execution_binding_from_existing(config_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return ExecutionBindingDTO.from_existing(binding_id=config_id, payload=payload).to_mapping()


def provider_catalog_entry_from_existing(config_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return ProviderCatalogEntryDTO.from_existing(provider_id=config_id, payload=payload).to_mapping()


def connection_catalog_entry_from_existing(config_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return ConnectionCatalogEntryDTO.from_existing(
        connector_profile_id=config_id,
        payload=payload,
    ).to_mapping()


def persistence_catalog_entry_from_existing(config_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return PersistenceCatalogEntryDTO.from_existing(
        persistence_profile_id=config_id,
        payload=payload,
    ).to_mapping()


def production_profile_from_existing(config_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return ProductionProfileDTO.from_existing(profile_id=config_id, payload=payload).to_mapping()
