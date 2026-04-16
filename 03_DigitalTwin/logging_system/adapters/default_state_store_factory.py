from __future__ import annotations

import os
from pathlib import Path

from .file_state_store import FileStateStore


DEFAULT_STATE_ENV_VAR = "LOGSYS_STATE_FILE"


def build_default_state_store(state_file_override: str | None = None) -> FileStateStore:
    configured = state_file_override or os.environ.get(DEFAULT_STATE_ENV_VAR, "").strip()
    if configured != "":
        return FileStateStore(state_file=Path(configured))
    return FileStateStore(
        state_file=Path.home() / ".nk_system" / "03.0020_logging_system" / "logging_state.json"
    )
