from __future__ import annotations

from typing import Any, Mapping

from ..dtos import ProductionProfileDTO


class ProductionProfileValidator:
    _ALLOWED_STATUS = {"active", "inactive", "deprecated"}

    def validate_shape(self, dto: ProductionProfileDTO) -> None:
        if dto.status not in self._ALLOWED_STATUS:
            raise ValueError("unsupported_production_profile_status")

    def validate_bindings(
        self,
        dto: ProductionProfileDTO,
        *,
        provider_payload: Mapping[str, Any],
        connection_payload: Mapping[str, Any],
        persistence_payload: Mapping[str, Any],
    ) -> None:
        provider = {str(k): v for k, v in dict(provider_payload).items()}
        connection = {str(k): v for k, v in dict(connection_payload).items()}
        persistence = {str(k): v for k, v in dict(persistence_payload).items()}

        provider_connection = str(provider.get("connection_profile_id", "")).strip()
        provider_persistence = str(provider.get("persistence_profile_id", "")).strip()
        provider_execution_profile = str(provider.get("required_execution_profile_id", "")).strip()

        if provider_connection != dto.connection_ref:
            raise ValueError("production_profile_connection_ref_mismatch")
        if provider_persistence != dto.persistence_ref:
            raise ValueError("production_profile_persistence_ref_mismatch")
        if provider_execution_profile != dto.required_execution_profile_id:
            raise ValueError("production_profile_execution_profile_mismatch")

        if str(connection.get("provider_id", "")).strip() != dto.provider_ref:
            raise ValueError("production_profile_connection_provider_mismatch")
        if str(persistence.get("provider_id", "")).strip() != dto.provider_ref:
            raise ValueError("production_profile_persistence_provider_mismatch")
