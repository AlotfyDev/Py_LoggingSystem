from __future__ import annotations

import unittest

from logging_system.containers.level_containers import LevelContainers
from logging_system.containers.slot_lifecycle import SlotLifecycle
from logging_system.handlers.log_level_handler import LogLevelHandler
from logging_system.level_api.e_log_level import ELogLevel
from logging_system.previewers.console_previewer import ConsolePreviewer
from logging_system.previewers.web_previewer import WebPreviewer
from logging_system.resolvers.dispatcher_resolver_pipeline import DispatcherResolverPipeline
from logging_system.resolvers.readonly_resolver_pipeline import ReadOnlyResolverPipeline
from logging_system.resolvers.writer_resolver_pipeline import WriterResolverPipeline


class NewComponentsBehaviorTests(unittest.TestCase):
    def test_e_log_level_parse(self) -> None:
        self.assertEqual(ELogLevel.parse("warn"), ELogLevel.Warn)
        self.assertEqual(ELogLevel.parse("ERROR"), ELogLevel.ERR)
        with self.assertRaises(ValueError):
            ELogLevel.parse("unknown")

    def test_slot_lifecycle_transitions(self) -> None:
        lifecycle = SlotLifecycle()
        lifecycle.create_slot("slot-1")
        lifecycle.set_state("slot-1", "WRITING")
        lifecycle.set_state("slot-1", "READY")
        self.assertEqual(lifecycle.get_state("slot-1"), "READY")
        with self.assertRaises(RuntimeError):
            lifecycle.set_state("slot-1", "NEW")

    def test_level_containers_partitioning(self) -> None:
        containers = LevelContainers()
        pk = containers.add_record(level="INFO", record_id="r1")
        self.assertEqual(pk, "level:INFO")
        self.assertIn("r1", containers.snapshot()[pk])

        containers.configure(partition_strategy="hybrid")
        pk2 = containers.add_record(level="WARN", record_id="r2", context={"tenant": "alpha"})
        self.assertEqual(pk2, "tenant:alpha|level:WARN")

    def test_log_level_handler_emit_routes_record(self) -> None:
        records: list[tuple[dict[str, object], dict[str, object] | None]] = []
        containers = LevelContainers()
        resolver = WriterResolverPipeline()
        handler = LogLevelHandler()

        def fake_emit(payload: dict[str, object], context: dict[str, object] | None) -> str:
            records.append((payload, context))
            return "rec-001"

        record_id = handler.emit(
            level="info",
            message="hello",
            attributes={"a": 1},
            context={"tenant": "t1"},
            emit_callable=fake_emit,
            level_containers=containers,
            writer_resolver=resolver,
        )
        self.assertEqual(record_id, "rec-001")
        self.assertEqual(records[0][0]["level"], "INFO")

    def test_previewers_modes(self) -> None:
        row = {"record_id": "r1", "level": "INFO", "message": "hello"}
        console = ConsolePreviewer()
        self.assertIn("hello", console.preview([row]))
        console.set_mode("system_pause")
        self.assertEqual(console.preview([row]), "")

        web = WebPreviewer()
        web.set_mode("pop_single")
        payload = web.preview_payload([row, {"record_id": "r2"}])
        self.assertEqual(len(payload["records"]), 1)

    def test_resolver_pipelines(self) -> None:
        writer = WriterResolverPipeline()
        writer.enforce_writer_authority_scope("writer")
        with self.assertRaises(PermissionError):
            writer.enforce_writer_authority_scope("viewer")

        dispatcher = DispatcherResolverPipeline()
        candidate = dispatcher.resolve_dispatch_candidate(round_id="rd-1", pending_count=2)
        self.assertTrue(candidate["dispatch_ready"])

        readonly = ReadOnlyResolverPipeline()
        scope = readonly.resolve_query_projection_scope(filters={}, page=1, page_size=10)
        self.assertEqual(scope["page"], 1)


if __name__ == "__main__":
    unittest.main()
