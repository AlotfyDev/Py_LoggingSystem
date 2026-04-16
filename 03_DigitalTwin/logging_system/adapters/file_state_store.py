from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from ..ports.state_store_port import StateStorePort


@dataclass(frozen=True)
class FileStateStore(StateStorePort):
    state_file: Path

    def load_state(self) -> Mapping[str, Any]:
        if not self.state_file.exists():
            return {}
        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid state JSON at {self.state_file}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"State root must be object at {self.state_file}")
        return payload

    def save_state(self, state: Mapping[str, Any]) -> None:
        if not isinstance(state, Mapping):
            raise TypeError("state must be a mapping")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.state_file.with_suffix(self.state_file.suffix + ".tmp")
        temp_file.write_text(
            json.dumps(state, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        temp_file.replace(self.state_file)
