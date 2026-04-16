from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RetentionDTO:
    profile_id: str
    max_records: int
    max_record_age_seconds: int | None
    config_version: str

    @classmethod
    def from_mapping(cls, profile_id: str, payload: Mapping[str, Any]) -> "RetentionDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("retention configuration payload must be a mapping")
        version = str(payload.get("config_version", "")).strip()
        if not version:
            raise ValueError("retention configuration requires non-empty config_version")
        max_records = payload.get("max_records")
        if not isinstance(max_records, int) or max_records <= 0:
            raise ValueError("retention configuration requires max_records > 0")
        age = payload.get("max_record_age_seconds")
        if age is not None and (not isinstance(age, int) or age <= 0):
            raise ValueError("max_record_age_seconds must be a positive integer when provided")
        return cls(
            profile_id=str(profile_id),
            max_records=max_records,
            max_record_age_seconds=age,
            config_version=version,
        )

    @classmethod
    def from_existing(cls, profile_id: str, payload: Mapping[str, Any]) -> "RetentionDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("retention payload must be a mapping")
        source: Mapping[str, Any]
        if "retention" in payload and isinstance(payload["retention"], Mapping):
            source = payload["retention"]
            merged = dict(source)
            if "config_version" not in merged and "config_version" in payload:
                merged["config_version"] = payload["config_version"]
            source = merged
        else:
            source = payload
        if "config_version" not in source:
            source = {**dict(source), "config_version": "legacy-unversioned"}
        return cls.from_mapping(profile_id=profile_id, payload=source)

    def to_policy_payload(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "retention": {
                "max_records": self.max_records,
                "max_record_age_seconds": self.max_record_age_seconds,
            },
        }

    def to_mapping(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "max_records": self.max_records,
            "max_record_age_seconds": self.max_record_age_seconds,
        }
