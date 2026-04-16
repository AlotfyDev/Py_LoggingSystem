from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import uuid4


@dataclass
class WriterResolverPipeline:
    def enforce_writer_authority_scope(self, actor_role: str) -> None:
        current_role = str(actor_role).strip().lower()
        if current_role not in {"writer", "system_writer", "manager"}:
            raise PermissionError(f"actor role is not allowed for writer pipeline: {actor_role}")

    def resolve_write_target(
        self,
        *,
        level: str,
        context: Mapping[str, object] | None = None,
    ) -> Mapping[str, str]:
        payload = dict(context or {})
        current_level = str(level).strip().upper()
        tenant = str(payload.get("tenant", "default")).strip() or "default"
        partition_key = f"tenant:{tenant}|level:{current_level}"
        return {
            "pipeline": "writer",
            "partition_key": partition_key,
            "level": current_level,
            "tenant": tenant,
        }

    def build_handoff_event(self, *, to_pipeline: str, slot_or_record_ref: str, reason: str) -> Mapping[str, str]:
        return {
            "handoff_id": f"handoff-{uuid4()}",
            "from_pipeline": "writer",
            "to_pipeline": str(to_pipeline).strip(),
            "slot_or_record_ref": str(slot_or_record_ref).strip(),
            "reason": str(reason).strip(),
        }
