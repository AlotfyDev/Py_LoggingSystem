from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class PreviewerIntegrationPort(Protocol):
    def configure_profile(self, profile_payload: Mapping[str, Any]) -> None:
        ...

    def render_console(
        self,
        records: Sequence[Mapping[str, Any]],
        *,
        mode: str | None = None,
        limit: int = 50,
    ) -> str:
        ...

    def render_web(
        self,
        records: Sequence[Mapping[str, Any]],
        *,
        mode: str | None = None,
        limit: int = 50,
    ) -> Mapping[str, Any]:
        ...
