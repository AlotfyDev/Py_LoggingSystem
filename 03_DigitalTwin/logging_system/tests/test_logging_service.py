from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from logging_system.adapters.adapter_registry import AdapterRegistry
from logging_system.adapters.file_state_store import FileStateStore
from logging_system.adapters.no_op_adapter import NoOpAdapter
from logging_system.models.default_content_schema_catalog import ERROR_CONTENT_SCHEMA_ID
from logging_system.services.logging_service import LoggingService
from logging_system.tests.support import InMemoryStateStore


class LoggingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = LoggingService(_state_store=InMemoryStateStore())
        self.service.bind_adapter("telemetry.noop")

    def test_admin_registries_and_evidence(self) -> None:
        self.service.register_schema(
            "schema.main",
            {
                "required_keys": ["message"],
                "properties": {
                    "message": {"type": "string", "min_length": 1},
                },
            },
        )
        self.service.register_policy("policy.retention", {"mode": "bounded"})
        self.service.approve_runtime_profile("runtime.default", {"enabled": True})

        evidence = self.service.collect_operational_evidence()
        self.assertEqual(evidence["schema_count"], 4)
        self.assertEqual(evidence["policy_count"], 1)
        self.assertEqual(evidence["runtime_profile_count"], 1)
        self.assertGreaterEqual(evidence["production_profile_count"], 1)

    def test_emit_dispatch_and_query(self) -> None:
        self.service.log(level="info", message="hello")
        pending = self.service.query_projection(filters={"message": "hello"})
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["state"], "pending")

        self.service.dispatch_round("round-001")
        dispatched = self.service.query_projection(filters={"message": "hello"})
        self.assertEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0]["state"], "dispatched")

    def test_safepoint_requires_empty_pending_queue(self) -> None:
        self.service.log(level="debug", message="queued")
        with self.assertRaises(RuntimeError):
            self.service.enforce_safepoint("sp-1")
        self.service.dispatch_round("round-1")
        self.service.enforce_safepoint("sp-1")

    def test_retention_limit_evicts_oldest(self) -> None:
        self.service.configure_retention_and_eviction(max_records=2)
        self.service.log(level="info", message="m1")
        self.service.log(level="info", message="m2")
        self.service.log(level="info", message="m3")
        self.service.dispatch_round("round-retention")
        rows = self.service.query_projection(filters={})
        self.assertEqual(len(rows), 2)
        messages = [item["payload"]["message"] for item in rows]
        self.assertEqual(messages, ["m2", "m3"])

    def test_subscribe_notifications(self) -> None:
        seen: list[str] = []

        def listener(record: dict[str, object]) -> None:
            payload = record.get("payload", {})
            if isinstance(payload, dict):
                seen.append(str(payload.get("message")))

        self.service.subscribe_notifications("listener-1", listener)
        self.service.log(level="warn", message="notify-me")
        self.service.dispatch_round("round-subscribe")
        self.assertEqual(seen, ["notify-me"])

    def test_default_content_schema_catalog_is_seeded(self) -> None:
        evidence = self.service.collect_operational_evidence()
        schema_ids = evidence["schema_ids"]
        self.assertIn("log.content.default.v1", schema_ids)
        self.assertIn("log.content.audit.v1", schema_ids)
        self.assertIn("log.content.error.v1", schema_ids)

    def test_emit_fails_closed_when_payload_violates_schema(self) -> None:
        with self.assertRaises(ValueError):
            self.service.emit(
                payload={
                    "level": "INFO",
                    # message missing
                    "attributes": {},
                    "context": {},
                }
            )

    def test_emit_uses_alternate_schema_from_context(self) -> None:
        record_id = self.service.emit(
            payload={
                "schema_id": ERROR_CONTENT_SCHEMA_ID,
                "level": "ERROR",
                "message": "failure",
                "error_code": "E-001",
                "attributes": {},
                "context": {},
            },
            context={"schema_id": ERROR_CONTENT_SCHEMA_ID},
        )
        self.assertTrue(record_id.startswith("logging-"))

    def test_register_schema_rejects_invalid_shape(self) -> None:
        with self.assertRaises(ValueError):
            self.service.register_schema("custom.schema.v1", {"required_keys": ["x"]})

    def test_schema_catalog_crud_for_custom_entry(self) -> None:
        schema_id = "custom.schema.v1"
        schema_payload = {
            "required_keys": ["message"],
            "properties": {
                "message": {"type": "string", "min_length": 1},
            },
        }
        self.service.create_schema(schema_id, schema_payload)
        self.assertIn(schema_id, self.service.list_schema_ids())
        row = self.service.get_schema(schema_id)
        self.assertEqual(row["required_keys"], ["message"])

        updated = {
            "required_keys": ["message", "attributes"],
            "properties": {
                "message": {"type": "string", "min_length": 1},
                "attributes": {"type": "object"},
            },
        }
        self.service.update_schema(schema_id, updated)
        row2 = self.service.get_schema(schema_id)
        self.assertEqual(row2["required_keys"], ["message", "attributes"])

        self.service.delete_schema(schema_id)
        self.assertNotIn(schema_id, self.service.list_schema_ids())

    def test_delete_protected_default_schema_is_blocked(self) -> None:
        with self.assertRaises(RuntimeError):
            self.service.delete_schema("log.content.default.v1")

    def test_schema_catalog_persists_across_service_instances_with_file_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            svc1 = LoggingService(_state_store=FileStateStore(state_path))
            svc1.create_schema(
                "persisted.schema.v1",
                {
                    "required_keys": ["message"],
                    "properties": {"message": {"type": "string", "min_length": 1}},
                },
            )

            svc2 = LoggingService(_state_store=FileStateStore(state_path))
            self.assertIn("persisted.schema.v1", svc2.list_schema_ids())


class AdapterRegistryTests(unittest.TestCase):
    def test_duplicate_key_rejected_without_overwrite(self) -> None:
        registry = AdapterRegistry()
        registry.register("telemetry.noop", NoOpAdapter())
        with self.assertRaises(KeyError):
            registry.register("telemetry.noop", NoOpAdapter())


if __name__ == "__main__":
    unittest.main()
