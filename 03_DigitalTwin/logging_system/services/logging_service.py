from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Mapping
from uuid import uuid4

from ..adapters.adapter_registry import AdapterRegistry
from ..adapters.default_registry_factory import build_default_adapter_registry
from ..adapters.default_state_store_factory import build_default_state_store
from ..containers.level_containers import LevelContainers
from ..containers.slot_lifecycle import SlotLifecycle
from ..configurator.service import ConfiguratorService
from ..handlers.log_level_handler import LogLevelHandler
from ..level_api.log_debug import LogDebug
from ..level_api.log_error import LogError
from ..level_api.log_fatal import LogFatal
from ..level_api.log_info import LogInfo
from ..level_api.log_trace import LogTrace
from ..level_api.log_warn import LogWarn
from ..models.default_content_schema_catalog import (
    AUDIT_CONTENT_SCHEMA_ID,
    DEFAULT_CONTENT_SCHEMA_ID,
    ERROR_CONTENT_SCHEMA_ID,
    build_default_content_schema_catalog,
)
from ..models.record import LogRecord
from ..models.utc_now_iso import utc_now_iso
from ..log_container_module.service import LogContainerModuleService
from ..ports.administrative_port import AdministrativePort
from ..ports.consuming_port import ConsumingPort
from ..ports.log_container_provider_port import LogContainerProviderPort
from ..ports.managerial_port import ManagerialPort
from ..ports.previewer_integration_port import PreviewerIntegrationPort
from ..ports.resource_management_client_port import ResourceManagementClientPort
from ..ports.state_store_port import StateStorePort
from ..previewers.console_previewer import ConsolePreviewer
from ..previewers.web_previewer import WebPreviewer
from ..production_profiles.service import ProductionProfileCatalogService
from ..provider_catalogs.default_entries import (
    build_default_connection_entries,
    build_default_persistence_entries,
    build_default_provider_entries,
)
from ..provider_catalogs.service import ProviderCatalogService
from ..resource_management.adapters.in_memory_resource_management_client import InMemoryResourceManagementClient
from ..resolvers.dispatcher_resolver_pipeline import DispatcherResolverPipeline
from ..resolvers.readonly_resolver_pipeline import ReadOnlyResolverPipeline
from ..resolvers.writer_resolver_pipeline import WriterResolverPipeline

# Metrics integration
from ..observability.metrics.registry import MetricRegistry

# Tracing integration
from ..observability.tracing.context import TracingContext
from ..observability.tracing.types import ESpanKind

ALLOWED_THREAD_SAFETY_MODES = {
    "single_writer_per_partition",
    "thread_safe_locked",
    "lock_free_cas",
}

ALLOWED_BACKPRESSURE_ACTIONS = {
    "block",
    "drop_oldest",
    "drop_newest",
    "sample",
    "retry_with_jitter",
}


@dataclass
class LoggingService(AdministrativePort, ManagerialPort, ConsumingPort):
    _schema_registry: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    _policy_registry: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    _runtime_profiles: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    _production_profiles: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    _records: deque[LogRecord] = field(default_factory=deque)
    _pending_records: deque[LogRecord] = field(default_factory=deque)
    _listeners: dict[str, Callable[[Mapping[str, Any]], None]] = field(default_factory=dict)
    _audit_trail: list[Mapping[str, Any]] = field(default_factory=list)
    _adapter_registry: AdapterRegistry = field(default_factory=build_default_adapter_registry)
    _state_store: StateStorePort = field(default_factory=build_default_state_store)
    _log_container_module: LogContainerProviderPort = field(default_factory=LogContainerModuleService)
    _resource_management_client: ResourceManagementClientPort = field(default_factory=InMemoryResourceManagementClient)
    _provider_catalog_service: ProviderCatalogService = field(default_factory=ProviderCatalogService)
    _active_adapter_key: str = "telemetry.noop"
    _active_production_profile_id: str | None = None
    _active_content_schema_id: str = DEFAULT_CONTENT_SCHEMA_ID
    _container_binding_id: str = "container.binding.local.default"
    _container_backend_profile_id: str = "container.backend.local.inmemory"
    _container_lease_id: str | None = None
    _execution_binding_id: str = "execution.binding.local.default"
    _required_execution_profile_id: str = "exec.logging.local.default"
    _execution_lease_id: str | None = None
    _queue_policy_id: str = "queue.policy.default"
    _thread_safety_mode: str = "single_writer_per_partition"
    _allow_unbound_dispatch_fallback: bool = False
    _protected_schema_ids: set[str] = field(default_factory=set)
    _max_records: int = 10_000
    _max_record_age_seconds: int | None = None
    _lock: RLock = field(default_factory=RLock)
    _total_emitted: int = 0
    _total_dispatched: int = 0
    _total_evicted: int = 0
    _dispatch_failures: int = 0
    _listener_failures: int = 0
    _last_round_id: str | None = None
    _last_safepoint_id: str | None = None
    _level_containers: LevelContainers = field(default_factory=LevelContainers)
    _slot_lifecycle: SlotLifecycle = field(default_factory=SlotLifecycle)
    _writer_resolver_pipeline: WriterResolverPipeline = field(default_factory=WriterResolverPipeline)
    _dispatcher_resolver_pipeline: DispatcherResolverPipeline = field(default_factory=DispatcherResolverPipeline)
    _readonly_resolver_pipeline: ReadOnlyResolverPipeline = field(default_factory=ReadOnlyResolverPipeline)
    _log_level_handler: LogLevelHandler = field(default_factory=LogLevelHandler)
    _log_debug_api: LogDebug = field(default_factory=LogDebug)
    _log_info_api: LogInfo = field(default_factory=LogInfo)
    _log_warn_api: LogWarn = field(default_factory=LogWarn)
    _log_error_api: LogError = field(default_factory=LogError)
    _log_fatal_api: LogFatal = field(default_factory=LogFatal)
    _log_trace_api: LogTrace = field(default_factory=LogTrace)
    _console_previewer: ConsolePreviewer = field(default_factory=ConsolePreviewer)
    _web_previewer: WebPreviewer = field(default_factory=WebPreviewer)
    _preview_integration_adapter: PreviewerIntegrationPort | None = None
    _configurator_service: ConfiguratorService = field(init=False)
    _production_profile_service: ProductionProfileCatalogService = field(init=False)
    _metrics_registry: MetricRegistry = field(default_factory=MetricRegistry.get_instance)
    _tracing_context: TracingContext = field(default_factory=TracingContext)

    def __post_init__(self) -> None:
        default_catalog = build_default_content_schema_catalog()
        for schema_id, schema_payload in default_catalog.items():
            self._validate_schema_payload(schema_payload)
            self._schema_registry[schema_id] = dict(schema_payload)
        self._protected_schema_ids.update(
            {
                DEFAULT_CONTENT_SCHEMA_ID,
                AUDIT_CONTENT_SCHEMA_ID,
                ERROR_CONTENT_SCHEMA_ID,
            }
        )
        self._level_containers = self._log_container_module.level_containers()
        self._slot_lifecycle = self._log_container_module.slot_lifecycle()
        self._provider_catalog_service.seed_defaults_if_empty(
            provider_entries=build_default_provider_entries(),
            connection_entries=build_default_connection_entries(),
            persistence_entries=build_default_persistence_entries(),
        )
        self._production_profile_service = ProductionProfileCatalogService(
            self._production_profiles,
            provider_lookup=self.get_provider_catalog_entry,
            connection_lookup=self.get_connection_catalog_entry,
            persistence_lookup=self.get_persistence_catalog_entry,
        )
        self._production_profile_service.seed_defaults_if_empty()
        self._load_persisted_state()
        self._ensure_default_container_assignment()
        self._ensure_default_execution_assignment()
        if self._active_production_profile_id is None:
            with self._lock:
                default_profile_id = "prod.logging.local.default"
                if default_profile_id in self._production_profiles:
                    self._active_production_profile_id = default_profile_id
        self._configurator_service = ConfiguratorService(self)

    def _initialize_metrics(self) -> None:
        """Initialize metrics for logging service observability."""
        # These metrics will be created lazily on first use
        pass

    def register_schema(self, schema_id: str, schema_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(schema_id, "schema_id")
        with self._lock:
            exists = key in self._schema_registry
        if exists:
            self.update_schema(key, schema_payload)
            return
        self.create_schema(key, schema_payload)

    def create_schema(self, schema_id: str, schema_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(schema_id, "schema_id")
        value = self._copy_mapping(schema_payload, "schema_payload")
        self._validate_schema_payload(value)
        with self._lock:
            if key in self._schema_registry:
                raise KeyError(f"schema_id already exists: {key}")
            self._schema_registry[key] = value
            self._append_audit_event_locked(
                action="create_schema",
                payload={"schema_id": key},
            )
            self._persist_state_locked()

    def get_schema(self, schema_id: str) -> Mapping[str, Any]:
        key = self._validate_identifier(schema_id, "schema_id")
        with self._lock:
            schema_payload = self._schema_registry.get(key)
        if schema_payload is None:
            raise KeyError(f"schema_id is not registered: {key}")
        return dict(schema_payload)

    def update_schema(self, schema_id: str, schema_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(schema_id, "schema_id")
        value = self._copy_mapping(schema_payload, "schema_payload")
        self._validate_schema_payload(value)
        with self._lock:
            if key not in self._schema_registry:
                raise KeyError(f"schema_id is not registered: {key}")
            self._schema_registry[key] = value
            self._append_audit_event_locked(
                action="update_schema",
                payload={"schema_id": key},
            )
            self._persist_state_locked()

    def delete_schema(self, schema_id: str) -> None:
        key = self._validate_identifier(schema_id, "schema_id")
        with self._lock:
            if key not in self._schema_registry:
                raise KeyError(f"schema_id is not registered: {key}")
            if key in self._protected_schema_ids:
                raise RuntimeError(f"schema_id is protected and cannot be deleted: {key}")
            if key == self._active_content_schema_id:
                raise RuntimeError("cannot delete active content schema")
            del self._schema_registry[key]
            self._append_audit_event_locked(
                action="delete_schema",
                payload={"schema_id": key},
            )
            self._persist_state_locked()

    def list_schema_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._schema_registry.keys())

    def register_policy(self, policy_id: str, policy_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(policy_id, "policy_id")
        value = self._copy_mapping(policy_payload, "policy_payload")
        with self._lock:
            self._policy_registry[key] = value
            self._append_audit_event_locked(
                action="register_policy",
                payload={"policy_id": key},
            )
            self._persist_state_locked()

    def create_policy(self, policy_id: str, policy_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(policy_id, "policy_id")
        value = self._copy_mapping(policy_payload, "policy_payload")
        with self._lock:
            if key in self._policy_registry:
                raise KeyError(f"policy_id already exists: {key}")
            self._policy_registry[key] = value
            self._append_audit_event_locked(action="create_policy", payload={"policy_id": key})
            self._persist_state_locked()

    def get_policy(self, policy_id: str) -> Mapping[str, Any]:
        key = self._validate_identifier(policy_id, "policy_id")
        with self._lock:
            value = self._policy_registry.get(key)
        if value is None:
            raise KeyError(f"policy_id is not registered: {key}")
        return dict(value)

    def update_policy(self, policy_id: str, policy_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(policy_id, "policy_id")
        value = self._copy_mapping(policy_payload, "policy_payload")
        with self._lock:
            if key not in self._policy_registry:
                raise KeyError(f"policy_id is not registered: {key}")
            self._policy_registry[key] = value
            self._append_audit_event_locked(action="update_policy", payload={"policy_id": key})
            self._persist_state_locked()

    def delete_policy(self, policy_id: str) -> None:
        key = self._validate_identifier(policy_id, "policy_id")
        with self._lock:
            if key not in self._policy_registry:
                raise KeyError(f"policy_id is not registered: {key}")
            del self._policy_registry[key]
            self._append_audit_event_locked(action="delete_policy", payload={"policy_id": key})
            self._persist_state_locked()

    def list_policy_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._policy_registry.keys())

    def configure_retention_and_eviction(
        self,
        *,
        max_records: int,
        max_record_age_seconds: int | None = None,
    ) -> None:
        if max_records <= 0:
            raise ValueError("max_records must be > 0")
        if max_record_age_seconds is not None and max_record_age_seconds <= 0:
            raise ValueError("max_record_age_seconds must be > 0 when provided")
        with self._lock:
            self._max_records = max_records
            self._max_record_age_seconds = max_record_age_seconds
            self._append_audit_event_locked(
                action="configure_retention_and_eviction",
                payload={
                    "max_records": max_records,
                    "max_record_age_seconds": max_record_age_seconds,
                },
            )
            self._log_container_module.configure_retention(
                max_records=max_records,
                max_record_age_seconds=max_record_age_seconds,
            )
            self._persist_state_locked()

    def approve_runtime_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(profile_id, "profile_id")
        value = self._copy_mapping(profile_payload, "profile_payload")
        with self._lock:
            self._runtime_profiles[key] = value
            self._append_audit_event_locked(
                action="approve_runtime_profile",
                payload={"profile_id": key},
            )
            self._persist_state_locked()

    def create_runtime_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(profile_id, "profile_id")
        value = self._copy_mapping(profile_payload, "profile_payload")
        with self._lock:
            if key in self._runtime_profiles:
                raise KeyError(f"profile_id already exists: {key}")
            self._runtime_profiles[key] = value
            self._append_audit_event_locked(action="create_runtime_profile", payload={"profile_id": key})
            self._persist_state_locked()

    def get_runtime_profile(self, profile_id: str) -> Mapping[str, Any]:
        key = self._validate_identifier(profile_id, "profile_id")
        with self._lock:
            value = self._runtime_profiles.get(key)
        if value is None:
            raise KeyError(f"profile_id is not registered: {key}")
        return dict(value)

    def update_runtime_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(profile_id, "profile_id")
        value = self._copy_mapping(profile_payload, "profile_payload")
        with self._lock:
            if key not in self._runtime_profiles:
                raise KeyError(f"profile_id is not registered: {key}")
            self._runtime_profiles[key] = value
            self._append_audit_event_locked(action="update_runtime_profile", payload={"profile_id": key})
            self._persist_state_locked()

    def delete_runtime_profile(self, profile_id: str) -> None:
        key = self._validate_identifier(profile_id, "profile_id")
        with self._lock:
            if key not in self._runtime_profiles:
                raise KeyError(f"profile_id is not registered: {key}")
            del self._runtime_profiles[key]
            self._append_audit_event_locked(action="delete_runtime_profile", payload={"profile_id": key})
            self._persist_state_locked()

    def list_runtime_profile_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._runtime_profiles.keys())

    def create_production_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(profile_id, "profile_id")
        value = self._copy_mapping(profile_payload, "profile_payload")
        value["profile_id"] = key
        self._production_profile_service.create_profile(value)
        with self._lock:
            self._append_audit_event_locked(action="create_production_profile", payload={"profile_id": key})
            self._persist_state_locked()

    def get_production_profile(self, profile_id: str) -> Mapping[str, Any]:
        key = self._validate_identifier(profile_id, "profile_id")
        return self._production_profile_service.get_profile(key)

    def update_production_profile(self, profile_id: str, profile_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(profile_id, "profile_id")
        value = self._copy_mapping(profile_payload, "profile_payload")
        value["profile_id"] = key
        self._production_profile_service.update_profile(value)
        with self._lock:
            self._append_audit_event_locked(action="update_production_profile", payload={"profile_id": key})
            self._persist_state_locked()

    def delete_production_profile(self, profile_id: str) -> None:
        key = self._validate_identifier(profile_id, "profile_id")
        with self._lock:
            if self._active_production_profile_id == key:
                raise RuntimeError("cannot delete active production profile")
        self._production_profile_service.delete_profile(key)
        with self._lock:
            self._append_audit_event_locked(action="delete_production_profile", payload={"profile_id": key})
            self._persist_state_locked()

    def list_production_profile_ids(self) -> list[str]:
        return self._production_profile_service.list_profile_ids()

    def get_active_production_profile_id(self) -> str | None:
        with self._lock:
            return self._active_production_profile_id

    def validate_production_profile_integrity(self) -> Mapping[str, Any]:
        return self._production_profile_service.validate_integrity()

    def activate_production_profile(self, profile_id: str) -> Mapping[str, Any]:
        key = self._validate_identifier(profile_id, "profile_id")
        profile = dict(self._production_profile_service.get_profile(key))
        status = str(profile.get("status", "")).strip().lower()
        if status != "active":
            raise RuntimeError("cannot_activate_non_active_production_profile")
        binding_refs = profile.get("binding_refs")
        if not isinstance(binding_refs, Mapping):
            raise RuntimeError("production_profile_missing_binding_refs")
        container_binding_id = self._validate_identifier(
            str(binding_refs.get("container_binding_id", "")),
            "container_binding_id",
        )
        container_backend_profile_id = self._validate_identifier(
            str(binding_refs.get("container_backend_profile_id", "")),
            "container_backend_profile_id",
        )
        execution_binding_id = self._validate_identifier(
            str(binding_refs.get("execution_binding_id", "")),
            "execution_binding_id",
        )
        required_execution_profile_id = self._validate_identifier(
            str(binding_refs.get("required_execution_profile_id", "")),
            "required_execution_profile_id",
        )
        adapter_key = self._validate_identifier(str(binding_refs.get("adapter_key", "")), "adapter_key")

        self.bind_container_assignment(
            container_binding_id=container_binding_id,
            container_backend_profile_id=container_backend_profile_id,
            container_lease_id=None,
        )
        self.bind_execution_assignment(
            execution_binding_id=execution_binding_id,
            required_execution_profile_id=required_execution_profile_id,
            execution_lease_id=None,
        )
        self.bind_adapter(adapter_key)

        with self._lock:
            self._active_production_profile_id = key
            self._append_audit_event_locked(action="activate_production_profile", payload={"profile_id": key})
            self._persist_state_locked()
        return {
            "profile_id": key,
            "container_assignment": dict(self.get_container_assignment_status()),
            "execution_assignment": dict(self.get_execution_assignment_status()),
            "active_adapter_key": adapter_key,
        }

    def create_provider_catalog_entry(self, provider_id: str, provider_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(provider_id, "provider_id")
        value = self._copy_mapping(provider_payload, "provider_payload")
        value["provider_id"] = key
        self._provider_catalog_service.create_provider_entry(value)
        with self._lock:
            self._append_audit_event_locked(action="create_provider_catalog_entry", payload={"provider_id": key})
            self._persist_state_locked()

    def get_provider_catalog_entry(self, provider_id: str) -> Mapping[str, Any]:
        key = self._validate_identifier(provider_id, "provider_id")
        return self._provider_catalog_service.get_provider_entry(key)

    def update_provider_catalog_entry(self, provider_id: str, provider_payload: Mapping[str, Any]) -> None:
        key = self._validate_identifier(provider_id, "provider_id")
        value = self._copy_mapping(provider_payload, "provider_payload")
        value["provider_id"] = key
        self._provider_catalog_service.update_provider_entry(value)
        with self._lock:
            self._append_audit_event_locked(action="update_provider_catalog_entry", payload={"provider_id": key})
            self._persist_state_locked()

    def delete_provider_catalog_entry(self, provider_id: str) -> None:
        key = self._validate_identifier(provider_id, "provider_id")
        self._provider_catalog_service.delete_provider_entry(key)
        with self._lock:
            self._append_audit_event_locked(action="delete_provider_catalog_entry", payload={"provider_id": key})
            self._persist_state_locked()

    def list_provider_catalog_entries(self) -> list[str]:
        return self._provider_catalog_service.list_provider_ids()

    def create_connection_catalog_entry(
        self,
        connector_profile_id: str,
        connection_payload: Mapping[str, Any],
    ) -> None:
        key = self._validate_identifier(connector_profile_id, "connector_profile_id")
        value = self._copy_mapping(connection_payload, "connection_payload")
        value["connector_profile_id"] = key
        self._provider_catalog_service.create_connection_entry(value)
        with self._lock:
            self._append_audit_event_locked(
                action="create_connection_catalog_entry",
                payload={"connector_profile_id": key},
            )
            self._persist_state_locked()

    def get_connection_catalog_entry(self, connector_profile_id: str) -> Mapping[str, Any]:
        key = self._validate_identifier(connector_profile_id, "connector_profile_id")
        return self._provider_catalog_service.get_connection_entry(key)

    def update_connection_catalog_entry(
        self,
        connector_profile_id: str,
        connection_payload: Mapping[str, Any],
    ) -> None:
        key = self._validate_identifier(connector_profile_id, "connector_profile_id")
        value = self._copy_mapping(connection_payload, "connection_payload")
        value["connector_profile_id"] = key
        self._provider_catalog_service.update_connection_entry(value)
        with self._lock:
            self._append_audit_event_locked(
                action="update_connection_catalog_entry",
                payload={"connector_profile_id": key},
            )
            self._persist_state_locked()

    def delete_connection_catalog_entry(self, connector_profile_id: str) -> None:
        key = self._validate_identifier(connector_profile_id, "connector_profile_id")
        self._provider_catalog_service.delete_connection_entry(key)
        with self._lock:
            self._append_audit_event_locked(
                action="delete_connection_catalog_entry",
                payload={"connector_profile_id": key},
            )
            self._persist_state_locked()

    def list_connection_catalog_entries(self) -> list[str]:
        return self._provider_catalog_service.list_connection_profile_ids()

    def create_persistence_catalog_entry(
        self,
        persistence_profile_id: str,
        persistence_payload: Mapping[str, Any],
    ) -> None:
        key = self._validate_identifier(persistence_profile_id, "persistence_profile_id")
        value = self._copy_mapping(persistence_payload, "persistence_payload")
        value["persistence_profile_id"] = key
        self._provider_catalog_service.create_persistence_entry(value)
        with self._lock:
            self._append_audit_event_locked(
                action="create_persistence_catalog_entry",
                payload={"persistence_profile_id": key},
            )
            self._persist_state_locked()

    def get_persistence_catalog_entry(self, persistence_profile_id: str) -> Mapping[str, Any]:
        key = self._validate_identifier(persistence_profile_id, "persistence_profile_id")
        return self._provider_catalog_service.get_persistence_entry(key)

    def update_persistence_catalog_entry(
        self,
        persistence_profile_id: str,
        persistence_payload: Mapping[str, Any],
    ) -> None:
        key = self._validate_identifier(persistence_profile_id, "persistence_profile_id")
        value = self._copy_mapping(persistence_payload, "persistence_payload")
        value["persistence_profile_id"] = key
        self._provider_catalog_service.update_persistence_entry(value)
        with self._lock:
            self._append_audit_event_locked(
                action="update_persistence_catalog_entry",
                payload={"persistence_profile_id": key},
            )
            self._persist_state_locked()

    def delete_persistence_catalog_entry(self, persistence_profile_id: str) -> None:
        key = self._validate_identifier(persistence_profile_id, "persistence_profile_id")
        self._provider_catalog_service.delete_persistence_entry(key)
        with self._lock:
            self._append_audit_event_locked(
                action="delete_persistence_catalog_entry",
                payload={"persistence_profile_id": key},
            )
            self._persist_state_locked()

    def list_persistence_catalog_entries(self) -> list[str]:
        return self._provider_catalog_service.list_persistence_profile_ids()

    def validate_provider_catalog_integrity(self) -> Mapping[str, Any]:
        return self._provider_catalog_service.validate_integrity()


    def create_configuration(self, config_type: str, config_id: str, config_payload: Mapping[str, Any]) -> None:
        self._configurator_service.create_configuration(config_type, config_id, config_payload)

    def get_configuration(self, config_type: str, config_id: str) -> Mapping[str, Any]:
        return self._configurator_service.get_configuration(config_type, config_id)

    def update_configuration(self, config_type: str, config_id: str, config_payload: Mapping[str, Any]) -> None:
        self._configurator_service.update_configuration(config_type, config_id, config_payload)

    def delete_configuration(self, config_type: str, config_id: str) -> None:
        self._configurator_service.delete_configuration(config_type, config_id)

    def list_configuration_ids(self, config_type: str) -> list[str]:
        return self._configurator_service.list_configuration_ids(config_type)

    def configure_dispatch_failure_policy(self, policy_payload: Mapping[str, Any]) -> None:
        self.register_policy("dispatch.failure_policy", policy_payload)

    def configure_signal_qos_profile(self, policy_payload: Mapping[str, Any]) -> None:
        self.register_policy("signal.qos_profile", policy_payload)

    def configure_mandatory_label_schema(self, policy_payload: Mapping[str, Any]) -> None:
        self.register_policy("signal.mandatory_label_schema", policy_payload)

    def configure_slot_lifecycle_policy(self, policy_payload: Mapping[str, Any]) -> None:
        self._log_container_module.configure_slot_lifecycle_policy(policy_payload)
        self.register_policy("slot.lifecycle_policy", policy_payload)

    def configure_level_container_policy(self, policy_payload: Mapping[str, Any]) -> None:
        payload = self._copy_mapping(policy_payload, "policy_payload")
        strategy = str(payload.get("partition_strategy", self._level_containers.partition_strategy))
        max_records = int(payload.get("max_records_per_partition", self._level_containers.max_records_per_partition))
        self._level_containers.configure(
            partition_strategy=strategy,
            max_records_per_partition=max_records,
        )
        self._log_container_module.configure_level_container_policy(payload)
        self.register_policy("container.level_policy", payload)

    def configure_resolver_pipeline_policy(self, policy_payload: Mapping[str, Any]) -> None:
        self.register_policy("resolver.pipeline_policy", policy_payload)

    def configure_previewer_profile(self, profile_payload: Mapping[str, Any]) -> None:
        payload = self._copy_mapping(profile_payload, "profile_payload")
        console_mode = payload.get("console_mode")
        if isinstance(console_mode, str):
            self._console_previewer.set_mode(console_mode)
        web_mode = payload.get("web_mode")
        if isinstance(web_mode, str):
            self._web_previewer.set_mode(web_mode)
        if self._preview_integration_adapter is not None:
            self._preview_integration_adapter.configure_profile(payload)
        self.approve_runtime_profile("previewer.profile", payload)

    def configure_loglevel_api_policy(self, policy_payload: Mapping[str, Any]) -> None:
        self.register_policy("api.log_level_policy", policy_payload)

    def bind_previewer_adapter(self, adapter: PreviewerIntegrationPort) -> None:
        if not isinstance(adapter, PreviewerIntegrationPort):
            raise TypeError("adapter must implement PreviewerIntegrationPort")
        with self._lock:
            self._preview_integration_adapter = adapter
            self._append_audit_event_locked(
                action="bind_previewer_adapter",
                payload={"adapter_type": type(adapter).__name__},
            )
            self._persist_state_locked()


    def apply_configuration(self, config_type: str, config_id: str) -> Mapping[str, Any]:
        return self._configurator_service.apply_configuration(config_type, config_id)


    def activate_content_schema(self, schema_id: str) -> None:
        key = self._validate_identifier(schema_id, "schema_id")
        with self._lock:
            if key not in self._schema_registry:
                raise KeyError(f"schema_id is not registered: {key}")
            self._active_content_schema_id = key
            self._append_audit_event_locked(
                action="activate_content_schema",
                payload={"schema_id": key},
            )
            self._persist_state_locked()

    def bind_adapter(self, adapter_key: str) -> None:
        key = self._validate_identifier(adapter_key, "adapter_key")
        self._adapter_registry.resolve(key)
        with self._lock:
            self._active_adapter_key = key
            self._append_audit_event_locked(
                action="bind_adapter",
                payload={"adapter_key": key},
            )
            self._persist_state_locked()

    def bind_container_assignment(
        self,
        *,
        container_binding_id: str,
        container_backend_profile_id: str,
        container_lease_id: str | None = None,
    ) -> Mapping[str, Any]:
        binding_id = self._validate_identifier(container_binding_id, "container_binding_id")
        backend_profile_id = self._validate_identifier(container_backend_profile_id, "container_backend_profile_id")

        lease_id = container_lease_id
        if lease_id is None:
            lease = self._resource_management_client.request_container_lease(
                logger_instance_id="LOGSYS.default",
                container_binding_id=binding_id,
                container_backend_profile_id=backend_profile_id,
            )
            lease_id = str(lease.get("container_lease_id", "")).strip()
        lease_key = self._validate_identifier(lease_id, "container_lease_id")

        if not self._resource_management_client.validate_container_lease(lease_key):
            raise RuntimeError(f"invalid or expired container lease: {lease_key}")

        with self._lock:
            self._container_binding_id = binding_id
            self._container_backend_profile_id = backend_profile_id
            self._container_lease_id = lease_key
            self._append_audit_event_locked(
                action="bind_container_assignment",
                payload={
                    "container_binding_id": binding_id,
                    "container_backend_profile_id": backend_profile_id,
                    "container_lease_id": lease_key,
                },
            )
            self._persist_state_locked()
        return self.get_container_assignment_status()

    def unbind_container_assignment(self) -> None:
        with self._lock:
            lease_id = self._container_lease_id
            self._container_lease_id = None
            self._append_audit_event_locked(
                action="unbind_container_assignment",
                payload={"container_binding_id": self._container_binding_id},
            )
            self._persist_state_locked()
        if lease_id:
            self._resource_management_client.release_container_lease(lease_id)

    def validate_container_assignment(self) -> bool:
        with self._lock:
            lease_id = self._container_lease_id
        if lease_id is None:
            return False
        return self._resource_management_client.validate_container_lease(lease_id)

    def get_container_assignment_status(self) -> Mapping[str, Any]:
        with self._lock:
            lease_id = self._container_lease_id
            binding_id = self._container_binding_id
            backend_profile_id = self._container_backend_profile_id
        lease_valid = False
        lease_payload: Mapping[str, Any] | None = None
        if lease_id is not None:
            lease_valid = self._resource_management_client.validate_container_lease(lease_id)
            if lease_valid:
                lease_payload = self._resource_management_client.get_container_lease(lease_id)
        return {
            "container_binding_id": binding_id,
            "container_backend_profile_id": backend_profile_id,
            "container_lease_id": lease_id,
            "container_lease_valid": lease_valid,
            "container_lease": dict(lease_payload or {}),
        }

    def bind_execution_assignment(
        self,
        *,
        execution_binding_id: str,
        required_execution_profile_id: str,
        execution_lease_id: str | None = None,
        queue_policy_id: str | None = None,
        thread_safety_mode: str | None = None,
    ) -> Mapping[str, Any]:
        binding_id = self._validate_identifier(execution_binding_id, "execution_binding_id")
        profile_id = self._validate_identifier(required_execution_profile_id, "required_execution_profile_id")

        profile_payload = self._resource_management_client.get_execution_profile(profile_id)
        profile_thread_mode = str(profile_payload.get("thread_safety_mode", "")).strip()
        if profile_thread_mode not in ALLOWED_THREAD_SAFETY_MODES:
            raise RuntimeError(f"unsupported thread_safety_mode in execution profile: {profile_thread_mode}")

        resolved_thread_mode = profile_thread_mode
        if thread_safety_mode is not None:
            requested_mode = self._validate_identifier(thread_safety_mode, "thread_safety_mode")
            if requested_mode != profile_thread_mode:
                raise RuntimeError(
                    "thread_safety_mode override must match execution profile thread_safety_mode"
                )
            resolved_thread_mode = requested_mode

        resolved_queue_policy_id = self._validate_identifier(
            queue_policy_id or f"queue.policy.{profile_id}",
            "queue_policy_id",
        )

        lease_id = execution_lease_id
        if lease_id is None:
            lease = self._resource_management_client.request_execution_lease(
                logger_instance_id="LOGSYS.default",
                execution_binding_id=binding_id,
                required_execution_profile_id=profile_id,
            )
            lease_id = str(lease.get("execution_lease_id", "")).strip()
        lease_key = self._validate_identifier(lease_id, "execution_lease_id")
        if not self._resource_management_client.validate_execution_lease(lease_key):
            raise RuntimeError(f"invalid or expired execution lease: {lease_key}")

        with self._lock:
            self._execution_binding_id = binding_id
            self._required_execution_profile_id = profile_id
            self._execution_lease_id = lease_key
            self._queue_policy_id = resolved_queue_policy_id
            self._thread_safety_mode = resolved_thread_mode
            self._append_audit_event_locked(
                action="bind_execution_assignment",
                payload={
                    "execution_binding_id": binding_id,
                    "required_execution_profile_id": profile_id,
                    "execution_lease_id": lease_key,
                    "queue_policy_id": resolved_queue_policy_id,
                    "thread_safety_mode": resolved_thread_mode,
                },
            )
            self._persist_state_locked()
        return self.get_execution_assignment_status()

    def unbind_execution_assignment(self) -> None:
        with self._lock:
            lease_id = self._execution_lease_id
            self._execution_lease_id = None
            self._append_audit_event_locked(
                action="unbind_execution_assignment",
                payload={"execution_binding_id": self._execution_binding_id},
            )
            self._persist_state_locked()
        if lease_id:
            self._resource_management_client.release_execution_lease(lease_id)

    def validate_execution_assignment(self) -> bool:
        with self._lock:
            lease_id = self._execution_lease_id
            profile_id = self._required_execution_profile_id
        if lease_id is None:
            return False
        if not self._resource_management_client.validate_execution_lease(lease_id):
            return False
        try:
            profile_payload = self._resource_management_client.get_execution_profile(profile_id)
        except KeyError:
            return False
        thread_mode = str(profile_payload.get("thread_safety_mode", "")).strip()
        return thread_mode in ALLOWED_THREAD_SAFETY_MODES

    def get_execution_assignment_status(self) -> Mapping[str, Any]:
        with self._lock:
            lease_id = self._execution_lease_id
            binding_id = self._execution_binding_id
            profile_id = self._required_execution_profile_id
            queue_policy_id = self._queue_policy_id
            thread_safety_mode = self._thread_safety_mode
        lease_valid = False
        lease_payload: Mapping[str, Any] | None = None
        if lease_id is not None:
            lease_valid = self._resource_management_client.validate_execution_lease(lease_id)
            if lease_valid:
                lease_payload = self._resource_management_client.get_execution_lease(lease_id)
        try:
            profile_payload = self._resource_management_client.get_execution_profile(profile_id)
        except KeyError:
            profile_payload = {}
        return {
            "execution_binding_id": binding_id,
            "required_execution_profile_id": profile_id,
            "execution_lease_id": lease_id,
            "execution_lease_valid": lease_valid,
            "execution_lease": dict(lease_payload or {}),
            "queue_policy_id": queue_policy_id,
            "thread_safety_mode": thread_safety_mode,
            "execution_profile": dict(profile_payload),
        }

    def list_available_adapters(self) -> list[str]:
        return self._adapter_registry.list_keys()

    def dispatch_round(self, round_id: str) -> None:
        import time
        start_time = time.time()

        current_round_id = self._validate_identifier(round_id, "round_id")
        self._ensure_dispatch_assignment_or_fail()
        batch, dropped_count = self._drain_pending_for_dispatch()
        with self._lock:
            if len(batch) == 0:
                self._last_round_id = current_round_id
                self._total_evicted += dropped_count
                return
            active_adapter_key = self._active_adapter_key
            execution_lease_id = self._execution_lease_id
            required_execution_profile_id = self._required_execution_profile_id
            fallback_allowed = self._allow_unbound_dispatch_fallback
        self._dispatcher_resolver_pipeline.resolve_dispatch_candidate(
            round_id=current_round_id,
            pending_count=len(batch),
        )
        self._dispatcher_resolver_pipeline.resolve_dispatch_receiver_binding(adapter_key=active_adapter_key)
        adapter = self._adapter_registry.resolve(active_adapter_key)
        dispatch_tasks: list[Callable[[], Mapping[str, Any]]] = []
        for record in batch:
            projection = record.to_projection()
            projection["round_id"] = current_round_id

            def make_task(payload: Mapping[str, Any]) -> Callable[[], Mapping[str, Any]]:
                def task() -> Mapping[str, Any]:
                    adapter.emit_signal(signal_name="logging", payload=payload)
                    return payload

                return task

            dispatch_tasks.append(make_task(projection))

        try:
            self._execute_dispatch_tasks(
                tasks=dispatch_tasks,
                execution_lease_id=execution_lease_id,
                required_execution_profile_id=required_execution_profile_id,
                allow_unbound_fallback=fallback_allowed,
            )
        except Exception as exc:  # noqa: BLE001
            self._log_container_module.requeue_pending_front(batch)
            with self._lock:
                self._dispatch_failures += 1

            # Record dispatch error metrics
            self._metrics_registry.counter(
                name="logs_dispatch_errors_total",
                description="Total number of dispatch failures",
                unit="errors",
                labels={"service": "logging_service", "adapter": active_adapter_key},
                initial_value=1
            )

            raise RuntimeError(f"dispatch_round failed for adapter {active_adapter_key}") from exc

        dispatched_batch: list[LogRecord] = []
        for record in batch:
            dispatched_batch.append(
                LogRecord(
                    record_id=record.record_id,
                    payload=dict(record.payload),
                    created_at_utc=record.created_at_utc,
                    dispatched_at_utc=utc_now_iso(),
                    adapter_key=active_adapter_key,
                )
            )

        evicted_count = self._log_container_module.commit_dispatched(dispatched_batch)
        listener_failures = self._log_container_module.notify_listeners(dispatched_batch)
        with self._lock:
            self._total_dispatched += len(dispatched_batch)
            self._total_evicted += evicted_count + dropped_count
            self._listener_failures += listener_failures
            self._last_round_id = current_round_id
            self._persist_state_locked()

        # Record dispatch metrics
        self._metrics_registry.counter(
            name="logs_dispatched_total",
            description="Total number of logs successfully dispatched",
            unit="logs",
            labels={"service": "logging_service"},
            initial_value=len(dispatched_batch)
        )

        # Update queue depth gauge
        current_queue_depth = self._log_container_module.pending_count()
        self._metrics_registry.gauge_set(
            name="queue_depth",
            value=current_queue_depth,
            description="Current number of logs pending dispatch",
            unit="logs",
            labels={"service": "logging_service"}
        )

        # Record dispatch latency histogram
        dispatch_duration = time.time() - start_time
        self._metrics_registry.histogram_observe(
            name="dispatch_latency_seconds",
            value=dispatch_duration,
            description="Time taken to dispatch a batch of logs",
            unit="seconds",
            labels={"service": "logging_service", "adapter": active_adapter_key}
        )

    def enforce_safepoint(self, safepoint_id: str) -> None:
        current_safepoint_id = self._validate_identifier(safepoint_id, "safepoint_id")
        with self._lock:
            if self._log_container_module.pending_count() > 0:
                raise RuntimeError(
                    "cannot enforce safepoint while pending records exist; dispatch_round is required first"
                )
            self._last_safepoint_id = current_safepoint_id

    def collect_operational_evidence(self) -> Mapping[str, Any]:
        container_status = self.get_container_assignment_status()
        execution_status = self.get_execution_assignment_status()
        with self._lock:
            return {
                "active_adapter_key": self._active_adapter_key,
                "active_content_schema_id": self._active_content_schema_id,
                "adapter_keys": self._adapter_registry.list_keys(),
                "totals": {
                    "emitted": self._total_emitted,
                    "dispatched": self._total_dispatched,
                    "evicted": self._total_evicted,
                    "dispatch_failures": self._dispatch_failures,
                    "listener_failures": self._listener_failures,
                },
                "queue_depth": self._log_container_module.pending_count(),
                "stored_count": self._log_container_module.stored_count(),
                "schema_count": len(self._schema_registry),
                "schema_ids": sorted(self._schema_registry.keys()),
                "protected_schema_ids": sorted(self._protected_schema_ids),
                "policy_count": len(self._policy_registry),
                "runtime_profile_count": len(self._runtime_profiles),
                "production_profile_count": len(self._production_profiles),
                "active_production_profile_id": self._active_production_profile_id,
                "last_round_id": self._last_round_id,
                "last_safepoint_id": self._last_safepoint_id,
                "level_container_partitions": dict(self._log_container_module.partition_sizes()),
                "retention": {
                    "max_records": self._max_records,
                    "max_record_age_seconds": self._max_record_age_seconds,
                },
                "audit_trail_size": len(self._audit_trail),
                "previewer_integration_bound": self._preview_integration_adapter is not None,
                "container_assignment": container_status,
                "execution_assignment": execution_status,
            }

    def submit_signal_or_request(
        self,
        payload: Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> str:
        payload_copy = self._copy_mapping(payload, "payload")
        context_copy = dict(context or {})
        if len(context_copy) > 0:
            payload_copy.setdefault("context", context_copy)
        selected_schema_id = str(
            context_copy.get("schema_id") or payload_copy.get("schema_id") or self._active_content_schema_id
        )
        schema_payload = self._resolve_schema(selected_schema_id)
        self._validate_payload_against_schema(payload_copy, schema_payload, selected_schema_id)
        record_id = f"logging-{uuid4()}"
        record = LogRecord(record_id=record_id, payload=payload_copy)
        self._log_container_module.enqueue_pending(record, context=context_copy)
        with self._lock:
            self._total_emitted += 1
            self._persist_state_locked()

        # Record metrics
        self._metrics_registry.counter(
            name="logs_emitted_total",
            description="Total number of logs emitted",
            unit="logs",
            labels={"service": "logging_service"},
            initial_value=1
        )

        return record_id

    def emit(self, payload: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> str:
        return self.submit_signal_or_request(payload=payload, context=context)

    def traced_emit(self, payload: Mapping[str, Any], context: Mapping[str, Any] | None = None) -> str:
        """
        Emit a log entry with automatic tracing.

        This method wraps the emit operation in a span, providing distributed tracing
        capabilities for logging operations.

        Args:
            payload: Log payload with level, message, attributes, context
            context: Optional additional context

        Returns:
            Record ID of the emitted log
        """
        # Extract span context from HTTP headers if available
        span_context = None
        if context and "headers" in context:
            span_context = self._tracing_context.extract_context(context["headers"])

        # Create a span for the logging operation
        with self._tracing_context.span(
            name=f"log.{payload.get('level', 'UNKNOWN').lower()}",
            kind=ESpanKind.INTERNAL,
            attributes={
                "log.level": payload.get("level", "UNKNOWN"),
                "log.message": payload.get("message", "")[:100],  # Truncate long messages
            },
            parent_context=span_context
        ) as span:
            # Inject current span context into outgoing headers if present
            if context and "headers" in context:
                outgoing_headers = self._tracing_context.inject_context()
                context["headers"].update(outgoing_headers)

            # Perform the actual emit operation
            record_id = self.emit(payload, context)

            # Add additional span attributes
            span.add_attribute("log.record_id", record_id)

            return record_id

    def query_projection(
        self,
        *,
        filters: Mapping[str, Any] | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> list[Mapping[str, Any]]:
        scope = self._readonly_resolver_pipeline.resolve_query_projection_scope(
            filters=filters,
            page=page,
            page_size=page_size,
        )
        return self._log_container_module.query_projection(
            filters=dict(scope["filters"]),
            page=int(scope["page"]),
            page_size=int(scope["page_size"]),
        )

    def query(self, filters: Mapping[str, Any] | None = None) -> list[Mapping[str, Any]]:
        return self.query_projection(filters=filters, page=1, page_size=100)

    def subscribe_notifications(
        self,
        listener_id: str,
        listener: Callable[[Mapping[str, Any]], None],
    ) -> None:
        self._log_container_module.subscribe_listener(listener_id, listener)

    def read_only_inspection(self) -> Mapping[str, Any]:
        evidence = self.collect_operational_evidence()
        with self._lock:
            evidence = dict(evidence)
            evidence["schemas"] = sorted(self._schema_registry.keys())
            evidence["policies"] = sorted(self._policy_registry.keys())
            evidence["runtime_profiles"] = sorted(self._runtime_profiles.keys())
            evidence["production_profiles"] = sorted(self._production_profiles.keys())
        return evidence

    def get_metrics_prometheus(self) -> str:
        """
        Get all metrics in Prometheus text format.

        Returns:
            String containing all metrics in Prometheus exposition format
        """
        from ..observability.metrics.exporters.prometheus import PrometheusExporter
        exporter = PrometheusExporter(self._metrics_registry)
        return exporter.export()

    def get_tracing_info(self) -> Mapping[str, Any]:
        """
        Get current tracing information.

        Returns:
            Dictionary containing current span information and tracing status
        """
        current_span = self._tracing_context.current_span
        return {
            "tracing_enabled": self._tracing_context._config.enabled,
            "current_span": {
                "active": current_span is not None,
                "name": current_span.name if current_span else None,
                "trace_id": current_span.context.trace_id if current_span else None,
                "span_id": current_span.context.span_id if current_span else None,
                "kind": current_span.kind.value if current_span else None,
            } if current_span else None,
            "sampling_rate": self._tracing_context._config.sampling_rate,
            "service_name": self._tracing_context._config.service_name,
        }

    def log(
        self,
        level: str,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        return self._log_level_handler.emit(
            level=level,
            message=message,
            attributes=attributes,
            context=context,
            emit_callable=self.emit,
            level_containers=self._level_containers,
            writer_resolver=self._writer_resolver_pipeline,
        )

    def log_debug(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        return self._log_debug_api.submit(
            service=self,
            message=message,
            attributes=attributes,
            context=context,
        )

    def log_info(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        return self._log_info_api.submit(
            service=self,
            message=message,
            attributes=attributes,
            context=context,
        )

    def log_warn(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        return self._log_warn_api.submit(
            service=self,
            message=message,
            attributes=attributes,
            context=context,
        )

    def log_error(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        return self._log_error_api.submit(
            service=self,
            message=message,
            attributes=attributes,
            context=context,
        )

    def log_fatal(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        return self._log_fatal_api.submit(
            service=self,
            message=message,
            attributes=attributes,
            context=context,
        )

    def log_trace(
        self,
        message: str,
        attributes: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> str:
        return self._log_trace_api.submit(
            service=self,
            message=message,
            attributes=attributes,
            context=context,
        )

    def preview_console(self, *, mode: str | None = None, limit: int = 50) -> str:
        rows = [record.to_projection() for record in self._log_container_module.list_dispatched_records()]
        rows.extend(record.to_projection() for record in self._log_container_module.list_pending_records())
        rows = rows[-max(1, limit) :]
        with self._lock:
            preview_adapter = self._preview_integration_adapter
        if preview_adapter is not None:
            return preview_adapter.render_console(rows, mode=mode, limit=limit)
        if mode is not None:
            self._console_previewer.set_mode(mode)
        return self._console_previewer.preview(rows)

    def preview_web(self, *, mode: str | None = None, limit: int = 50) -> Mapping[str, Any]:
        rows = [record.to_projection() for record in self._log_container_module.list_dispatched_records()]
        rows.extend(record.to_projection() for record in self._log_container_module.list_pending_records())
        rows = rows[-max(1, limit) :]
        with self._lock:
            preview_adapter = self._preview_integration_adapter
        if preview_adapter is not None:
            return preview_adapter.render_web(rows, mode=mode, limit=limit)
        if mode is not None:
            self._web_previewer.set_mode(mode)
        return self._web_previewer.preview_payload(rows)

    def _ensure_default_container_assignment(self) -> None:
        if self._container_lease_id is not None and self._resource_management_client.validate_container_lease(
            self._container_lease_id
        ):
            return
        lease = self._resource_management_client.request_container_lease(
            logger_instance_id="LOGSYS.default",
            container_binding_id=self._container_binding_id,
            container_backend_profile_id=self._container_backend_profile_id,
        )
        lease_id = str(lease.get("container_lease_id", "")).strip()
        if lease_id == "":
            raise RuntimeError("resource management client returned empty container_lease_id")
        self._container_lease_id = lease_id

    def _ensure_default_execution_assignment(self) -> None:
        if self._execution_lease_id is not None and self._resource_management_client.validate_execution_lease(
            self._execution_lease_id
        ):
            return
        profile_id = self._required_execution_profile_id
        try:
            profile_payload = self._resource_management_client.get_execution_profile(profile_id)
        except KeyError:
            profile_id = "exec.logging.local.default"
            profile_payload = self._resource_management_client.get_execution_profile(profile_id)
            self._required_execution_profile_id = profile_id
        thread_mode = str(profile_payload.get("thread_safety_mode", "")).strip()
        if thread_mode not in ALLOWED_THREAD_SAFETY_MODES:
            raise RuntimeError(f"unsupported thread_safety_mode in execution profile: {thread_mode}")
        lease = self._resource_management_client.request_execution_lease(
            logger_instance_id="LOGSYS.default",
            execution_binding_id=self._execution_binding_id,
            required_execution_profile_id=profile_id,
        )
        lease_id = str(lease.get("execution_lease_id", "")).strip()
        if lease_id == "":
            raise RuntimeError("resource management client returned empty execution_lease_id")
        self._execution_lease_id = lease_id
        self._thread_safety_mode = thread_mode
        self._queue_policy_id = f"queue.policy.{self._required_execution_profile_id}"

    def _ensure_dispatch_assignment_or_fail(self) -> None:
        with self._lock:
            container_lease_id = self._container_lease_id
            execution_lease_id = self._execution_lease_id
            required_execution_profile_id = self._required_execution_profile_id
            fallback_allowed = self._allow_unbound_dispatch_fallback
        if container_lease_id is None:
            if fallback_allowed:
                return
            raise RuntimeError("container assignment is required before dispatch")
        if execution_lease_id is None:
            if fallback_allowed:
                return
            raise RuntimeError("execution assignment is required before dispatch")

        if not self._resource_management_client.validate_container_lease(container_lease_id):
            if fallback_allowed:
                return
            raise RuntimeError(f"container lease is invalid or expired: {container_lease_id}")

        if not self._resource_management_client.validate_execution_lease(execution_lease_id):
            if fallback_allowed:
                return
            raise RuntimeError(f"execution lease is invalid or expired: {execution_lease_id}")

        profile_payload = self._resource_management_client.get_execution_profile(required_execution_profile_id)
        thread_mode = str(profile_payload.get("thread_safety_mode", "")).strip()
        if thread_mode not in ALLOWED_THREAD_SAFETY_MODES:
            raise RuntimeError(f"unsupported thread_safety_mode in execution profile: {thread_mode}")
        with self._lock:
            self._thread_safety_mode = thread_mode

    def _drain_pending_for_dispatch(self) -> tuple[list[LogRecord], int]:
        batch = self._log_container_module.drain_pending()
        if len(batch) == 0:
            return batch, 0

        with self._lock:
            profile_id = self._required_execution_profile_id
        profile_payload = self._resource_management_client.get_execution_profile(profile_id)
        queue_bounds = profile_payload.get("queue_bounds")
        max_items = queue_bounds.get("max_items") if isinstance(queue_bounds, Mapping) else None
        if not isinstance(max_items, int) or max_items <= 0:
            self._log_container_module.requeue_pending_front(batch)
            raise RuntimeError("execution profile queue_bounds.max_items must be a positive integer")
        if len(batch) <= max_items:
            return batch, 0

        backpressure_policy = profile_payload.get("backpressure_policy")
        action = backpressure_policy.get("action") if isinstance(backpressure_policy, Mapping) else None
        if not isinstance(action, str) or action not in ALLOWED_BACKPRESSURE_ACTIONS:
            self._log_container_module.requeue_pending_front(batch)
            raise RuntimeError("execution profile backpressure action is invalid or unsupported")

        overflow = len(batch) - max_items
        if action == "block":
            self._log_container_module.requeue_pending_front(batch)
            raise RuntimeError("dispatch blocked by execution backpressure policy")
        if action == "retry_with_jitter":
            self._log_container_module.requeue_pending_front(batch)
            raise RuntimeError("dispatch deferred by retry_with_jitter backpressure policy")
        if action == "drop_oldest":
            return batch[-max_items:], overflow
        if action == "drop_newest":
            return batch[:max_items], overflow
        if action == "sample":
            return self._sample_records(batch, max_items), overflow
        self._log_container_module.requeue_pending_front(batch)
        raise RuntimeError(f"unsupported backpressure action: {action}")

    def _execute_dispatch_tasks(
        self,
        *,
        tasks: list[Callable[[], Mapping[str, Any]]],
        execution_lease_id: str | None,
        required_execution_profile_id: str,
        allow_unbound_fallback: bool,
    ) -> None:
        if len(tasks) == 0:
            return
        if execution_lease_id is None:
            if not allow_unbound_fallback:
                raise RuntimeError("execution assignment is required before dispatch task execution")
            for task in tasks:
                task()
            return
        self._resource_management_client.execute_dispatch_tasks(
            execution_lease_id=execution_lease_id,
            required_execution_profile_id=required_execution_profile_id,
            tasks=tasks,
        )

    @staticmethod
    def _sample_records(records: list[LogRecord], max_items: int) -> list[LogRecord]:
        if max_items <= 0:
            return []
        if len(records) <= max_items:
            return list(records)
        step = len(records) / max_items
        sampled: list[LogRecord] = []
        for idx in range(max_items):
            sampled.append(records[min(int(idx * step), len(records) - 1)])
        return sampled

    def _append_audit_event_locked(self, *, action: str, payload: Mapping[str, Any]) -> None:
        self._audit_trail.append(
            {
                "event_id": f"audit-{uuid4()}",
                "created_at_utc": utc_now_iso(),
                "action": action,
                "payload": dict(payload),
            }
        )

    def _apply_retention_locked(self) -> None:
        if self._max_record_age_seconds is not None:
            cutoff = datetime.now(timezone.utc).timestamp() - self._max_record_age_seconds
            while len(self._records) > 0:
                first = self._records[0]
                if self._parse_utc(first.created_at_utc).timestamp() >= cutoff:
                    break
                self._records.popleft()
                self._total_evicted += 1
        while len(self._records) > self._max_records:
            self._records.popleft()
            self._total_evicted += 1

    def _resolve_schema(self, schema_id: str) -> Mapping[str, Any]:
        key = self._validate_identifier(schema_id, "schema_id")
        with self._lock:
            schema_payload = self._schema_registry.get(key)
        if schema_payload is None:
            raise KeyError(f"schema_id is not registered: {key}")
        return schema_payload

    @classmethod
    def _validate_schema_payload(cls, schema_payload: Mapping[str, Any]) -> None:
        required_keys = schema_payload.get("required_keys")
        properties = schema_payload.get("properties")
        if not isinstance(required_keys, list) or not all(isinstance(item, str) and item.strip() for item in required_keys):
            raise ValueError("schema_payload.required_keys must be a non-empty list of field names")
        if not isinstance(properties, Mapping):
            raise ValueError("schema_payload.properties must be a mapping")
        for required_key in required_keys:
            if required_key not in properties:
                raise ValueError(f"schema required key has no property definition: {required_key}")
        for field_name, field_rules in properties.items():
            if not isinstance(field_rules, Mapping):
                raise ValueError(f"schema property rules must be mapping for field: {field_name}")
            field_type = field_rules.get("type")
            if field_type is None:
                raise ValueError(f"schema property type is required for field: {field_name}")
            if field_type not in {"string", "object", "number", "integer", "boolean", "array"}:
                raise ValueError(f"unsupported schema property type '{field_type}' for field: {field_name}")

    @classmethod
    def _validate_payload_against_schema(
        cls,
        payload: Mapping[str, Any],
        schema_payload: Mapping[str, Any],
        schema_id: str,
    ) -> None:
        required_keys = list(schema_payload.get("required_keys", []))
        properties = dict(schema_payload.get("properties", {}))
        allow_additional = bool(schema_payload.get("allow_additional_properties", True))

        for required_key in required_keys:
            if required_key not in payload:
                raise ValueError(f"payload violates schema '{schema_id}': missing required key '{required_key}'")

        if not allow_additional:
            unknown = [key for key in payload.keys() if key not in properties]
            if unknown:
                raise ValueError(
                    f"payload violates schema '{schema_id}': additional properties not allowed: {', '.join(unknown)}"
                )

        for field_name, field_rules in properties.items():
            if field_name not in payload:
                continue
            value = payload[field_name]
            expected_type = str(field_rules.get("type"))
            if not cls._value_matches_type(value, expected_type):
                raise ValueError(
                    f"payload violates schema '{schema_id}': field '{field_name}' must be of type '{expected_type}'"
                )
            allowed_values = field_rules.get("enum")
            if isinstance(allowed_values, list) and value not in allowed_values:
                raise ValueError(
                    f"payload violates schema '{schema_id}': field '{field_name}' value '{value}' not in enum"
                )
            min_length = field_rules.get("min_length")
            if isinstance(min_length, int) and isinstance(value, str) and len(value.strip()) < min_length:
                raise ValueError(
                    f"payload violates schema '{schema_id}': field '{field_name}' min_length={min_length}"
                )

    @staticmethod
    def _value_matches_type(value: Any, expected_type: str) -> bool:
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "object":
            return isinstance(value, Mapping)
        if expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "array":
            return isinstance(value, list)
        return False

    def _load_persisted_state(self) -> None:
        payload = self._state_store.load_state()
        if not isinstance(payload, Mapping) or len(payload) == 0:
            return

        schema_registry = payload.get("schema_registry")
        if isinstance(schema_registry, Mapping):
            for schema_id, schema_payload in schema_registry.items():
                if not isinstance(schema_id, str) or not isinstance(schema_payload, Mapping):
                    continue
                self._validate_schema_payload(schema_payload)
                self._schema_registry[schema_id] = dict(schema_payload)

        policy_registry = payload.get("policy_registry")
        if isinstance(policy_registry, Mapping):
            self._policy_registry = {
                str(key): dict(value)
                for key, value in policy_registry.items()
                if isinstance(key, str) and isinstance(value, Mapping)
            }

        runtime_profiles = payload.get("runtime_profiles")
        if isinstance(runtime_profiles, Mapping):
            self._runtime_profiles = {
                str(key): dict(value)
                for key, value in runtime_profiles.items()
                if isinstance(key, str) and isinstance(value, Mapping)
            }

        production_profiles = payload.get("production_profiles")
        if isinstance(production_profiles, Mapping):
            self._production_profiles = {
                str(key): dict(value)
                for key, value in production_profiles.items()
                if isinstance(key, str) and isinstance(value, Mapping)
            }
            self._production_profile_service = ProductionProfileCatalogService(
                self._production_profiles,
                provider_lookup=self.get_provider_catalog_entry,
                connection_lookup=self.get_connection_catalog_entry,
                persistence_lookup=self.get_persistence_catalog_entry,
            )
            self._production_profile_service.seed_defaults_if_empty()

        provider_catalog_state = payload.get("provider_catalog_state")
        if isinstance(provider_catalog_state, Mapping):
            self._provider_catalog_service.import_state(provider_catalog_state)

        active_production_profile_id = payload.get("active_production_profile_id")
        if isinstance(active_production_profile_id, str) and active_production_profile_id.strip() != "":
            self._active_production_profile_id = active_production_profile_id.strip()

        active_schema = payload.get("active_content_schema_id")
        if isinstance(active_schema, str) and active_schema in self._schema_registry:
            self._active_content_schema_id = active_schema

        active_adapter = payload.get("active_adapter_key")
        if isinstance(active_adapter, str) and self._adapter_registry.has(active_adapter):
            self._active_adapter_key = active_adapter

        retention = payload.get("retention")
        if isinstance(retention, Mapping):
            max_records = retention.get("max_records")
            max_age = retention.get("max_record_age_seconds")
            if isinstance(max_records, int) and max_records > 0:
                self._max_records = max_records
            if max_age is None:
                self._max_record_age_seconds = None
            elif isinstance(max_age, int) and max_age > 0:
                self._max_record_age_seconds = max_age
            self._log_container_module.configure_retention(
                max_records=self._max_records,
                max_record_age_seconds=self._max_record_age_seconds,
            )

        log_container_state = payload.get("log_container_state")
        if isinstance(log_container_state, Mapping):
            self._log_container_module.import_state(log_container_state)
        else:
            # Backward compatibility with pre-module persisted shape.
            legacy_state = {
                "records": payload.get("records"),
                "pending_records": payload.get("pending_records"),
                "retention": payload.get("retention"),
            }
            self._log_container_module.import_state(legacy_state)

        container_assignment = payload.get("container_assignment")
        if isinstance(container_assignment, Mapping):
            binding_id = container_assignment.get("container_binding_id")
            backend_profile_id = container_assignment.get("container_backend_profile_id")
            lease_id = container_assignment.get("container_lease_id")
            if isinstance(binding_id, str) and binding_id.strip() != "":
                self._container_binding_id = binding_id.strip()
            if isinstance(backend_profile_id, str) and backend_profile_id.strip() != "":
                self._container_backend_profile_id = backend_profile_id.strip()
            if isinstance(lease_id, str) and lease_id.strip() != "":
                self._container_lease_id = lease_id.strip()

        execution_assignment = payload.get("execution_assignment")
        if isinstance(execution_assignment, Mapping):
            execution_binding_id = execution_assignment.get("execution_binding_id")
            execution_profile_id = execution_assignment.get("required_execution_profile_id")
            execution_lease_id = execution_assignment.get("execution_lease_id")
            queue_policy_id = execution_assignment.get("queue_policy_id")
            thread_safety_mode = execution_assignment.get("thread_safety_mode")
            if isinstance(execution_binding_id, str) and execution_binding_id.strip() != "":
                self._execution_binding_id = execution_binding_id.strip()
            if isinstance(execution_profile_id, str) and execution_profile_id.strip() != "":
                self._required_execution_profile_id = execution_profile_id.strip()
            if isinstance(execution_lease_id, str) and execution_lease_id.strip() != "":
                self._execution_lease_id = execution_lease_id.strip()
            if isinstance(queue_policy_id, str) and queue_policy_id.strip() != "":
                self._queue_policy_id = queue_policy_id.strip()
            if isinstance(thread_safety_mode, str) and thread_safety_mode.strip() != "":
                self._thread_safety_mode = thread_safety_mode.strip()

        fallback_policy = payload.get("allow_unbound_dispatch_fallback")
        if isinstance(fallback_policy, bool):
            self._allow_unbound_dispatch_fallback = fallback_policy

    def _persist_state_locked(self) -> None:
        log_container_state = self._log_container_module.export_state()
        self._state_store.save_state(
            {
                "schema_registry": {key: dict(value) for key, value in self._schema_registry.items()},
                "policy_registry": {key: dict(value) for key, value in self._policy_registry.items()},
                "runtime_profiles": {key: dict(value) for key, value in self._runtime_profiles.items()},
                "production_profiles": {key: dict(value) for key, value in self._production_profiles.items()},
                "provider_catalog_state": self._provider_catalog_service.export_state(),
                "active_content_schema_id": self._active_content_schema_id,
                "active_adapter_key": self._active_adapter_key,
                "active_production_profile_id": self._active_production_profile_id,
                "retention": {
                    "max_records": self._max_records,
                    "max_record_age_seconds": self._max_record_age_seconds,
                },
                "records": list(log_container_state.get("records", [])),
                "pending_records": list(log_container_state.get("pending_records", [])),
                "log_container_state": dict(log_container_state),
                "container_assignment": {
                    "container_binding_id": self._container_binding_id,
                    "container_backend_profile_id": self._container_backend_profile_id,
                    "container_lease_id": self._container_lease_id,
                },
                "execution_assignment": {
                    "execution_binding_id": self._execution_binding_id,
                    "required_execution_profile_id": self._required_execution_profile_id,
                    "execution_lease_id": self._execution_lease_id,
                    "queue_policy_id": self._queue_policy_id,
                    "thread_safety_mode": self._thread_safety_mode,
                },
                "allow_unbound_dispatch_fallback": self._allow_unbound_dispatch_fallback,
            }
        )

    @staticmethod
    def _parse_utc(value: str) -> datetime:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).astimezone(timezone.utc)

    @staticmethod
    def _validate_identifier(value: str, field_name: str) -> str:
        normalized = str(value).strip()
        if normalized == "":
            raise ValueError(f"{field_name} is required")
        return normalized

    @staticmethod
    def _copy_mapping(value: Mapping[str, Any], field_name: str) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise TypeError(f"{field_name} must be a mapping")
        return dict(value)

    @staticmethod
    def _serialize_record(record: LogRecord) -> Mapping[str, Any]:
        return {
            "record_id": record.record_id,
            "payload": dict(record.payload),
            "created_at_utc": record.created_at_utc,
            "dispatched_at_utc": record.dispatched_at_utc,
            "adapter_key": record.adapter_key,
        }

    @staticmethod
    def _parse_record_payload(value: Any) -> LogRecord | None:
        if not isinstance(value, Mapping):
            return None
        record_id = value.get("record_id")
        payload = value.get("payload")
        created_at_utc = value.get("created_at_utc")
        if not isinstance(record_id, str) or not isinstance(payload, Mapping):
            return None
        if not isinstance(created_at_utc, str):
            created_at_utc = utc_now_iso()
        dispatched_at_utc = value.get("dispatched_at_utc")
        if dispatched_at_utc is not None and not isinstance(dispatched_at_utc, str):
            dispatched_at_utc = None
        adapter_key = value.get("adapter_key")
        if adapter_key is not None and not isinstance(adapter_key, str):
            adapter_key = None
        return LogRecord(
            record_id=record_id,
            payload=dict(payload),
            created_at_utc=created_at_utc,
            dispatched_at_utc=dispatched_at_utc,
            adapter_key=adapter_key,
        )
