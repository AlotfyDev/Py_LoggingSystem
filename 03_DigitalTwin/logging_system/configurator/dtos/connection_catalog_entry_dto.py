from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ConnectionCatalogEntryDTO:
    connector_profile_id: str
    config_version: str
    connection_payload: dict[str, Any]

    @classmethod
    def from_mapping(
        cls,
        connector_profile_id: str,
        payload: Mapping[str, Any],
    ) -> "ConnectionCatalogEntryDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("connection catalog configuration payload must be a mapping")
        version = str(payload.get("config_version", "")).strip()
        if not version:
            raise ValueError("connection catalog configuration requires non-empty config_version")

        body = payload.get("connection_entry", payload)
        if not isinstance(body, Mapping):
            raise ValueError("connection catalog configuration requires connection_entry mapping")

        effective_id = str(body.get("connector_profile_id", connector_profile_id)).strip()
        if effective_id == "":
            raise ValueError("connection catalog configuration requires connector_profile_id")
        if effective_id != str(connector_profile_id).strip():
            raise ValueError("connector_profile_id must match config_id")

        connection_payload = dict(body)
        connection_payload["connector_profile_id"] = effective_id

        return cls(
            connector_profile_id=effective_id,
            config_version=version,
            connection_payload=connection_payload,
        )

    @classmethod
    def from_existing(
        cls,
        connector_profile_id: str,
        payload: Mapping[str, Any],
    ) -> "ConnectionCatalogEntryDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("connection catalog payload must be a mapping")
        source = {"connection_entry": dict(payload), "config_version": "legacy-unversioned"}
        return cls.from_mapping(connector_profile_id=connector_profile_id, payload=source)

    def to_catalog_payload(self) -> dict[str, Any]:
        return dict(self.connection_payload)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "connector_profile_id": self.connector_profile_id,
            "connection_entry": dict(self.connection_payload),
        }

