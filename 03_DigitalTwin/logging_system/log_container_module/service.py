from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Mapping

from ..containers.level_containers import LevelContainers
from ..containers.slot_lifecycle import SlotLifecycle
from ..models.record import LogRecord


@dataclass
class LogContainerModuleService:
    _records: deque[LogRecord] = field(default_factory=deque)
    _pending_records: deque[LogRecord] = field(default_factory=deque)
    _listeners: dict[str, Callable[[Mapping[str, Any]], None]] = field(default_factory=dict)
    _level_containers: LevelContainers = field(default_factory=LevelContainers)
    _slot_lifecycle: SlotLifecycle = field(default_factory=SlotLifecycle)
    _max_records: int = 10_000
    _max_record_age_seconds: int | None = None
    _slot_lifecycle_policy: dict[str, Any] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def configure_retention(self, *, max_records: int, max_record_age_seconds: int | None = None) -> None:
        if max_records <= 0:
            raise ValueError("max_records must be > 0")
        if max_record_age_seconds is not None and max_record_age_seconds <= 0:
            raise ValueError("max_record_age_seconds must be > 0 when provided")
        with self._lock:
            self._max_records = max_records
            self._max_record_age_seconds = max_record_age_seconds
            self._apply_retention_locked()

    def configure_level_container_policy(self, policy_payload: Mapping[str, Any]) -> None:
        payload = dict(policy_payload)
        strategy = str(payload.get("partition_strategy", self._level_containers.partition_strategy))
        max_records = int(payload.get("max_records_per_partition", self._level_containers.max_records_per_partition))
        with self._lock:
            self._level_containers.configure(
                partition_strategy=strategy,
                max_records_per_partition=max_records,
            )

    def configure_slot_lifecycle_policy(self, policy_payload: Mapping[str, Any]) -> None:
        payload = dict(policy_payload)
        with self._lock:
            self._slot_lifecycle_policy = payload

    def enqueue_pending(self, record: LogRecord, *, context: Mapping[str, Any] | None = None) -> None:
        level = str(record.payload.get("level", "INFO")).strip().upper() or "INFO"
        with self._lock:
            self._pending_records.append(record)
            self._level_containers.add_record(level=level, record_id=record.record_id, context=context)

    def drain_pending(self) -> list[LogRecord]:
        with self._lock:
            batch = list(self._pending_records)
            self._pending_records.clear()
        return batch

    def requeue_pending_front(self, records: Sequence[LogRecord]) -> None:
        with self._lock:
            for record in reversed(list(records)):
                self._pending_records.appendleft(record)

    def commit_dispatched(self, records: Sequence[LogRecord]) -> int:
        with self._lock:
            before = len(self._records)
            self._records.extend(records)
            self._apply_retention_locked()
            return max(0, before + len(records) - len(self._records))

    def subscribe_listener(self, listener_id: str, listener: Callable[[Mapping[str, Any]], None]) -> None:
        key = str(listener_id).strip()
        if key == "":
            raise ValueError("listener_id is required")
        if not callable(listener):
            raise TypeError("listener must be callable")
        with self._lock:
            if key in self._listeners:
                raise KeyError(f"listener_id already registered: {key}")
            self._listeners[key] = listener

    def notify_listeners(self, records: Sequence[LogRecord]) -> int:
        with self._lock:
            listeners = list(self._listeners.values())
        failures = 0
        for record in records:
            view = record.to_projection()
            for listener in listeners:
                try:
                    listener(view)
                except Exception:  # noqa: BLE001
                    failures += 1
        return failures

    def list_dispatched_records(self) -> Sequence[LogRecord]:
        with self._lock:
            return list(self._records)

    def list_pending_records(self) -> Sequence[LogRecord]:
        with self._lock:
            return list(self._pending_records)

    def query_projection(
        self,
        *,
        filters: Mapping[str, Any] | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[Mapping[str, Any]]:
        selected: list[Mapping[str, Any]] = []
        normalized_filters = dict(filters or {})
        with self._lock:
            records = list(self._records)
            pending = list(self._pending_records)
        for record in records:
            if record.matches(normalized_filters):
                view = record.to_projection()
                view["state"] = "dispatched"
                selected.append(view)
        for record in pending:
            if record.matches(normalized_filters):
                view = record.to_projection()
                view["state"] = "pending"
                selected.append(view)
        start = (int(page) - 1) * int(page_size)
        end = start + int(page_size)
        return selected[start:end]

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending_records)

    def stored_count(self) -> int:
        with self._lock:
            return len(self._records)

    def partition_sizes(self) -> Mapping[str, int]:
        with self._lock:
            return self._level_containers.partition_sizes()

    def level_containers(self) -> LevelContainers:
        return self._level_containers

    def slot_lifecycle(self) -> SlotLifecycle:
        return self._slot_lifecycle

    def export_state(self) -> Mapping[str, Any]:
        with self._lock:
            return {
                "records": [self._serialize_record(record) for record in self._records],
                "pending_records": [self._serialize_record(record) for record in self._pending_records],
                "retention": {
                    "max_records": self._max_records,
                    "max_record_age_seconds": self._max_record_age_seconds,
                },
                "level_container": {
                    "partition_strategy": self._level_containers.partition_strategy,
                    "max_records_per_partition": self._level_containers.max_records_per_partition,
                },
                "slot_lifecycle_policy": dict(self._slot_lifecycle_policy),
            }

    def import_state(self, payload: Mapping[str, Any]) -> None:
        if not isinstance(payload, Mapping):
            return
        with self._lock:
            records = payload.get("records")
            if isinstance(records, list):
                parsed_records: deque[LogRecord] = deque()
                for item in records:
                    parsed = self._parse_record_payload(item)
                    if parsed is not None:
                        parsed_records.append(parsed)
                self._records = parsed_records

            pending_records = payload.get("pending_records")
            if isinstance(pending_records, list):
                parsed_pending: deque[LogRecord] = deque()
                for item in pending_records:
                    parsed = self._parse_record_payload(item)
                    if parsed is not None:
                        parsed_pending.append(parsed)
                self._pending_records = parsed_pending

            retention = payload.get("retention")
            if isinstance(retention, Mapping):
                max_records = retention.get("max_records")
                max_age = retention.get("max_record_age_seconds")
                if isinstance(max_records, int) and max_records > 0:
                    self._max_records = max_records
                if max_age is None:
                    self._max_record_age_seconds = None
                elif isinstance(max_age, int) and max_age > 0:
                    self._max_record_age_seconds = max_age

            level_container = payload.get("level_container")
            if isinstance(level_container, Mapping):
                strategy = str(level_container.get("partition_strategy", self._level_containers.partition_strategy))
                max_partition = int(
                    level_container.get("max_records_per_partition", self._level_containers.max_records_per_partition)
                )
                self._level_containers.configure(
                    partition_strategy=strategy,
                    max_records_per_partition=max_partition,
                )

            slot_lifecycle_policy = payload.get("slot_lifecycle_policy")
            if isinstance(slot_lifecycle_policy, Mapping):
                self._slot_lifecycle_policy = dict(slot_lifecycle_policy)

            self._apply_retention_locked()

    def _apply_retention_locked(self) -> None:
        if self._max_record_age_seconds is not None:
            cutoff = datetime.now(timezone.utc).timestamp() - self._max_record_age_seconds
            while len(self._records) > 0:
                first = self._records[0]
                created_utc = self._parse_utc(first.created_at_utc)
                if created_utc.timestamp() >= cutoff:
                    break
                self._records.popleft()
        while len(self._records) > self._max_records:
            self._records.popleft()

    @staticmethod
    def _parse_utc(value: str) -> datetime:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(timezone.utc)

    @staticmethod
    def _serialize_record(record: LogRecord) -> Mapping[str, Any]:
        return {
            "record_id": record.record_id,
            "payload": dict(record.payload),
            "created_at_utc": record.created_at_utc,
            "dispatched_at_utc": record.dispatched_at_utc,
            "adapter_key": record.adapter_key,
        }

    @staticmethod
    def _parse_record_payload(value: Any) -> LogRecord | None:
        if not isinstance(value, Mapping):
            return None
        record_id = value.get("record_id")
        payload = value.get("payload")
        created_at_utc = value.get("created_at_utc")
        if not isinstance(record_id, str) or not isinstance(payload, Mapping):
            return None
        if not isinstance(created_at_utc, str):
            return None
        dispatched_at_utc = value.get("dispatched_at_utc")
        if dispatched_at_utc is not None and not isinstance(dispatched_at_utc, str):
            dispatched_at_utc = None
        adapter_key = value.get("adapter_key")
        if adapter_key is not None and not isinstance(adapter_key, str):
            adapter_key = None
        return LogRecord(
            record_id=record_id,
            payload=dict(payload),
            created_at_utc=created_at_utc,
            dispatched_at_utc=dispatched_at_utc,
            adapter_key=adapter_key,
        )
