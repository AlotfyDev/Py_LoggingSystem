from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..ports.observability_viewer_provider_port import ObservabilityViewerProviderPort
from ..ports.previewer_integration_port import PreviewerIntegrationPort
from ..specialization.logging_viewer_specialization import (
    LOGGING_VIEWER_PROFILE_ID,
    apply_logging_viewer_specialization_profile_config,
    build_logging_viewer_specialization_pack,
    build_logging_viewer_specialization_profile_config,
    map_record_to_viewer_envelope_and_content,
    register_logging_viewer_specialization_pack,
    upsert_logging_viewer_specialization_profile_config,
)


@dataclass
class ObservabilityViewerAdapter(PreviewerIntegrationPort):
    _viewer: ObservabilityViewerProviderPort
    _active_profile_id: str = LOGGING_VIEWER_PROFILE_ID
    _profile_payload_override: Mapping[str, Any] | None = None
    _registered: bool = field(default=False, init=False)

    def configure_profile(self, profile_payload: Mapping[str, Any]) -> None:
        if not isinstance(profile_payload, Mapping):
            raise TypeError("profile_payload must be a mapping")
        payload = dict(profile_payload)
        requested_profile_id = str(payload.get("profile_id", "")).strip()
        if requested_profile_id != "":
            self._active_profile_id = requested_profile_id
        self._profile_payload_override = payload
        self._registered = False

    def render_console(
        self,
        records: Sequence[Mapping[str, Any]],
        *,
        mode: str | None = None,
        limit: int = 50,
    ) -> str:
        self._ensure_specialization_registered()
        selected = list(records)[-max(1, limit) :]
        if len(selected) == 0:
            return ""
        if mode == "system_pause":
            return ""
        if mode == "pop_single":
            selected = [selected[0]]

        lines: list[str] = []
        for record in selected:
            envelope, content = map_record_to_viewer_envelope_and_content(record)
            rendered = self._viewer.render_console_preview(
                profile_id=self._active_profile_id,
                envelope=envelope,
                content=content,
                mode=mode,
            )
            payload = rendered.get("payload", {})
            line_payload = payload.get("content", payload) if isinstance(payload, Mapping) else {}
            level = str(line_payload.get("level", content.get("level", "INFO"))).upper()
            message = str(line_payload.get("message", content.get("message", "")))
            record_id = str(envelope.get("record_id", ""))
            lines.append(f"[{level}] {record_id} {message}".strip())
        return "\n".join(lines)

    def render_web(
        self,
        records: Sequence[Mapping[str, Any]],
        *,
        mode: str | None = None,
        limit: int = 50,
    ) -> Mapping[str, Any]:
        self._ensure_specialization_registered()
        selected = list(records)[-max(1, limit) :]
        if mode == "pop_single" and len(selected) > 1:
            selected = [selected[0]]
        if mode == "system_pause":
            return {"mode": "system_pause", "records": []}

        rendered_rows: list[Mapping[str, Any]] = []
        for record in selected:
            envelope, content = map_record_to_viewer_envelope_and_content(record)
            rendered_rows.append(
                self._viewer.render_web_preview(
                    profile_id=self._active_profile_id,
                    envelope=envelope,
                    content=content,
                    mode=mode,
                )
            )
        return {"mode": mode or "collective", "records": rendered_rows}

    def _ensure_specialization_registered(self) -> None:
        if self._registered:
            return
        pack = build_logging_viewer_specialization_pack()
        specialization_config = build_logging_viewer_specialization_profile_config(pack=pack)
        if self._profile_payload_override is not None:
            merged_profile = dict(pack["profile"]["profile_payload"])
            merged_profile.update(dict(self._profile_payload_override))
            pack = dict(pack)
            pack["profile"] = {
                "profile_id": self._active_profile_id,
                "profile_payload": merged_profile,
            }
            specialization_config = build_logging_viewer_specialization_profile_config(
                profile_id=self._active_profile_id,
                profile_payload=merged_profile,
                pack=pack,
            )
        register_logging_viewer_specialization_pack(self._viewer, pack=pack)
        upsert_logging_viewer_specialization_profile_config(self._viewer, profile_config=specialization_config)
        apply_logging_viewer_specialization_profile_config(self._viewer)
        self._registered = True
