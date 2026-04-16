from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


CANONICAL_SLOT_STATES = (
    "NEW",
    "WRITING",
    "READY",
    "DISPATCHING",
    "DISPATCHED",
    "FAILED",
    "EVICTED",
)


@dataclass
class SlotLifecycle:
    _states: dict[str, str] = field(default_factory=dict)
    _substates: dict[str, str] = field(default_factory=dict)
    _transitions: dict[str, set[str]] = field(
        default_factory=lambda: {
            "NEW": {"WRITING"},
            "WRITING": {"READY", "FAILED"},
            "READY": {"DISPATCHING", "EVICTED"},
            "DISPATCHING": {"DISPATCHED", "FAILED"},
            "DISPATCHED": {"EVICTED"},
            "FAILED": {"EVICTED"},
            "EVICTED": set(),
        }
    )

    def create_slot(self, slot_id: str) -> None:
        current_slot_id = self._normalize_slot_id(slot_id)
        if current_slot_id in self._states:
            raise KeyError(f"slot_id already exists: {current_slot_id}")
        self._states[current_slot_id] = "NEW"

    def get_state(self, slot_id: str) -> str:
        current_slot_id = self._normalize_slot_id(slot_id)
        if current_slot_id not in self._states:
            raise KeyError(f"slot_id is not registered: {current_slot_id}")
        return self._states[current_slot_id]

    def set_state(self, slot_id: str, new_state: str, *, substate: str | None = None) -> None:
        current_slot_id = self._normalize_slot_id(slot_id)
        if current_slot_id not in self._states:
            raise KeyError(f"slot_id is not registered: {current_slot_id}")

        current_state = self._states[current_slot_id]
        target_state = str(new_state).strip().upper()
        if target_state not in CANONICAL_SLOT_STATES:
            raise ValueError(f"unsupported canonical slot state: {new_state}")
        if not self.can_transition(current_state, target_state):
            raise RuntimeError(f"invalid slot transition: {current_state}->{target_state}")

        self._states[current_slot_id] = target_state
        if substate is not None:
            normalized_substate = str(substate).strip()
            if normalized_substate == "":
                raise ValueError("substate cannot be empty")
            self._substates[current_slot_id] = normalized_substate

    def can_transition(self, from_state: str, to_state: str) -> bool:
        source = str(from_state).strip().upper()
        target = str(to_state).strip().upper()
        if source not in self._transitions:
            return False
        return target in self._transitions[source]

    def snapshot(self) -> Mapping[str, Mapping[str, str]]:
        return {
            slot_id: {
                "state": state,
                "substate": self._substates.get(slot_id, ""),
            }
            for slot_id, state in self._states.items()
        }

    @staticmethod
    def _normalize_slot_id(slot_id: str) -> str:
        current_slot_id = str(slot_id).strip()
        if current_slot_id == "":
            raise ValueError("slot_id is required")
        return current_slot_id
