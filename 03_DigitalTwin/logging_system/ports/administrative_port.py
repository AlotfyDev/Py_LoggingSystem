from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class AdministrativePort(Protocol):
    # Backward-compatible upsert-style registration.
    def register_schema(self, schema_id: str, schema_payload: Mapping[str, Any]) -> None:
        ...

    # Explicit schema catalog CRUD.
    def create_schema(self, schema_id: str, schema_payload: Mapping[str, Any]) -> None:
        ...

    def get_schema(self, schema_id: str) -> Mapping[str, Any]:
        ...

    def update_schema(self, schema_id: str, schema_payload: Mapping[str, Any]) -> None:
        ...

    def delete_schema(self, schema_id: str) -> None:
        ...

    def list_schema_ids(self) -> list[str]:
        ...

    def register_policy(self, policy_id: str, policy_payload: Mapping[str, Any]) -> None:
        ...

    def create_policy(self, policy_id: str, policy_payload: Mapping[str, Any]) -> None:
        ...

    def get_policy(self, policy_id: str) -> Mapping[str, Any]:
        ...

    def update_policy(self, policy_id: str, policy_payload: Mapping[str, Any]) -> None:
        ...

    def delete_policy(self, policy_id: str) -> None:
        ...

    def list_policy_ids(self) -> list[str]:
        ...

    def configure_retention_and_eviction(
        self,
        *,
        max_records: int,
        max_record_age_seconds: int | None = None,
    ) -> None:
        ...

    def approve_runtime_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        ...

    def create_runtime_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        ...

    def get_runtime_profile(self, profile_id: str) -> Mapping[str, Any]:
        ...

    def update_runtime_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        ...

    def delete_runtime_profile(self, profile_id: str) -> None:
        ...

    def list_runtime_profile_ids(self) -> list[str]:
        ...

    def create_production_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        ...

    def get_production_profile(self, profile_id: str) -> Mapping[str, Any]:
        ...

    def update_production_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        ...

    def delete_production_profile(self, profile_id: str) -> None:
        ...

    def list_production_profile_ids(self) -> list[str]:
        ...

    def validate_production_profile_integrity(self) -> Mapping[str, Any]:
        ...

    def create_provider_catalog_entry(self, provider_id: str, provider_payload: Mapping[str, Any]) -> None:
        ...

    def get_provider_catalog_entry(self, provider_id: str) -> Mapping[str, Any]:
        ...

    def update_provider_catalog_entry(self, provider_id: str, provider_payload: Mapping[str, Any]) -> None:
        ...

    def delete_provider_catalog_entry(self, provider_id: str) -> None:
        ...

    def list_provider_catalog_entries(self) -> list[str]:
        ...

    def create_connection_catalog_entry(
        self,
        connector_profile_id: str,
        connection_payload: Mapping[str, Any],
    ) -> None:
        ...

    def get_connection_catalog_entry(self, connector_profile_id: str) -> Mapping[str, Any]:
        ...

    def update_connection_catalog_entry(
        self,
        connector_profile_id: str,
        connection_payload: Mapping[str, Any],
    ) -> None:
        ...

    def delete_connection_catalog_entry(self, connector_profile_id: str) -> None:
        ...

    def list_connection_catalog_entries(self) -> list[str]:
        ...

    def create_persistence_catalog_entry(
        self,
        persistence_profile_id: str,
        persistence_payload: Mapping[str, Any],
    ) -> None:
        ...

    def get_persistence_catalog_entry(self, persistence_profile_id: str) -> Mapping[str, Any]:
        ...

    def update_persistence_catalog_entry(
        self,
        persistence_profile_id: str,
        persistence_payload: Mapping[str, Any],
    ) -> None:
        ...

    def delete_persistence_catalog_entry(self, persistence_profile_id: str) -> None:
        ...

    def list_persistence_catalog_entries(self) -> list[str]:
        ...

    def validate_provider_catalog_integrity(self) -> Mapping[str, Any]:
        ...

    def create_configuration(self, config_type: str, config_id: str, config_payload: Mapping[str, Any]) -> None:
        ...

    def get_configuration(self, config_type: str, config_id: str) -> Mapping[str, Any]:
        ...

    def update_configuration(self, config_type: str, config_id: str, config_payload: Mapping[str, Any]) -> None:
        ...

    def delete_configuration(self, config_type: str, config_id: str) -> None:
        ...

    def list_configuration_ids(self, config_type: str) -> list[str]:
        ...

