from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import uuid4


@dataclass
class DispatcherResolverPipeline:
    def resolve_dispatch_candidate(self, *, round_id: str, pending_count: int) -> Mapping[str, object]:
        current_round_id = str(round_id).strip()
        if current_round_id == "":
            raise ValueError("round_id is required")
        if pending_count < 0:
            raise ValueError("pending_count must be >= 0")
        return {
            "pipeline": "dispatcher",
            "round_id": current_round_id,
            "pending_count": pending_count,
            "dispatch_ready": pending_count > 0,
        }

    def resolve_dispatch_receiver_binding(self, *, adapter_key: str) -> Mapping[str, str]:
        current_adapter_key = str(adapter_key).strip()
        if current_adapter_key == "":
            raise ValueError("adapter_key is required")
        return {
            "pipeline": "dispatcher",
            "adapter_key": current_adapter_key,
        }

    def build_handoff_event(self, *, to_pipeline: str, slot_or_record_ref: str, reason: str) -> Mapping[str, str]:
        return {
            "handoff_id": f"handoff-{uuid4()}",
            "from_pipeline": "dispatcher",
            "to_pipeline": str(to_pipeline).strip(),
            "slot_or_record_ref": str(slot_or_record_ref).strip(),
            "reason": str(reason).strip(),
        }
