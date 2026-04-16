from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ExecutionBindingDTO:
    binding_id: str
    execution_binding_id: str
    required_execution_profile_id: str
    execution_lease_id: str | None
    queue_policy_id: str | None
    thread_safety_mode: str | None
    binding_metadata: dict[str, Any]
    config_version: str

    @classmethod
    def from_mapping(cls, binding_id: str, payload: Mapping[str, Any]) -> "ExecutionBindingDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("execution binding configuration payload must be a mapping")
        version = str(payload.get("config_version", "")).strip()
        if not version:
            raise ValueError("execution binding configuration requires non-empty config_version")

        execution_binding_id = str(payload.get("execution_binding_id", "")).strip()
        if not execution_binding_id:
            raise ValueError("execution binding configuration requires execution_binding_id")

        required_execution_profile_id = str(payload.get("required_execution_profile_id", "")).strip()
        if not required_execution_profile_id:
            raise ValueError("execution binding configuration requires required_execution_profile_id")

        execution_lease_value = payload.get("execution_lease_id")
        execution_lease_id: str | None = None
        if execution_lease_value is not None:
            execution_lease_id = str(execution_lease_value).strip() or None

        queue_policy_value = payload.get("queue_policy_id")
        queue_policy_id: str | None = None
        if queue_policy_value is not None:
            queue_policy_id = str(queue_policy_value).strip() or None

        thread_mode_value = payload.get("thread_safety_mode")
        thread_safety_mode: str | None = None
        if thread_mode_value is not None:
            thread_safety_mode = str(thread_mode_value).strip() or None

        binding_metadata = payload.get("binding_metadata", {})
        if not isinstance(binding_metadata, Mapping):
            raise ValueError("execution binding configuration requires binding_metadata mapping")

        return cls(
            binding_id=str(binding_id),
            execution_binding_id=execution_binding_id,
            required_execution_profile_id=required_execution_profile_id,
            execution_lease_id=execution_lease_id,
            queue_policy_id=queue_policy_id,
            thread_safety_mode=thread_safety_mode,
            binding_metadata=dict(binding_metadata),
            config_version=version,
        )

    @classmethod
    def from_existing(cls, binding_id: str, payload: Mapping[str, Any]) -> "ExecutionBindingDTO":
        if not isinstance(payload, Mapping):
            raise TypeError("execution binding payload must be a mapping")
        source: Mapping[str, Any]
        if "execution_binding" in payload and isinstance(payload["execution_binding"], Mapping):
            source = payload["execution_binding"]
            merged = dict(source)
            if "config_version" not in merged and "config_version" in payload:
                merged["config_version"] = payload["config_version"]
            source = merged
        else:
            source = payload

        if "config_version" not in source:
            source = {**dict(source), "config_version": "legacy-unversioned"}

        return cls.from_mapping(binding_id=binding_id, payload=source)

    def to_policy_payload(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "execution_binding": {
                "execution_binding_id": self.execution_binding_id,
                "required_execution_profile_id": self.required_execution_profile_id,
                "execution_lease_id": self.execution_lease_id,
                "queue_policy_id": self.queue_policy_id,
                "thread_safety_mode": self.thread_safety_mode,
                "binding_metadata": dict(self.binding_metadata),
            },
        }

    def to_mapping(self) -> dict[str, Any]:
        return {
            "config_version": self.config_version,
            "execution_binding_id": self.execution_binding_id,
            "required_execution_profile_id": self.required_execution_profile_id,
            "execution_lease_id": self.execution_lease_id,
            "queue_policy_id": self.queue_policy_id,
            "thread_safety_mode": self.thread_safety_mode,
            "binding_metadata": dict(self.binding_metadata),
        }
