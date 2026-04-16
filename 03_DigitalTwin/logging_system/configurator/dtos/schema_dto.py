from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class SchemaDTO:
    schema_id: str
    schema_payload: dict[str, Any]
    config_version: str

    @classmethod
    def from_mapping(cls, schema_id: str, payload: Mapping[str, Any]) -> "SchemaDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("schema configuration payload must be a mapping")
        version = str(payload.get("config_version", "")).strip()
        if not version:
            raise ValueError("schema configuration requires non-empty config_version")
        schema_payload = payload.get("schema_payload")
        if not isinstance(schema_payload, Mapping):
            raise ValueError("schema configuration requires schema_payload mapping")
        return cls(schema_id=str(schema_id), schema_payload=dict(schema_payload), config_version=version)

    @classmethod
    def from_existing(cls, schema_id: str, payload: Mapping[str, Any]) -> "SchemaDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("schema payload must be a mapping")
        version = str(payload.get("config_version") or "legacy-unversioned")
        schema_payload = dict(payload)
        schema_payload.pop("config_version", None)
        return cls(schema_id=str(schema_id), schema_payload=schema_payload, config_version=version)

    def to_schema_payload(self) -> dict[str, Any]:
        data = dict(self.schema_payload)
        data["config_version"] = self.config_version
        return data

    def to_mapping(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "schema_payload": dict(self.schema_payload),
        }
