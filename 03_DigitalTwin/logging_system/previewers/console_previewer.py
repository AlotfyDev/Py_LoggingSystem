from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass
class ConsolePreviewer:
    mode: str = "collective"

    def set_mode(self, mode: str) -> None:
        current_mode = str(mode).strip().lower()
        if current_mode not in {"pop_single", "collective", "system_pause"}:
            raise ValueError(f"unsupported console preview mode: {mode}")
        self.mode = current_mode

    def format_record(self, record: Mapping[str, object]) -> str:
        payload = record.get("payload")
        if isinstance(payload, Mapping):
            level = str(payload.get("level", record.get("level", "UNKNOWN"))).upper()
            message = str(payload.get("message", record.get("message", "")))
        else:
            level = str(record.get("level", "UNKNOWN")).upper()
            message = str(record.get("message", ""))
        record_id = str(record.get("record_id", ""))
        return f"[{level}] {record_id} {message}".strip()

    def preview(self, records: Sequence[Mapping[str, object]]) -> str:
        if self.mode == "system_pause":
            return ""
        if len(records) == 0:
            return ""
        if self.mode == "pop_single":
            return self.format_record(records[0])
        return "\n".join(self.format_record(item) for item in records)
