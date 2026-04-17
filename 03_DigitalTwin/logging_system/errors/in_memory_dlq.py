from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from .dlq_contract import DLQConfig, DLQEntry, DLQStatistics, EDLQStatus


class InMemoryDeadLetterQueue:
    def __init__(self, config: DLQConfig | None = None) -> None:
        self._config = config or DLQConfig()
        self._entries: dict[str, DLQEntry] = {}
        self._lock = threading.RLock()
        self._entry_order: list[str] = []

    def add(
        self,
        error_code: str,
        message: str,
        payload: Any,
        metadata: dict[str, Any] | None = None,
    ) -> DLQEntry:
        with self._lock:
            if len(self._entries) >= self._config.max_entries:
                self._evict_oldest()

            entry_id = str(uuid.uuid4())
            entry = DLQEntry(
                entry_id=entry_id,
                error_code=error_code,
                message=message,
                payload=payload,
                status=EDLQStatus.PENDING,
                max_attempts=self._config.max_attempts,
                metadata=metadata or {},
            )
            self._entries[entry_id] = entry
            self._entry_order.append(entry_id)
            return entry

    def get(self, entry_id: str) -> DLQEntry | None:
        with self._lock:
            return self._entries.get(entry_id)

    def get_by_status(self, status: EDLQStatus) -> list[DLQEntry]:
        with self._lock:
            return [e for e in self._entries.values() if e.status == status]

    def update_status(self, entry_id: str, status: EDLQStatus) -> bool:
        with self._lock:
            if entry_id not in self._entries:
                return False
            entry = self._entries[entry_id]
            self._entries[entry_id] = DLQEntry(
                entry_id=entry.entry_id,
                error_code=entry.error_code,
                message=entry.message,
                payload=entry.payload,
                status=status,
                timestamp_utc=entry.timestamp_utc,
                retry_count=entry.retry_count,
                max_attempts=entry.max_attempts,
                next_retry_at=entry.next_retry_at,
                last_error=entry.last_error,
                metadata=entry.metadata,
            )
            return True

    def retry(self, entry_id: str) -> bool:
        with self._lock:
            if entry_id not in self._entries:
                return False
            entry = self._entries[entry_id]
            if entry.retry_count >= entry.max_attempts:
                return False
            next_retry = datetime.now(timezone.utc) + timedelta(seconds=self._config.retry_delay_seconds)
            self._entries[entry_id] = DLQEntry(
                entry_id=entry.entry_id,
                error_code=entry.error_code,
                message=entry.message,
                payload=entry.payload,
                status=EDLQStatus.RETRYING,
                timestamp_utc=entry.timestamp_utc,
                retry_count=entry.retry_count + 1,
                max_attempts=entry.max_attempts,
                next_retry_at=next_retry.isoformat(),
                last_error=entry.last_error,
                metadata=entry.metadata,
            )
            return True

    def discard(self, entry_id: str) -> bool:
        return self.update_status(entry_id, EDLQStatus.DISCARDED)

    def get_statistics(self) -> DLQStatistics:
        with self._lock:
            pending = sum(1 for e in self._entries.values() if e.status == EDLQStatus.PENDING)
            retrying = sum(1 for e in self._entries.values() if e.status == EDLQStatus.RETRYING)
            failed = sum(1 for e in self._entries.values() if e.status == EDLQStatus.FAILED)
            expired = sum(1 for e in self._entries.values() if e.status == EDLQStatus.EXPIRED)
            discarded = sum(1 for e in self._entries.values() if e.status == EDLQStatus.DISCARDED)
            return DLQStatistics(
                total_entries=len(self._entries),
                pending_entries=pending,
                retrying_entries=retrying,
                failed_entries=failed,
                expired_entries=expired,
                discarded_entries=discarded,
                total_retries=sum(e.retry_count for e in self._entries.values()),
            )

    def cleanup_expired(self) -> int:
        with self._lock:
            removed = 0
            now = datetime.now(timezone.utc)
            expired_ids = []
            for entry in self._entries.values():
                if entry.status == EDLQStatus.EXPIRED:
                    expired_ids.append(entry.entry_id)
                elif entry.next_retry_at:
                    retry_time = datetime.fromisoformat(entry.next_retry_at)
                    if retry_time < now:
                        expired_ids.append(entry.entry_id)
            for entry_id in expired_ids:
                del self._entries[entry_id]
                if entry_id in self._entry_order:
                    self._entry_order.remove(entry_id)
                removed += 1
            return removed

    def get_all(self) -> list[DLQEntry]:
        with self._lock:
            return [self._entries[eid] for eid in self._entry_order if eid in self._entries]

    def _evict_oldest(self) -> None:
        if self._entry_order:
            oldest_id = self._entry_order[0]
            del self._entries[oldest_id]
            self._entry_order.pop(0)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
