from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PolicyDTO:
    policy_id: str
    policy_payload: dict[str, Any]
    config_version: str

    @classmethod
    def from_mapping(cls, policy_id: str, payload: Mapping[str, Any]) -> "PolicyDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("policy configuration payload must be a mapping")
        version = str(payload.get("config_version", "")).strip()
        if not version:
            raise ValueError("policy configuration requires non-empty config_version")
        policy_payload = payload.get("policy_payload")
        if not isinstance(policy_payload, Mapping):
            raise ValueError("policy configuration requires policy_payload mapping")
        return cls(policy_id=str(policy_id), policy_payload=dict(policy_payload), config_version=version)

    @classmethod
    def from_existing(cls, policy_id: str, payload: Mapping[str, Any]) -> "PolicyDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("policy payload must be a mapping")
        version = str(payload.get("config_version") or "legacy-unversioned")
        policy_payload = dict(payload)
        policy_payload.pop("config_version", None)
        return cls(policy_id=str(policy_id), policy_payload=policy_payload, config_version=version)

    def to_policy_payload(self) -> dict[str, Any]:
        data = dict(self.policy_payload)
        data["config_version"] = self.config_version
        return data

    def to_mapping(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "policy_payload": dict(self.policy_payload),
        }
