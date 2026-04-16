from __future__ import annotations

from typing import Any, Mapping


LOGGING_VIEWER_SCHEMA_ID = "logging.schema.v1"
LOGGING_VIEWER_CONSOLE_FORMAT_ID = "logging.console.default.v1"
LOGGING_VIEWER_WEB_FORMAT_ID = "logging.web.default.v1"
LOGGING_VIEWER_PROFILE_ID = "logging.default"
LOGGING_VIEWER_SPECIALIZATION_CONFIG_ID = "logging.specialization_profile.default"


def build_logging_viewer_specialization_pack(**kwargs: Any) -> Mapping[str, Any]:
    module = _load_ovs_logging_specialization_module()
    return module.build_pack(**kwargs)


def map_record_to_viewer_envelope_and_content(record: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    module = _load_ovs_logging_specialization_module()
    return module.map_record(record)


def register_logging_viewer_specialization_pack(provider_port: Any, *, pack: Mapping[str, Any] | None = None) -> None:
    module = _load_ovs_logging_specialization_module()
    module.register_pack(provider_port, pack=pack)


def build_logging_viewer_specialization_profile_config(**kwargs: Any) -> Mapping[str, Any]:
    module = _load_ovs_logging_specialization_module()
    return module.build_profile_config(**kwargs)


def upsert_logging_viewer_specialization_profile_config(
    provider_port: Any,
    *,
    profile_config: Mapping[str, Any] | None = None,
) -> None:
    module = _load_ovs_logging_specialization_module()
    module.upsert_profile_config(provider_port, profile_config=profile_config)


def apply_logging_viewer_specialization_profile_config(
    provider_port: Any,
    *,
    config_id: str = LOGGING_VIEWER_SPECIALIZATION_CONFIG_ID,
) -> Mapping[str, Any]:
    module = _load_ovs_logging_specialization_module()
    return module.apply_profile_config(provider_port, config_id=config_id)


def _load_ovs_logging_specialization_module() -> Any:
    try:
        from observability_viewer_system.specialized import logging as ovs_logging
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency boundary
        raise RuntimeError(
            "observability_viewer_system.specialized.logging is required. "
            "Ensure ObservabilityViewerSystem DigitalTwin is available on PYTHONPATH."
        ) from exc
    return ovs_logging
