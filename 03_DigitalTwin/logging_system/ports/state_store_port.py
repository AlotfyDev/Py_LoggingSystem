from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class StateStorePort(Protocol):
    def load_state(self) -> Mapping[str, Any]:
        ...

    def save_state(self, state: Mapping[str, Any]) -> None:
        ...
