from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ..level_api.e_log_level import ELogLevel


@dataclass
class LogLevelHandler:
    def normalize_envelope(
        self,
        *,
        level: str,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        parsed_level = ELogLevel.parse(level).runtime_level
        current_message = str(message).strip()
        if current_message == "":
            raise ValueError("message is required")
        current_attributes = dict(attributes or {})
        current_context = dict(context or {})
        payload = {
            "level": parsed_level,
            "message": current_message,
            "attributes": current_attributes,
            "context": current_context,
        }
        return payload, current_context

    def apply_schema_validation(
        self,
        *,
        payload: Mapping[str, Any],
        context: Mapping[str, Any],
        schema_validator: Callable[[Mapping[str, Any], Mapping[str, Any]], None] | None = None,
    ) -> None:
        if schema_validator is None:
            return
        schema_validator(payload, context)

    def route_to_level_container(
        self,
        *,
        level: str,
        record_id: str,
        level_containers: Any | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        if level_containers is None:
            return
        level_containers.add_record(level=level, record_id=record_id, context=context)

    def publish_dispatch_event(
        self,
        *,
        level: str,
        record_id: str,
        writer_resolver: Any | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> Mapping[str, str]:
        if writer_resolver is None:
            return {}
        writer_resolver.resolve_write_target(level=level, context=context)
        return writer_resolver.build_handoff_event(
            to_pipeline="dispatcher",
            slot_or_record_ref=record_id,
            reason=f"level:{level}",
        )

    def emit(
        self,
        *,
        level: str,
        message: str,
        attributes: Mapping[str, Any] | None,
        context: Mapping[str, Any] | None,
        emit_callable: Callable[[Mapping[str, Any], Mapping[str, Any] | None], str],
        level_containers: Any | None = None,
        writer_resolver: Any | None = None,
        schema_validator: Callable[[Mapping[str, Any], Mapping[str, Any]], None] | None = None,
    ) -> str:
        payload, current_context = self.normalize_envelope(
            level=level,
            message=message,
            attributes=attributes,
            context=context,
        )
        self.apply_schema_validation(payload=payload, context=current_context, schema_validator=schema_validator)
        record_id = emit_callable(payload, current_context)
        self.route_to_level_container(
            level=payload["level"],
            record_id=record_id,
            level_containers=level_containers,
            context=current_context,
        )
        self.publish_dispatch_event(
            level=payload["level"],
            record_id=record_id,
            writer_resolver=writer_resolver,
            context=current_context,
        )
        return record_id
