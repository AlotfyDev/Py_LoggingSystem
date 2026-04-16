from __future__ import annotations

from ..dtos import ProductionProfileDTO


def to_runtime_payload(dto: ProductionProfileDTO) -> dict[str, object]:
    payload = dto.to_mapping()
    payload["catalog_refs"] = {
        "provider_ref": dto.provider_ref,
        "connection_ref": dto.connection_ref,
        "persistence_ref": dto.persistence_ref,
    }
    payload["binding_refs"] = {
        "container_binding_id": dto.container_binding_id,
        "container_backend_profile_id": dto.container_backend_profile_id,
        "execution_binding_id": dto.execution_binding_id,
        "required_execution_profile_id": dto.required_execution_profile_id,
        "adapter_key": dto.adapter_key,
    }
    return payload
