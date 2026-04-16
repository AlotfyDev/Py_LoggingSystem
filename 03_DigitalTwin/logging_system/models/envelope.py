from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from .utc_now_iso import utc_now_iso

TContent = TypeVar("TContent")
TContext = TypeVar("TContext")
TMeta = TypeVar("TMeta")


@dataclass(frozen=True)
class LogEnvelope(Generic[TContent, TContext, TMeta]):
    content: TContent
    context: TContext
    metadata: TMeta
    created_at_utc: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        if self.content is None:
            raise ValueError("content is required")
        if self.context is None:
            raise ValueError("context is required")
        if self.metadata is None:
            raise ValueError("metadata is required")
