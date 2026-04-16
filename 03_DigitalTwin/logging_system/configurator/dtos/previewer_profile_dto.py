from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PreviewerProfileDTO:
    profile_id: str
    profile_payload: dict[str, Any]
    config_version: str

    @classmethod
    def from_mapping(cls, profile_id: str, payload: Mapping[str, Any]) -> "PreviewerProfileDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("previewer profile configuration payload must be a mapping")
        version = str(payload.get("config_version", "")).strip()
        if not version:
            raise ValueError("previewer profile configuration requires non-empty config_version")
        profile_payload = payload.get("profile_payload")
        if not isinstance(profile_payload, Mapping):
            raise ValueError("previewer profile configuration requires profile_payload mapping")
        return cls(profile_id=str(profile_id), profile_payload=dict(profile_payload), config_version=version)

    @classmethod
    def from_existing(cls, profile_id: str, payload: Mapping[str, Any]) -> "PreviewerProfileDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("previewer profile payload must be a mapping")
        version = str(payload.get("config_version") or "legacy-unversioned")
        profile_payload = dict(payload)
        profile_payload.pop("config_version", None)
        return cls(profile_id=str(profile_id), profile_payload=profile_payload, config_version=version)

    def to_profile_payload(self) -> dict[str, Any]:
        data = dict(self.profile_payload)
        data["config_version"] = self.config_version
        return data

    def to_mapping(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "profile_payload": dict(self.profile_payload),
        }
