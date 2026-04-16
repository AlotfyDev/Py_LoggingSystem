from __future__ import annotations

from importlib.util import find_spec
import unittest

from logging_system.adapters.adapter_registry import AdapterRegistry
from logging_system.adapters.no_op_adapter import NoOpAdapter
from logging_system.adapters.open_telemetry_adapter import OpenTelemetryAdapter
from logging_system.adapters.unavailable_open_telemetry_adapter import UnavailableOpenTelemetryAdapter


class AdapterRegistryBehaviorTests(unittest.TestCase):
    def test_register_resolve_list_and_has(self) -> None:
        reg = AdapterRegistry()
        reg.register("telemetry.noop", NoOpAdapter())
        self.assertTrue(reg.has("telemetry.noop"))
        self.assertEqual(reg.list_keys(), ["telemetry.noop"])
        resolved = reg.resolve("telemetry.noop")
        self.assertIsInstance(resolved, NoOpAdapter)

    def test_register_overwrite_control(self) -> None:
        reg = AdapterRegistry()
        reg.register("telemetry.noop", NoOpAdapter())
        with self.assertRaises(KeyError):
            reg.register("telemetry.noop", NoOpAdapter(), overwrite=False)
        reg.register("telemetry.noop", NoOpAdapter(), overwrite=True)


class AdapterBehaviorTests(unittest.TestCase):
    def test_noop_adapter_has_capability_profile(self) -> None:
        adapter = NoOpAdapter()
        adapter.emit_signal("logging", {"x": 1})
        profile = adapter.capability_profile()
        self.assertEqual(profile["adapter_key"], "telemetry.noop")

    def test_unavailable_adapter_fails_closed(self) -> None:
        adapter = UnavailableOpenTelemetryAdapter("missing")
        with self.assertRaises(RuntimeError):
            adapter.emit_signal("logging", {"x": 1})

    def test_open_telemetry_adapter_behavior_matches_environment(self) -> None:
        adapter = OpenTelemetryAdapter()
        if find_spec("opentelemetry") is None:
            with self.assertRaises(RuntimeError):
                adapter.emit_signal("logging", {"x": 1})
        else:
            adapter.emit_signal("logging", {"x": 1})


if __name__ == "__main__":
    unittest.main()
