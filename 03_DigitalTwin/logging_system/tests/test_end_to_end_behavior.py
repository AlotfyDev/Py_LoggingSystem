from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
import unittest

from logging_system.services.logging_service import LoggingService
from logging_system.tests.support import InMemoryStateStore


@dataclass
class CollectingAdapter:
    signals: list[Mapping[str, Any]] = field(default_factory=list)

    def emit_signal(self, signal_name: str, payload: Mapping[str, Any]) -> None:
        self.signals.append({"signal_name": signal_name, "payload": dict(payload)})

    def capability_profile(self) -> Mapping[str, Any]:
        return {
            "adapter_key": "telemetry.collector",
            "otel_semconv_profile": "otel.log.v1",
            "propagation_format": "w3c_tracecontext",
            "failure_mode": "raise",
        }


@dataclass
class FailingAdapter:
    def emit_signal(self, signal_name: str, payload: Mapping[str, Any]) -> None:
        raise RuntimeError("forced failure")

    def capability_profile(self) -> Mapping[str, Any]:
        return {
            "adapter_key": "telemetry.failing",
            "otel_semconv_profile": "otel.log.v1",
            "propagation_format": "w3c_tracecontext",
            "failure_mode": "raise",
        }


class EndToEndBehaviorTests(unittest.TestCase):
    def test_full_behavioral_flow(self) -> None:
        service = LoggingService(_state_store=InMemoryStateStore())
        collecting = CollectingAdapter()
        service._adapter_registry.register("telemetry.collector", collecting)  # intentional test-level injection
        service.bind_adapter("telemetry.collector")
        service.register_schema(
            "schema.default",
            {
                "required_keys": ["level", "message"],
                "properties": {
                    "level": {"type": "string"},
                    "message": {"type": "string", "min_length": 1},
                },
            },
        )
        service.register_policy("policy.default", {"retention": "bounded"})
        service.approve_runtime_profile("runtime.standard", {"enabled": True})
        service.configure_retention_and_eviction(max_records=3, max_record_age_seconds=3600)

        received: list[str] = []

        def listener(row: Mapping[str, Any]) -> None:
            payload = row.get("payload", {})
            if isinstance(payload, Mapping):
                received.append(str(payload.get("message")))

        service.subscribe_notifications("listener.main", listener)

        service.log(level="INFO", message="m1")
        service.log(level="WARN", message="m2")
        service.log(level="ERROR", message="m3")
        service.log(level="DEBUG", message="m4")
        service.dispatch_round("round.main")
        service.enforce_safepoint("sp.main")

        all_rows = service.query_projection(filters={})
        self.assertEqual(len(all_rows), 3)
        messages = [row["payload"]["message"] for row in all_rows]
        self.assertEqual(messages, ["m2", "m3", "m4"])

        self.assertEqual(len(collecting.signals), 4)
        self.assertEqual(received, ["m1", "m2", "m3", "m4"])

        ev = service.collect_operational_evidence()
        self.assertEqual(ev["totals"]["emitted"], 4)
        self.assertEqual(ev["totals"]["dispatched"], 4)
        self.assertEqual(ev["totals"]["evicted"], 1)
        self.assertEqual(ev["last_round_id"], "round.main")
        self.assertEqual(ev["last_safepoint_id"], "sp.main")

    def test_dispatch_failure_is_fail_closed_and_queue_is_preserved(self) -> None:
        service = LoggingService(_state_store=InMemoryStateStore())
        failing = FailingAdapter()
        service._adapter_registry.register("telemetry.failing", failing)
        service.bind_adapter("telemetry.failing")
        service.log(level="INFO", message="will-fail")
        with self.assertRaises(RuntimeError):
            service.dispatch_round("round.fail")

        ev = service.collect_operational_evidence()
        self.assertEqual(ev["queue_depth"], 1)
        self.assertEqual(ev["totals"]["dispatch_failures"], 1)
        self.assertEqual(ev["totals"]["dispatched"], 0)


if __name__ == "__main__":
    unittest.main()
