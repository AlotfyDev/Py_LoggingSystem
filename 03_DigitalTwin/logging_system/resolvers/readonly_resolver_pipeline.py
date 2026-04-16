from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import uuid4


@dataclass
class ReadOnlyResolverPipeline:
    def resolve_query_projection_scope(
        self,
        *,
        filters: Mapping[str, object] | None,
        page: int,
        page_size: int,
    ) -> Mapping[str, object]:
        if page <= 0:
            raise ValueError("page must be >= 1")
        if page_size <= 0 or page_size > 1000:
            raise ValueError("page_size must be between 1 and 1000")
        return {
            "pipeline": "readonly",
            "filters": dict(filters or {}),
            "page": page,
            "page_size": page_size,
        }

    def resolve_read_consistency_view(self, *, mode: str = "eventual") -> Mapping[str, str]:
        current_mode = str(mode).strip().lower()
        if current_mode not in {"eventual", "snapshot"}:
            raise ValueError(f"unsupported consistency mode: {mode}")
        return {
            "pipeline": "readonly",
            "consistency_mode": current_mode,
        }

    def build_handoff_event(self, *, to_pipeline: str, slot_or_record_ref: str, reason: str) -> Mapping[str, str]:
        return {
            "handoff_id": f"handoff-{uuid4()}",
            "from_pipeline": "readonly",
            "to_pipeline": str(to_pipeline).strip(),
            "slot_or_record_ref": str(slot_or_record_ref).strip(),
            "reason": str(reason).strip(),
        }
