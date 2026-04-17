import json
import tempfile
import threading
import time
from pathlib import Path

import pytest

from logging_system.errors import DLQConfig, EDLQStatus, FileBasedDeadLetterQueue


class TestDLQBackupRecovery:
    def test_dlq_backup_created_on_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            backup_path = file_path.with_suffix(".bak")

            dlq = FileBasedDeadLetterQueue(
                file_path=file_path,
                enable_batch_writes=False
            )
            entry = dlq.add("ERROR1", "Test", None)
            assert file_path.exists()

            dlq.update_status(entry.entry_id, EDLQStatus.FAILED)

            assert backup_path.exists(), "Backup should be created after first update"

    def test_dlq_backup_preserves_old_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            backup_path = file_path.with_suffix(".bak")

            dlq = FileBasedDeadLetterQueue(
                file_path=file_path,
                enable_batch_writes=False
            )
            entry1 = dlq.add("ERROR1", "Original", None)
            dlq.update_status(entry1.entry_id, EDLQStatus.FAILED)

            backup_content = backup_path.read_text(encoding="utf-8")
            import json
            backup_lines = [json.loads(line) for line in backup_content.strip().split("\n")]
            backup_error_codes = {line["error_code"] for line in backup_lines}
            backup_statuses = {line["status"] for line in backup_lines}

            assert "ERROR1" in backup_error_codes
            assert "PENDING" in backup_statuses
            assert "FAILED" not in backup_statuses

    def test_dlq_recovery_from_backup_on_corruption(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            backup_path = file_path.with_suffix(".bak")

            dlq1 = FileBasedDeadLetterQueue(
                file_path=file_path,
                enable_batch_writes=False
            )
            entry1 = dlq1.add("ERROR1", "Test1", None)
            entry2 = dlq1.add("ERROR2", "Test2", None)
            dlq1.update_status(entry1.entry_id, EDLQStatus.FAILED)
            dlq1.flush()
            del dlq1

            assert backup_path.exists(), "Backup must exist after update"

            file_path.write_text("CORRUPTED JSON\nINVALID", encoding="utf-8")

            dlq2 = FileBasedDeadLetterQueue(file_path=file_path)
            assert len(dlq2) == 2

            retrieved1 = dlq2.get(entry1.entry_id)
            retrieved2 = dlq2.get(entry2.entry_id)
            assert retrieved1 is not None
            assert retrieved2 is not None

    def test_dlq_recovery_from_missing_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            backup_path = file_path.with_suffix(".bak")

            assert not backup_path.exists()

            dlq = FileBasedDeadLetterQueue(file_path=file_path)
            dlq.add("ERROR", "Test", None)

            assert len(dlq) == 1


class TestDLQBatchWriteOptimization:
    def test_dlq_batch_write_aggregates_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"

            dlq = FileBasedDeadLetterQueue(
                file_path=file_path,
                enable_batch_writes=True,
                batch_interval_seconds=10.0
            )

            entry1 = dlq.add("ERROR1", "Test1", None)
            entry2 = dlq.add("ERROR2", "Test2", None)

            assert len(dlq) == 2
            assert not file_path.exists()

            dlq.flush()

            assert file_path.exists()
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 2

    def test_dlq_batch_write_respects_interval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"

            dlq = FileBasedDeadLetterQueue(
                file_path=file_path,
                enable_batch_writes=True,
                batch_interval_seconds=0.5
            )

            dlq.add("ERROR1", "Test1", None)
            dlq.add("ERROR2", "Test2", None)

            assert not file_path.exists()

            time.sleep(0.6)

            assert file_path.exists()
            assert file_path.stat().st_size > 0

    def test_dlq_flush_writes_immediately(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"

            dlq = FileBasedDeadLetterQueue(
                file_path=file_path,
                enable_batch_writes=True,
                batch_interval_seconds=10.0
            )

            dlq.add("ERROR1", "Test1", None)
            dlq.add("ERROR2", "Test2", None)

            assert not file_path.exists()

            dlq.flush()

            assert file_path.exists()
            assert file_path.stat().st_size > 0

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 2

    def test_dlq_immediate_write_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"

            dlq = FileBasedDeadLetterQueue(
                file_path=file_path,
                enable_batch_writes=False
            )

            dlq.add("ERROR1", "Test1", None)

            assert file_path.stat().st_size > 0


class TestDLQPersistenceEndToEnd:
    def test_dlq_clear_removes_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            backup_path = file_path.with_suffix(".bak")

            dlq = FileBasedDeadLetterQueue(
                file_path=file_path,
                enable_batch_writes=False
            )
            entry = dlq.add("ERROR", "Test", None)
            dlq.update_status(entry.entry_id, EDLQStatus.FAILED)
            assert backup_path.exists()

            dlq.clear()

            assert not file_path.exists()
            assert not backup_path.exists()

    def test_dlq_destructor_flushes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"

            def create_and_delete():
                dlq = FileBasedDeadLetterQueue(
                    file_path=file_path,
                    enable_batch_writes=True,
                    batch_interval_seconds=60.0
                )
                dlq.add("ERROR1", "Test1", None)
                dlq.add("ERROR2", "Test2", None)
                dlq.flush()

            create_and_delete()

            assert file_path.exists()
            assert file_path.stat().st_size > 0

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 2

    def test_dlq_thread_safety_with_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "dlq.jsonl"
            config = DLQConfig(max_entries=200)
            dlq = FileBasedDeadLetterQueue(
                config=config,
                file_path=file_path,
                enable_batch_writes=True,
                batch_interval_seconds=0.5
            )
            errors = []

            def add_entries(start: int, count: int):
                try:
                    for i in range(start, start + count):
                        dlq.add(f"ERROR{i}", f"Test {i}", {"index": i})
                except Exception as e:
                    errors.append(e)

            threads = []
            for i in range(10):
                t = threading.Thread(target=add_entries, args=(i * 10, 10))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            dlq.flush()

            assert len(errors) == 0
            assert len(dlq) <= 200
