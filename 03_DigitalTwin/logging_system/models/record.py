from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .utc_now_iso import utc_now_iso


@dataclass(frozen=True)
class LogRecord:
    record_id: str
    payload: Mapping[str, Any]
    created_at_utc: str = field(default_factory=utc_now_iso)
    dispatched_at_utc: str | None = None
    adapter_key: str | None = None

    def __post_init__(self) -> None:
        if self.record_id.strip() == "":
            raise ValueError("record_id is required")
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping")

    def to_projection(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "created_at_utc": self.created_at_utc,
            "dispatched_at_utc": self.dispatched_at_utc,
            "adapter_key": self.adapter_key,
            "payload": dict(self.payload),
        }

    def matches(self, filters: Mapping[str, Any]) -> bool:
        if len(filters) == 0:
            return True
        payload = self.payload
        return all(payload.get(key) == value for key, value in filters.items())
