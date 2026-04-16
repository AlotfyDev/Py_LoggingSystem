from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass
class LevelContainers:
    partition_strategy: str = "by_level"
    max_records_per_partition: int = 0
    _partitions: dict[str, deque[str]] = field(default_factory=lambda: defaultdict(deque))

    def configure(self, *, partition_strategy: str, max_records_per_partition: int = 0) -> None:
        strategy = str(partition_strategy).strip().lower()
        if strategy not in {"by_level", "by_tenant", "hybrid"}:
            raise ValueError(f"unsupported partition strategy: {partition_strategy}")
        if max_records_per_partition < 0:
            raise ValueError("max_records_per_partition must be >= 0")
        self.partition_strategy = strategy
        self.max_records_per_partition = max_records_per_partition

    def add_record(self, *, level: str, record_id: str, context: Mapping[str, object] | None = None) -> str:
        current_level = str(level).strip().upper()
        if current_level == "":
            raise ValueError("level is required")
        current_record_id = str(record_id).strip()
        if current_record_id == "":
            raise ValueError("record_id is required")

        partition_key = self._resolve_partition_key(level=current_level, context=context)
        partition = self._partitions[partition_key]
        partition.append(current_record_id)
        if self.max_records_per_partition > 0:
            while len(partition) > self.max_records_per_partition:
                partition.popleft()
        return partition_key

    def pop_record(self, *, level: str, context: Mapping[str, object] | None = None) -> str | None:
        partition_key = self._resolve_partition_key(level=str(level).strip().upper(), context=context)
        partition = self._partitions.get(partition_key)
        if partition is None or len(partition) == 0:
            return None
        return partition.popleft()

    def snapshot(self) -> dict[str, list[str]]:
        return {key: list(queue) for key, queue in self._partitions.items()}

    def partition_sizes(self) -> dict[str, int]:
        return {key: len(queue) for key, queue in self._partitions.items()}

    def _resolve_partition_key(self, *, level: str, context: Mapping[str, object] | None = None) -> str:
        payload = dict(context or {})
        tenant = str(payload.get("tenant", "")).strip()

        if self.partition_strategy == "by_level":
            return f"level:{level}"
        if self.partition_strategy == "by_tenant":
            if tenant == "":
                raise ValueError("tenant is required for by_tenant strategy")
            return f"tenant:{tenant}"
        if tenant == "":
            raise ValueError("tenant is required for hybrid strategy")
        return f"tenant:{tenant}|level:{level}"
