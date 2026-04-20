from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Callable, TypeVar

if TYPE_CHECKING:
    pass

T = TypeVar("T")


class CancellationEvent:
    def __init__(self) -> None:
        self._event = threading.Event()

    def set(self) -> None:
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()

    def reset(self) -> None:
        self._event.clear()
