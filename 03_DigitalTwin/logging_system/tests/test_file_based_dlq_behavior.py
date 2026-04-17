import json
import tempfile
import threading
import time
from pathlib import Path

import pytest

from logging_system.errors import DLQConfig, EDLQStatus, FileBasedDeadLetterQueue


class TestFileBasedDLQPersistence:
    def test_dlq_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            dlq = FileBasedDeadLetterQueue(file_path=file_path)
            entry = dlq.add("ERROR1", "Test message", {"key": "value"})

            dlq2 = FileBasedDeadLetterQueue(file_path=file_path)
            retrieved = dlq2.get(entry.entry_id)
            assert retrieved is not None
            assert retrieved.error_code == "ERROR1"
            assert retrieved.message == "Test message"

    def test_dlq_corrupted_file_handling(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            file_path.write_text("invalid json\n{" + '"corrupted": true}\n', encoding="utf-8")

            dlq = FileBasedDeadLetterQueue(file_path=file_path)
            assert len(dlq) == 0

            entry = dlq.add("ERROR", "After corruption", None)
            assert entry is not None
            assert len(dlq) == 1

    def test_dlq_purge_expired(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            config = DLQConfig(max_entries=100, expiration_seconds=1)
            dlq = FileBasedDeadLetterQueue(config=config, file_path=file_path)

            dlq.add("ERROR1", "Old", None)
            time.sleep(1.1)

            dlq.add("ERROR2", "New", None)
            assert len(dlq) == 2

            purged = dlq.purge_expired(ttl_seconds=1)
            assert purged == 1
            assert len(dlq) == 1

            remaining = dlq.get_all()
            assert len(remaining) == 1
            assert remaining[0].error_code == "ERROR2"

    def test_dlq_retry_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            dlq = FileBasedDeadLetterQueue(file_path=file_path)
            entry = dlq.add("ERROR", "Test", None)

            result = dlq.retry_entry(entry.entry_id, "Network timeout")
            assert result is True

            updated = dlq.get(entry.entry_id)
            assert updated is not None
            assert updated.retry_count == 1
            assert updated.last_error == "Network timeout"
            assert updated.status == EDLQStatus.RETRYING

    def test_dlq_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            dlq = FileBasedDeadLetterQueue(file_path=file_path)
            dlq.add("ERROR1", "Test1", None)
            dlq.add("ERROR2", "Test2", None)
            assert len(dlq) == 2

            count = dlq.clear()
            assert count == 2
            assert len(dlq) == 0
            assert not file_path.exists()


class TestFileBasedDLQAtomicWrite:
    def test_dlq_atomic_write_on_add(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            dlq = FileBasedDeadLetterQueue(file_path=file_path)

            dlq.add("ERROR", "Test", None)
            assert file_path.exists()

            with open(file_path, "r", encoding="utf-8") as f:
                line = f.readline()
                data = json.loads(line)
                assert data["error_code"] == "ERROR"

    def test_dlq_atomic_write_on_retry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            dlq = FileBasedDeadLetterQueue(file_path=file_path)
            entry = dlq.add("ERROR", "Test", None)

            dlq.retry(entry.entry_id)

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                data = json.loads(content)
                assert data["retry_count"] == 1


class TestFileBasedDLQThreadSafety:
    def test_dlq_thread_safety(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            config = DLQConfig(max_entries=100)
            dlq = FileBasedDeadLetterQueue(config=config, file_path=file_path)
            errors = []

            def add_entries(start: int, count: int):
                try:
                    for i in range(start, start + count):
                        dlq.add(f"ERROR{i}", f"Test error {i}", {"index": i})
                except Exception as e:
                    errors.append(e)

            threads = []
            for i in range(10):
                t = threading.Thread(target=add_entries, args=(i * 10, 10))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            assert len(errors) == 0
            assert len(dlq) <= 100
