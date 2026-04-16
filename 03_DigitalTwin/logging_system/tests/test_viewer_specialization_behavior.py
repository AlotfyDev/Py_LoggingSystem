from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys
from typing import Any, Mapping
import unittest

_OVS_DIGITAL_TWIN = Path(__file__).resolve().parents[4] / "03.0061_ObservabilityViewerSystem" / "03_DigitalTwin"
if str(_OVS_DIGITAL_TWIN) not in sys.path:
    sys.path.insert(0, str(_OVS_DIGITAL_TWIN))

from logging_system.adapters.observability_viewer_adapter import ObservabilityViewerAdapter
from logging_system.services.logging_service import LoggingService
from logging_system.specialization.logging_viewer_specialization import (
    LOGGING_VIEWER_PROFILE_ID,
    build_logging_viewer_specialization_pack,
)
from logging_system.tests.support import InMemoryStateStore


@dataclass
class FakeViewerProvider:
    schemas: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    formats: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    profiles: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    configurations: dict[str, dict[str, Mapping[str, Any]]] = field(default_factory=dict)

    def create_schema(self, schema_id: str, schema_payload: Mapping[str, Any]) -> None:
        if schema_id in self.schemas:
            raise KeyError("exists")
        self.schemas[schema_id] = dict(schema_payload)

    def update_schema(self, schema_id: str, schema_payload: Mapping[str, Any]) -> None:
        self.schemas[schema_id] = dict(schema_payload)

    def create_format(self, format_id: str, format_payload: Mapping[str, Any]) -> None:
        if format_id in self.formats:
            raise KeyError("exists")
        self.formats[format_id] = dict(format_payload)

    def update_format(self, format_id: str, format_payload: Mapping[str, Any]) -> None:
        self.formats[format_id] = dict(format_payload)

    def create_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        if profile_id in self.profiles:
            raise KeyError("exists")
        self.profiles[profile_id] = dict(profile_payload)

    def update_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        self.profiles[profile_id] = dict(profile_payload)

    def create_configuration(self, config_type: str, config_id: str, config_payload: Mapping[str, Any]) -> None:
        rows = self.configurations.setdefault(config_type, {})
        if config_id in rows:
            raise KeyError("exists")
        rows[config_id] = dict(config_payload)

    def update_configuration(self, config_type: str, config_id: str, config_payload: Mapping[str, Any]) -> None:
        rows = self.configurations.setdefault(config_type, {})
        rows[config_id] = dict(config_payload)

    def apply_configuration(self, config_type: str, config_id: str) -> Mapping[str, Any]:
        rows = self.configurations.setdefault(config_type, {})
        if config_id not in rows:
            raise KeyError("missing config")
        config = dict(rows[config_id])
        if config_type == "specialization_profile":
            profile_id = str(config["profile_id"])
            profile_payload = dict(config["profile_payload"])
            if profile_id in self.profiles:
                self.update_profile(profile_id, profile_payload)
            else:
                self.create_profile(profile_id, profile_payload)
        return {"applied": True, "config_type": config_type, "config_id": config_id}

    def render_console_preview(
        self,
        profile_id: str,
        envelope: Mapping[str, Any],
        content: Mapping[str, Any],
        mode: str | None = None,
    ) -> Mapping[str, Any]:
        return {
            "target": "console",
            "mode": mode or "collective",
            "payload": {
                "envelope": dict(envelope),
                "content": dict(content),
            },
        }

    def render_web_preview(
        self,
        profile_id: str,
        envelope: Mapping[str, Any],
        content: Mapping[str, Any],
        mode: str | None = None,
    ) -> Mapping[str, Any]:
        return {
            "target": "web",
            "mode": mode or "collective",
            "payload": {
                "envelope": dict(envelope),
                "content": dict(content),
            },
        }


class ViewerSpecializationBehaviorTests(unittest.TestCase):
    def test_specialization_pack_contains_required_surfaces(self) -> None:
        pack = build_logging_viewer_specialization_pack()
        self.assertIn("envelope_definition", pack)
        self.assertIn("schema", pack)
        self.assertIn("formats", pack)
        self.assertIn("profile", pack)
        self.assertIn("required_renderer_adapter_keys", pack)

    def test_adapter_registers_specialization_and_renders(self) -> None:
        provider = FakeViewerProvider()
        adapter = ObservabilityViewerAdapter(_viewer=provider)
        rows = [
            {
                "record_id": "r1",
                "created_at_utc": "2026-01-01T00:00:00Z",
                "payload": {"level": "INFO", "message": "hello"},
            }
        ]
        console = adapter.render_console(rows, mode="collective", limit=50)
        self.assertIn("hello", console)
        web = adapter.render_web(rows, mode="collective", limit=50)
        self.assertEqual(web["mode"], "collective")
        self.assertGreaterEqual(len(provider.schemas), 1)
        self.assertGreaterEqual(len(provider.formats), 2)
        self.assertIn(LOGGING_VIEWER_PROFILE_ID, provider.profiles)

    def test_logging_service_delegates_preview_to_bound_adapter(self) -> None:
        provider = FakeViewerProvider()
        integration = ObservabilityViewerAdapter(_viewer=provider)
        service = LoggingService(_state_store=InMemoryStateStore())
        service.bind_previewer_adapter(integration)
        service.log_info("delegated-preview")
        service.dispatch_round("round-view")

        console = service.preview_console(mode="collective", limit=10)
        web = service.preview_web(mode="collective", limit=10)
        self.assertIn("delegated-preview", console)
        self.assertEqual(web["mode"], "collective")


if __name__ == "__main__":
    unittest.main()
