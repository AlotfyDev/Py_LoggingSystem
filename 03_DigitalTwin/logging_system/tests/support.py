from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class InMemoryStateStore:
    _state: dict[str, Any] = field(default_factory=dict)

    def load_state(self) -> Mapping[str, Any]:
        return dict(self._state)

    def save_state(self, state: Mapping[str, Any]) -> None:
        self._state = dict(state)
