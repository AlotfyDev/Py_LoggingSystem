from __future__ import annotations

import unittest

from logging_system.models.envelope import LogEnvelope
from logging_system.models.record import LogRecord


class LogEnvelopeBehaviorTests(unittest.TestCase):
    def test_rejects_none_content(self) -> None:
        with self.assertRaises(ValueError):
            LogEnvelope(content=None, context={}, metadata={})  # type: ignore[arg-type]

    def test_rejects_none_context(self) -> None:
        with self.assertRaises(ValueError):
            LogEnvelope(content={"message": "ok"}, context=None, metadata={})  # type: ignore[arg-type]

    def test_rejects_none_metadata(self) -> None:
        with self.assertRaises(ValueError):
            LogEnvelope(content={"message": "ok"}, context={}, metadata=None)  # type: ignore[arg-type]


class LogRecordBehaviorTests(unittest.TestCase):
    def test_to_projection_contains_expected_fields(self) -> None:
        rec = LogRecord(
            record_id="r1",
            payload={"level": "INFO", "message": "hello"},
            adapter_key="telemetry.noop",
            dispatched_at_utc="2026-01-01T00:00:00.000Z",
        )
        proj = rec.to_projection()
        self.assertEqual(proj["record_id"], "r1")
        self.assertEqual(proj["adapter_key"], "telemetry.noop")
        self.assertEqual(proj["payload"]["message"], "hello")

    def test_matches_filters_against_payload(self) -> None:
        rec = LogRecord(record_id="r2", payload={"level": "ERROR", "message": "boom"})
        self.assertTrue(rec.matches({"level": "ERROR"}))
        self.assertFalse(rec.matches({"level": "INFO"}))


if __name__ == "__main__":
    unittest.main()
