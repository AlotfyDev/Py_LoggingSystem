from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class ObservabilityViewerProviderPort(Protocol):
    def create_schema(self, schema_id: str, schema_payload: Mapping[str, Any]) -> None:
        ...

    def update_schema(self, schema_id: str, schema_payload: Mapping[str, Any]) -> None:
        ...

    def create_format(self, format_id: str, format_payload: Mapping[str, Any]) -> None:
        ...

    def update_format(self, format_id: str, format_payload: Mapping[str, Any]) -> None:
        ...

    def create_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        ...

    def update_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        ...

    def create_configuration(self, config_type: str, config_id: str, config_payload: Mapping[str, Any]) -> None:
        ...

    def update_configuration(self, config_type: str, config_id: str, config_payload: Mapping[str, Any]) -> None:
        ...

    def apply_configuration(self, config_type: str, config_id: str) -> Mapping[str, Any]:
        ...

    def render_console_preview(
        self,
        profile_id: str,
        envelope: Mapping[str, Any],
        content: Mapping[str, Any],
        mode: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    def render_web_preview(
        self,
        profile_id: str,
        envelope: Mapping[str, Any],
        content: Mapping[str, Any],
        mode: str | None = None,
    ) -> Mapping[str, Any]:
        ...
