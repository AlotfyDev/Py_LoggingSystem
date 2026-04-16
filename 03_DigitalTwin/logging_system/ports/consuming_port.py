from __future__ import annotations

from collections.abc import Callable
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


@runtime_checkable
class ConsumingPort(Protocol):
    def submit_signal_or_request(
        self,
        payload: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> str:
        ...

    def query_projection(
        self,
        *,
        filters: Mapping[str, Any] | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Sequence[Mapping[str, Any]]:
        ...

    def subscribe_notifications(
        self,
        listener_id: str,
        listener: Callable[[Mapping[str, Any]], None],
    ) -> None:
        ...

    def read_only_inspection(self) -> Mapping[str, Any]:
        ...

    # Backward-compatible names retained for existing callers.
    def emit(self, payload: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> str:
        ...

    def query(self, filters: Mapping[str, Any] | None = None) -> Sequence[Mapping[str, Any]]:
        ...

    def log_debug(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        ...

    def log_info(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        ...

    def log_warn(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        ...

    def log_error(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        ...

    def log_fatal(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        ...

    def log_trace(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        ...
