from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Mapping, Protocol, runtime_checkable

from ..models.record import LogRecord


@runtime_checkable
class LogContainerManagerialPort(Protocol):
    def enqueue_pending(self, record: LogRecord, *, context: Mapping[str, Any] | None = None) -> None:
        ...

    def drain_pending(self) -> list[LogRecord]:
        ...

    def requeue_pending_front(self, records: Sequence[LogRecord]) -> None:
        ...

    def commit_dispatched(self, records: Sequence[LogRecord]) -> int:
        ...

    def subscribe_listener(self, listener_id: str, listener: Callable[[Mapping[str, Any]], None]) -> None:
        ...

    def notify_listeners(self, records: Sequence[LogRecord]) -> int:
        ...
