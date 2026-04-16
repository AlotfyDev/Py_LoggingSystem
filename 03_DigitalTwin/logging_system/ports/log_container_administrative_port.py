from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class LogContainerAdministrativePort(Protocol):
    def configure_retention(self, *, max_records: int, max_record_age_seconds: int | None = None) -> None:
        ...

    def configure_level_container_policy(self, policy_payload: Mapping[str, Any]) -> None:
        ...

    def configure_slot_lifecycle_policy(self, policy_payload: Mapping[str, Any]) -> None:
        ...

    def export_state(self) -> Mapping[str, Any]:
        ...

    def import_state(self, payload: Mapping[str, Any]) -> None:
        ...
