from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ProviderCatalogEntryDTO:
    provider_id: str
    config_version: str
    provider_payload: dict[str, Any]

    @classmethod
    def from_mapping(cls, provider_id: str, payload: Mapping[str, Any]) -> "ProviderCatalogEntryDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("provider catalog configuration payload must be a mapping")
        version = str(payload.get("config_version", "")).strip()
        if not version:
            raise ValueError("provider catalog configuration requires non-empty config_version")

        body = payload.get("provider_entry", payload)
        if not isinstance(body, Mapping):
            raise ValueError("provider catalog configuration requires provider_entry mapping")

        effective_provider_id = str(body.get("provider_id", provider_id)).strip()
        if effective_provider_id == "":
            raise ValueError("provider catalog configuration requires provider_id")
        if effective_provider_id != str(provider_id).strip():
            raise ValueError("provider catalog configuration provider_id must match config_id")

        provider_payload = dict(body)
        provider_payload["provider_id"] = effective_provider_id

        return cls(
            provider_id=effective_provider_id,
            config_version=version,
            provider_payload=provider_payload,
        )

    @classmethod
    def from_existing(cls, provider_id: str, payload: Mapping[str, Any]) -> "ProviderCatalogEntryDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("provider catalog payload must be a mapping")
        source = {"provider_entry": dict(payload), "config_version": "legacy-unversioned"}
        return cls.from_mapping(provider_id=provider_id, payload=source)

    def to_catalog_payload(self) -> dict[str, Any]:
        return dict(self.provider_payload)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "provider_id": self.provider_id,
            "provider_entry": dict(self.provider_payload),
        }

