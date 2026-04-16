from __future__ import annotations

from typing import Any, Mapping

SUPPORTED_CONFIGURATION_TYPES = {
    "schema",
    "policy",
    "retention",
    "previewer_profile",
    "adapter_binding",
    "container_binding",
    "execution_binding",
    "provider_catalog_entry",
    "connection_catalog_entry",
    "persistence_catalog_entry",
    "production_profile",
}


def ensure_supported_config_type(config_type: str) -> str:
    normalized = str(config_type).strip().lower()
    if normalized not in SUPPORTED_CONFIGURATION_TYPES:
        allowed = ", ".join(sorted(SUPPORTED_CONFIGURATION_TYPES))
        raise ValueError(f"unsupported config_type '{config_type}'. allowed: {allowed}")
    return normalized


def ensure_identifier(identifier: str, field_name: str) -> str:
    value = str(identifier).strip()
    if not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def ensure_payload_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("configuration payload must be a mapping")
    return payload
