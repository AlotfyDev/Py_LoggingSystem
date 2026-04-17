from __future__ import annotations

import json
import shutil
import threading
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .dlq_contract import DLQConfig, DLQEntry, EDLQStatus
from .in_memory_dlq import InMemoryDeadLetterQueue


class FileBasedDeadLetterQueue(InMemoryDeadLetterQueue):
    def __init__(
        self,
        config: DLQConfig | None = None,
        file_path: str | Path | None = None,
        enable_batch_writes: bool = True,
        batch_interval_seconds: float = 5.0,
    ) -> None:
        super().__init__(config)
        self._file_path = Path(file_path) if file_path else self._default_file_path()
        self._backup_path = self._file_path.with_suffix(".bak")
        self._write_lock = threading.Lock()
        self._enable_batch_writes = enable_batch_writes
        self._batch_interval = batch_interval_seconds
        self._pending_writes: set[str] = set()
        self._batch_timer: threading.Timer | None = None
        self._load_state()

    def _default_file_path(self) -> Path:
        return Path.home() / ".logging_system" / "dlq" / "entries.jsonl"

    def _load_state(self) -> None:
        if not self._file_path.exists():
            self._try_recover_from_backup()
            return

        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = self._deserialize_entry(data)
                        self._entries[entry.entry_id] = entry
                        self._entry_order.append(entry.entry_id)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            if not self._entries:
                self._try_recover_from_backup()
        except (OSError, IOError):
            self._try_recover_from_backup()

    def _try_recover_from_backup(self) -> bool:
        if not self._backup_path.exists():
            return False

        try:
            with open(self._backup_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entry = self._deserialize_entry(data)
                        self._entries[entry.entry_id] = entry
                        self._entry_order.append(entry.entry_id)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

            shutil.copy2(str(self._backup_path), str(self._file_path))
            return True
        except (OSError, IOError):
            return False

    def _create_backup(self) -> None:
        if self._file_path.exists():
            self._backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(self._file_path), str(self._backup_path))

    def _serialize_entry(self, entry: DLQEntry) -> dict[str, Any]:
        data = asdict(entry)
        return data

    def _deserialize_entry(self, data: dict[str, Any]) -> DLQEntry:
        return DLQEntry(
            entry_id=data["entry_id"],
            error_code=data["error_code"],
            message=data["message"],
            payload=data["payload"],
            status=EDLQStatus(data["status"]),
            timestamp_utc=data["timestamp_utc"],
            retry_count=data["retry_count"],
            max_attempts=data["max_attempts"],
            next_retry_at=data.get("next_retry_at"),
            last_error=data.get("last_error"),
            metadata=data.get("metadata", {}),
        )

    def _flush_pending_writes(self) -> None:
        with self._write_lock:
            if not self._pending_writes:
                return

            self._create_backup()
            temp_path = self._file_path.with_suffix(".tmp")
            try:
                self._file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(temp_path, "w", encoding="utf-8") as f:
                    for eid in self._entry_order:
                        if eid in self._entries and eid in self._pending_writes:
                            data = self._serialize_entry(self._entries[eid])
                            f.write(json.dumps(data, ensure_ascii=False) + "\n")
                shutil.move(str(temp_path), str(self._file_path))
                self._pending_writes.clear()
            except OSError:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)

    def _schedule_batch_write(self, entry_id: str) -> None:
        self._pending_writes.add(entry_id)
        if not self._enable_batch_writes:
            self._flush_pending_writes()
            return

        if self._batch_timer is not None:
            self._batch_timer.cancel()

        self._batch_timer = threading.Timer(self._batch_interval, self._flush_pending_writes)
        self._batch_timer.daemon = True
        self._batch_timer.start()

    def _save_to_file(self, entry: DLQEntry) -> None:
        with self._write_lock:
            temp_path = self._file_path.with_suffix(".tmp")
            try:
                self._create_backup()
                self._file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(temp_path, "w", encoding="utf-8") as f:
                    for eid in self._entry_order:
                        if eid in self._entries:
                            data = self._serialize_entry(self._entries[eid])
                            f.write(json.dumps(data, ensure_ascii=False) + "\n")
                shutil.move(str(temp_path), str(self._file_path))
            except OSError:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)

    def add(
        self,
        error_code: str,
        message: str,
        payload: Any,
        metadata: dict[str, Any] | None = None,
    ) -> DLQEntry:
        entry = super().add(error_code, message, payload, metadata)
        if self._enable_batch_writes:
            self._schedule_batch_write(entry.entry_id)
        else:
            self._save_to_file(entry)
        return entry

    def get(self, entry_id: str) -> DLQEntry | None:
        return super().get(entry_id)

    def get_by_status(self, status: EDLQStatus) -> list[DLQEntry]:
        return super().get_by_status(status)

    def update_status(self, entry_id: str, status: EDLQStatus) -> bool:
        result = super().update_status(entry_id, status)
        if result:
            entry = self._entries.get(entry_id)
            if entry:
                if self._enable_batch_writes:
                    self._schedule_batch_write(entry_id)
                else:
                    self._save_to_file(entry)
        return result

    def retry(self, entry_id: str) -> bool:
        result = super().retry(entry_id)
        if result:
            entry = self._entries.get(entry_id)
            if entry:
                if self._enable_batch_writes:
                    self._schedule_batch_write(entry_id)
                else:
                    self._save_to_file(entry)
        return result

    def retry_entry(self, entry_id: str, error: str | None = None) -> bool:
        with self._lock:
            if entry_id not in self._entries:
                return False
            entry = self._entries[entry_id]
            next_retry = datetime.now(timezone.utc) + timedelta(
                seconds=self._config.retry_delay_seconds
            )
            updated = DLQEntry(
                entry_id=entry.entry_id,
                error_code=entry.error_code,
                message=entry.message,
                payload=entry.payload,
                status=EDLQStatus.RETRYING,
                timestamp_utc=entry.timestamp_utc,
                retry_count=entry.retry_count + 1,
                max_attempts=entry.max_attempts,
                next_retry_at=next_retry.isoformat(),
                last_error=error,
                metadata=entry.metadata,
            )
            self._entries[entry_id] = updated
            if self._enable_batch_writes:
                self._schedule_batch_write(entry_id)
            else:
                self._save_to_file(updated)
            return True

    def discard(self, entry_id: str) -> bool:
        return self.update_status(entry_id, EDLQStatus.DISCARDED)

    def get_statistics(self):
        return super().get_statistics()

    def purge_expired(self, ttl_seconds: int = 86400) -> int:
        with self._lock:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(seconds=ttl_seconds)
            expired_ids = []
            for entry in self._entries.values():
                timestamp = datetime.fromisoformat(entry.timestamp_utc)
                if timestamp < cutoff:
                    expired_ids.append(entry.entry_id)

            for entry_id in expired_ids:
                if entry_id in self._entries:
                    del self._entries[entry_id]
                if entry_id in self._entry_order:
                    self._entry_order.remove(entry_id)

            if expired_ids:
                self._save_all_to_file()

            return len(expired_ids)

    def _save_all_to_file(self) -> None:
        with self._write_lock:
            self._create_backup()
            temp_path = self._file_path.with_suffix(".tmp")
            try:
                self._file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(temp_path, "w", encoding="utf-8") as f:
                    for eid in self._entry_order:
                        if eid in self._entries:
                            data = self._serialize_entry(self._entries[eid])
                            f.write(json.dumps(data, ensure_ascii=False) + "\n")
                shutil.move(str(temp_path), str(self._file_path))
            except OSError:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)

    def get_all(self) -> list[DLQEntry]:
        return super().get_all()

    def clear(self) -> int:
        self.flush()
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self._entry_order.clear()
            with self._write_lock:
                if self._file_path.exists():
                    self._file_path.unlink()
                if self._backup_path.exists():
                    self._backup_path.unlink()
            return count

    def flush(self) -> None:
        if self._batch_timer is not None:
            self._batch_timer.cancel()
            self._batch_timer = None
        self._flush_pending_writes()

    def __len__(self) -> int:
        return super().__len__()

    def __del__(self) -> None:
        self.flush()
