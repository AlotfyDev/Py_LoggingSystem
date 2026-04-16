from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .e_log_level import ELogLevel


@dataclass(frozen=True)
class LogInfo:
    level: ELogLevel = ELogLevel.Info

    def submit(self, *, service: Any, message: str, attributes: Mapping[str, Any] | None = None, context: Mapping[str, Any] | None = None) -> str:
        return service.log(level=self.level.runtime_level, message=message, attributes=attributes, context=context)
