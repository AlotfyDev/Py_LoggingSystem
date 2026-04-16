from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from ..containers.level_containers import LevelContainers
from ..containers.slot_lifecycle import SlotLifecycle
from ..models.record import LogRecord


@runtime_checkable
class LogContainerConsumingPort(Protocol):
    def list_dispatched_records(self) -> Sequence[LogRecord]:
        ...

    def list_pending_records(self) -> Sequence[LogRecord]:
        ...

    def query_projection(
        self,
        *,
        filters: Mapping[str, Any] | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[Mapping[str, Any]]:
        ...

    def pending_count(self) -> int:
        ...

    def stored_count(self) -> int:
        ...

    def partition_sizes(self) -> Mapping[str, int]:
        ...

    def level_containers(self) -> LevelContainers:
        ...

    def slot_lifecycle(self) -> SlotLifecycle:
        ...
