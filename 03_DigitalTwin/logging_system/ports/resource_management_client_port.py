from __future__ import annotations

from collections.abc import Callable
from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class ResourceManagementClientPort(Protocol):
    def request_container_lease(
        self,
        *,
        logger_instance_id: str,
        container_binding_id: str,
        container_backend_profile_id: str,
    ) -> Mapping[str, Any]:
        ...

    def validate_container_lease(self, container_lease_id: str) -> bool:
        ...

    def get_container_lease(self, container_lease_id: str) -> Mapping[str, Any]:
        ...

    def release_container_lease(self, container_lease_id: str) -> None:
        ...

    def request_execution_lease(
        self,
        *,
        logger_instance_id: str,
        execution_binding_id: str,
        required_execution_profile_id: str,
    ) -> Mapping[str, Any]:
        ...

    def validate_execution_lease(self, execution_lease_id: str) -> bool:
        ...

    def get_execution_lease(self, execution_lease_id: str) -> Mapping[str, Any]:
        ...

    def release_execution_lease(self, execution_lease_id: str) -> None:
        ...

    def get_execution_profile(self, execution_profile_id: str) -> Mapping[str, Any]:
        ...

    def execute_dispatch_tasks(
        self,
        *,
        execution_lease_id: str,
        required_execution_profile_id: str,
        tasks: list[Callable[[], Any]],
    ) -> list[Any]:
        ...
