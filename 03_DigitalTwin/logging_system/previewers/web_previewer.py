from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass
class WebPreviewer:
    mode: str = "collective"

    def set_mode(self, mode: str) -> None:
        current_mode = str(mode).strip().lower()
        if current_mode not in {"pop_single", "collective", "system_pause"}:
            raise ValueError(f"unsupported web preview mode: {mode}")
        self.mode = current_mode

    def preview_payload(self, records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        if self.mode == "system_pause":
            return {"mode": self.mode, "records": []}
        if self.mode == "pop_single":
            return {"mode": self.mode, "records": [dict(records[0])] if len(records) > 0 else []}
        return {"mode": self.mode, "records": [dict(item) for item in records]}
