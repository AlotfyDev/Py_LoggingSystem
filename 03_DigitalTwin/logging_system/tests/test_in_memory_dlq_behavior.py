import threading
import time

import pytest

from logging_system.errors import DLQConfig, EDLQStatus, InMemoryDeadLetterQueue


class TestDLQBasicOperations:
    def test_dlq_add(self):
        dlq = InMemoryDeadLetterQueue()
        entry = dlq.add("NETWORK_ERROR", "Connection failed", {"url": "http://test.com"})
        assert entry.error_code == "NETWORK_ERROR"
        assert entry.message == "Connection failed"
        assert entry.status == EDLQStatus.PENDING

    def test_dlq_get(self):
        dlq = InMemoryDeadLetterQueue()
        entry = dlq.add("ERROR", "Test error", None)
        retrieved = dlq.get(entry.entry_id)
        assert retrieved is not None
        assert retrieved.entry_id == entry.entry_id

    def test_dlq_get_nonexistent(self):
        dlq = InMemoryDeadLetterQueue()
        result = dlq.get("nonexistent-id")
        assert result is None


class TestDLQStatusUpdates:
    def test_dlq_update_status(self):
        dlq = InMemoryDeadLetterQueue()
        entry = dlq.add("ERROR", "Test", None)
        result = dlq.update_status(entry.entry_id, EDLQStatus.FAILED)
        assert result is True
        updated = dlq.get(entry.entry_id)
        assert updated is not None
        assert updated.status == EDLQStatus.FAILED

    def test_dlq_retry(self):
        dlq = InMemoryDeadLetterQueue()
        entry = dlq.add("ERROR", "Test", None)
        result = dlq.retry(entry.entry_id)
        assert result is True
        updated = dlq.get(entry.entry_id)
        assert updated is not None
        assert updated.status == EDLQStatus.RETRYING
        assert updated.retry_count == 1

    def test_dlq_retry_max_attempts(self):
        """max_attempts=N means N retries allowed (retry_count 0→1→...→N blocked)"""
        config = DLQConfig(max_attempts=2)
        dlq = InMemoryDeadLetterQueue(config)
        entry = dlq.add("ERROR", "Test", None)
        assert entry.retry_count == 0
        result1 = dlq.retry(entry.entry_id)
        assert result1 is True
        retrieved = dlq.get(entry.entry_id)
        assert retrieved is not None and retrieved.retry_count == 1
        result2 = dlq.retry(entry.entry_id)
        assert result2 is True
        retrieved = dlq.get(entry.entry_id)
        assert retrieved is not None and retrieved.retry_count == 2
        result3 = dlq.retry(entry.entry_id)
        assert result3 is False

    def test_dlq_discard(self):
        dlq = InMemoryDeadLetterQueue()
        entry = dlq.add("ERROR", "Test", None)
        result = dlq.discard(entry.entry_id)
        assert result is True
        updated = dlq.get(entry.entry_id)
        assert updated is not None
        assert updated.status == EDLQStatus.DISCARDED


class TestDLQFiltering:
    def test_dlq_get_by_status(self):
        dlq = InMemoryDeadLetterQueue()
        entry1 = dlq.add("ERROR1", "Test1", None)
        entry2 = dlq.add("ERROR2", "Test2", None)
        dlq.update_status(entry1.entry_id, EDLQStatus.FAILED)
        pending = dlq.get_by_status(EDLQStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].entry_id == entry2.entry_id

    def test_dlq_get_all(self):
        dlq = InMemoryDeadLetterQueue()
        entry1 = dlq.add("ERROR1", "Test1", None)
        entry2 = dlq.add("ERROR2", "Test2", None)
        all_entries = dlq.get_all()
        assert len(all_entries) == 2


class TestDLQStatistics:
    def test_dlq_statistics(self):
        dlq = InMemoryDeadLetterQueue()
        dlq.add("ERROR1", "Test1", None)
        dlq.add("ERROR2", "Test2", None)
        entry3 = dlq.add("ERROR3", "Test3", None)
        dlq.update_status(entry3.entry_id, EDLQStatus.FAILED)
        stats = dlq.get_statistics()
        assert stats.total_entries == 3
        assert stats.pending_entries == 2
        assert stats.failed_entries == 1


class TestDLQMaxEntries:
    def test_dlq_max_entries_eviction(self):
        config = DLQConfig(max_entries=2)
        dlq = InMemoryDeadLetterQueue(config)
        entry1 = dlq.add("ERROR1", "Test1", None)
        entry2 = dlq.add("ERROR2", "Test2", None)
        entry3 = dlq.add("ERROR3", "Test3", None)
        assert len(dlq) == 2
        assert dlq.get(entry1.entry_id) is None
        assert dlq.get(entry2.entry_id) is not None
        assert dlq.get(entry3.entry_id) is not None


class TestDLQThreadSafety:
    def test_dlq_thread_safety(self):
        config = DLQConfig(max_entries=100)
        dlq = InMemoryDeadLetterQueue(config)
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
