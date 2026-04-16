from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable

from .previewer_integration_port import PreviewerIntegrationPort

@runtime_checkable
class ManagerialPort(Protocol):
    def bind_adapter(self, adapter_key: str) -> None:
        ...

    def bind_container_assignment(
        self,
        *,
        container_binding_id: str,
        container_backend_profile_id: str,
        container_lease_id: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    def unbind_container_assignment(self) -> None:
        ...

    def validate_container_assignment(self) -> bool:
        ...

    def get_container_assignment_status(self) -> Mapping[str, Any]:
        ...

    def bind_execution_assignment(
        self,
        *,
        execution_binding_id: str,
        required_execution_profile_id: str,
        execution_lease_id: str | None = None,
        queue_policy_id: str | None = None,
        thread_safety_mode: str | None = None,
    ) -> Mapping[str, Any]:
        ...

    def unbind_execution_assignment(self) -> None:
        ...

    def validate_execution_assignment(self) -> bool:
        ...

    def get_execution_assignment_status(self) -> Mapping[str, Any]:
        ...

    def dispatch_round(self, round_id: str) -> None:
        ...

    def enforce_safepoint(self, safepoint_id: str) -> None:
        ...

    def collect_operational_evidence(self) -> Mapping[str, Any]:
        ...

    def list_available_adapters(self) -> list[str]:
        ...

    def configure_dispatch_failure_policy(self, policy_payload: Mapping[str, Any]) -> None:
        ...

    def configure_signal_qos_profile(self, policy_payload: Mapping[str, Any]) -> None:
        ...

    def configure_mandatory_label_schema(self, policy_payload: Mapping[str, Any]) -> None:
        ...

    def configure_slot_lifecycle_policy(self, policy_payload: Mapping[str, Any]) -> None:
        ...

    def configure_level_container_policy(self, policy_payload: Mapping[str, Any]) -> None:
        ...

    def configure_resolver_pipeline_policy(self, policy_payload: Mapping[str, Any]) -> None:
        ...

    def configure_previewer_profile(self, profile_payload: Mapping[str, Any]) -> None:
        ...

    def configure_loglevel_api_policy(self, policy_payload: Mapping[str, Any]) -> None:
        ...


    def apply_configuration(self, config_type: str, config_id: str) -> Mapping[str, Any]:
        ...

    def activate_production_profile(self, profile_id: str) -> Mapping[str, Any]:
        ...

    def get_active_production_profile_id(self) -> str | None:
        ...

    def bind_previewer_adapter(self, adapter: PreviewerIntegrationPort) -> None:
        ...
