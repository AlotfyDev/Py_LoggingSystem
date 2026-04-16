from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PersistenceCatalogEntryDTO:
    persistence_profile_id: str
    config_version: str
    persistence_payload: dict[str, Any]

    @classmethod
    def from_mapping(
        cls,
        persistence_profile_id: str,
        payload: Mapping[str, Any],
    ) -> "PersistenceCatalogEntryDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("persistence catalog configuration payload must be a mapping")
        version = str(payload.get("config_version", "")).strip()
        if not version:
            raise ValueError("persistence catalog configuration requires non-empty config_version")

        body = payload.get("persistence_entry", payload)
        if not isinstance(body, Mapping):
            raise ValueError("persistence catalog configuration requires persistence_entry mapping")

        effective_id = str(body.get("persistence_profile_id", persistence_profile_id)).strip()
        if effective_id == "":
            raise ValueError("persistence catalog configuration requires persistence_profile_id")
        if effective_id != str(persistence_profile_id).strip():
            raise ValueError("persistence_profile_id must match config_id")

        persistence_payload = dict(body)
        persistence_payload["persistence_profile_id"] = effective_id

        return cls(
            persistence_profile_id=effective_id,
            config_version=version,
            persistence_payload=persistence_payload,
        )

    @classmethod
    def from_existing(
        cls,
        persistence_profile_id: str,
        payload: Mapping[str, Any],
    ) -> "PersistenceCatalogEntryDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("persistence catalog payload must be a mapping")
        source = {"persistence_entry": dict(payload), "config_version": "legacy-unversioned"}
        return cls.from_mapping(persistence_profile_id=persistence_profile_id, payload=source)

    def to_catalog_payload(self) -> dict[str, Any]:
        return dict(self.persistence_payload)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "persistence_profile_id": self.persistence_profile_id,
            "persistence_entry": dict(self.persistence_payload),
        }

