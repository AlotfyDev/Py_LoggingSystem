# 02 LoggingSystem Implementation Inventory SSOT

## Snapshot Metadata
- generated_at_utc: `2026-03-11T10:46:06Z`
- source_root: `D:/PythonTrader/NK_System/03.0020_LoggingSystem/03_DigitalTwin/logging_system`
- output_file: `D:/PythonTrader/NK_System/03.0020_LoggingSystem/00_Project_Management/02_LoggingSystem_Implementation_Inventory_SSOT.md`
- generated_by: `00_Project_Management/automation/generate_implementation_inventory_snapshot.py`
- total_python_files_scanned: `111`

## Regeneration Command
```powershell
python 03.0020_LoggingSystem/00_Project_Management/automation/generate_implementation_inventory_snapshot.py
```

## Package Boundary / Module Exports
1. `__init__.py`: constants: `__all__`
2. `adapters/__init__.py`: constants: `__all__`
3. `cli/__init__.py`: constants: `__all__`
4. `configurator/__init__.py`: constants: `__all__`
5. `configurator/dtos/__init__.py`: constants: `__all__`
6. `configurator/mappers/__init__.py`: constants: `__all__`
7. `configurator/validators/__init__.py`: constants: `__all__`
8. `containers/__init__.py`: constants: `__all__`
9. `handlers/__init__.py`: constants: `__all__`
10. `level_api/__init__.py`: constants: `__all__`
11. `log_container_module/__init__.py`: constants: `__all__`
12. `models/__init__.py`: constants: `__all__`
13. `ports/__init__.py`: constants: `__all__`
14. `previewers/__init__.py`: constants: `__all__`
15. `production_profiles/__init__.py`: constants: `__all__`
16. `production_profiles/catalog_entries/__init__.py`: constants: `__all__`
17. `production_profiles/dtos/__init__.py`: constants: `__all__`
18. `production_profiles/mappers/__init__.py`: constants: `__all__`
19. `production_profiles/validators/__init__.py`: constants: `__all__`
20. `provider_catalogs/__init__.py`: constants: `__all__`
21. `resolvers/__init__.py`: constants: `__all__`
22. `resource_management/__init__.py`: constants: `__all__`
23. `resource_management/adapters/__init__.py`: constants: `__all__`
24. `services/__init__.py`: constants: `__all__`
25. `specialization/__init__.py`: constants: `__all__`
26. `tests/__init__.py`: no top-level symbols

## Domain Models / Schema Catalog
1. `models/default_content_schema_catalog.py`: constants: `DEFAULT_CONTENT_SCHEMA_ID`, `AUDIT_CONTENT_SCHEMA_ID`, `ERROR_CONTENT_SCHEMA_ID`; functions: `build_default_content_schema_catalog`
2. `models/envelope.py`: constants: `TContent`, `TContext`, `TMeta`; classes: `LogEnvelope`
3. `models/record.py`: classes: `LogRecord`
4. `models/utc_now_iso.py`: functions: `utc_now_iso`

## Port Contracts (Administrative / Managerial / Consuming / State)
1. `ports/adapter_registry_port.py`: classes: `AdapterRegistryPort`
2. `ports/administrative_port.py`: classes: `AdministrativePort`
3. `ports/consuming_port.py`: classes: `ConsumingPort`
4. `ports/log_container_administrative_port.py`: classes: `LogContainerAdministrativePort`
5. `ports/log_container_consuming_port.py`: classes: `LogContainerConsumingPort`
6. `ports/log_container_managerial_port.py`: classes: `LogContainerManagerialPort`
7. `ports/log_container_provider_port.py`: classes: `LogContainerProviderPort`
8. `ports/managerial_port.py`: classes: `ManagerialPort`
9. `ports/observability_viewer_provider_port.py`: classes: `ObservabilityViewerProviderPort`
10. `ports/open_telemetry_adapter_port.py`: classes: `OpenTelemetryAdapterPort`
11. `ports/previewer_integration_port.py`: classes: `PreviewerIntegrationPort`
12. `ports/resource_management_client_port.py`: classes: `ResourceManagementClientPort`
13. `ports/state_store_port.py`: classes: `StateStorePort`

## Adapters / Factories (Provider Integrations + Persistence)
1. `adapters/adapter_registry.py`: classes: `AdapterRegistry`
2. `adapters/default_registry_factory.py`: functions: `build_default_adapter_registry`
3. `adapters/default_state_store_factory.py`: constants: `DEFAULT_STATE_ENV_VAR`; functions: `build_default_state_store`
4. `adapters/file_state_store.py`: classes: `FileStateStore`
5. `adapters/no_op_adapter.py`: classes: `NoOpAdapter`
6. `adapters/observability_viewer_adapter.py`: classes: `ObservabilityViewerAdapter`
7. `adapters/open_telemetry_adapter.py`: classes: `OpenTelemetryAdapter`
8. `adapters/unavailable_open_telemetry_adapter.py`: classes: `UnavailableOpenTelemetryAdapter`

## Service Orchestration / Runtime Logic
1. `services/logging_service.py`: constants: `ALLOWED_THREAD_SAFETY_MODES`, `ALLOWED_BACKPRESSURE_ACTIONS`; classes: `LoggingService`

## CLI Control Plane
1. `cli/json_payload_parser.py`: functions: `parse_json_object`
2. `cli/parser.py`: functions: `_add_log_payload_args`, `build_parser`
3. `cli/run_cli.py`: functions: `run_cli`

## Test Support + Behavioral/E2E Test Components
1. `tests/support.py`: classes: `InMemoryStateStore`
2. `tests/test_adapters_behavior.py`: classes: `AdapterRegistryBehaviorTests`, `AdapterBehaviorTests`
3. `tests/test_cli_behavior.py`: classes: `CliBehaviorTests`
4. `tests/test_container_assignment_behavior.py`: classes: `ContainerAssignmentBehaviorTests`
5. `tests/test_end_to_end_behavior.py`: classes: `CollectingAdapter`, `FailingAdapter`, `EndToEndBehaviorTests`
6. `tests/test_logging_service.py`: classes: `LoggingServiceTests`, `AdapterRegistryTests`
7. `tests/test_models_behavior.py`: classes: `LogEnvelopeBehaviorTests`, `LogRecordBehaviorTests`
8. `tests/test_new_components_behavior.py`: classes: `NewComponentsBehaviorTests`
9. `tests/test_ports_contracts_behavior.py`: classes: `PortsContractBehaviorTests`
10. `tests/test_production_profiles_behavior.py`: classes: `ProductionProfilesBehaviorTests`
11. `tests/test_provider_catalogs_behavior.py`: classes: `ProviderCatalogsBehaviorTests`
12. `tests/test_specialization_import_policy.py`: classes: `SpecializationImportPolicyTests`
13. `tests/test_thread_pool_resource_management_behavior.py`: classes: `ThreadPoolResourceManagementBehaviorTests`
14. `tests/test_validator_gates_behavior.py`: classes: `ValidatorGatesBehaviorTests`
15. `tests/test_viewer_specialization_behavior.py`: constants: `_OVS_DIGITAL_TWIN`; classes: `FakeViewerProvider`, `ViewerSpecializationBehaviorTests`

## Other
1. `configurator/dtos/adapter_binding_dto.py`: classes: `AdapterBindingDTO`
2. `configurator/dtos/connection_catalog_entry_dto.py`: classes: `ConnectionCatalogEntryDTO`
3. `configurator/dtos/container_binding_dto.py`: classes: `ContainerBindingDTO`
4. `configurator/dtos/execution_binding_dto.py`: classes: `ExecutionBindingDTO`
5. `configurator/dtos/persistence_catalog_entry_dto.py`: classes: `PersistenceCatalogEntryDTO`
6. `configurator/dtos/policy_dto.py`: classes: `PolicyDTO`
7. `configurator/dtos/previewer_profile_dto.py`: classes: `PreviewerProfileDTO`
8. `configurator/dtos/production_profile_dto.py`: classes: `ProductionProfileDTO`
9. `configurator/dtos/provider_catalog_entry_dto.py`: classes: `ProviderCatalogEntryDTO`
10. `configurator/dtos/retention_dto.py`: classes: `RetentionDTO`
11. `configurator/dtos/schema_dto.py`: classes: `SchemaDTO`
12. `configurator/mappers/configuration_mapper.py`: functions: `schema_from_existing`, `policy_from_existing`, `retention_from_existing`, `previewer_profile_from_existing`, `adapter_binding_from_existing`, `container_binding_from_existing`, `execution_binding_from_existing`, `provider_catalog_entry_from_existing`, `connection_catalog_entry_from_existing`, `persistence_catalog_entry_from_existing`, `production_profile_from_existing`
13. `configurator/service.py`: classes: `ConfiguratorService`
14. `configurator/validators/configuration_validator.py`: constants: `SUPPORTED_CONFIGURATION_TYPES`; functions: `ensure_supported_config_type`, `ensure_identifier`, `ensure_payload_mapping`
15. `containers/level_containers.py`: classes: `LevelContainers`
16. `containers/slot_lifecycle.py`: constants: `CANONICAL_SLOT_STATES`; classes: `SlotLifecycle`
17. `handlers/log_level_handler.py`: classes: `LogLevelHandler`
18. `level_api/e_log_level.py`: classes: `ELogLevel`
19. `level_api/log_debug.py`: classes: `LogDebug`
20. `level_api/log_error.py`: classes: `LogError`
21. `level_api/log_fatal.py`: classes: `LogFatal`
22. `level_api/log_info.py`: classes: `LogInfo`
23. `level_api/log_trace.py`: classes: `LogTrace`
24. `level_api/log_warn.py`: classes: `LogWarn`
25. `log_container_module/service.py`: classes: `LogContainerModuleService`
26. `previewers/console_previewer.py`: classes: `ConsolePreviewer`
27. `previewers/web_previewer.py`: classes: `WebPreviewer`
28. `production_profiles/catalog_entries/defaults.py`: functions: `build_default_production_profiles`
29. `production_profiles/dtos/production_profile_dto.py`: classes: `ProductionProfileDTO`; functions: `_require_non_empty_str`
30. `production_profiles/mappers/production_profile_mapper.py`: functions: `to_runtime_payload`
31. `production_profiles/service.py`: classes: `ProductionProfileCatalogService`
32. `production_profiles/validators/production_profile_validator.py`: classes: `ProductionProfileValidator`
33. `provider_catalogs/default_entries.py`: functions: `build_default_provider_entries`, `build_default_connection_entries`, `build_default_persistence_entries`
34. `provider_catalogs/models.py`: classes: `ProviderCatalogEntry`, `ConnectionCatalogEntry`, `PersistenceCatalogEntry`; functions: `_require_non_empty_str`, `_require_non_empty_str_list`
35. `provider_catalogs/service.py`: classes: `ProviderCatalogService`
36. `resolvers/dispatcher_resolver_pipeline.py`: classes: `DispatcherResolverPipeline`
37. `resolvers/readonly_resolver_pipeline.py`: classes: `ReadOnlyResolverPipeline`
38. `resolvers/writer_resolver_pipeline.py`: classes: `WriterResolverPipeline`
39. `resource_management/adapters/in_memory_resource_management_client.py`: classes: `InMemoryResourceManagementClient`
40. `resource_management/adapters/thread_pool_resource_management_client.py`: classes: `ThreadPoolResourceManagementClient`
41. `specialization/logging_viewer_specialization.py`: constants: `LOGGING_VIEWER_SCHEMA_ID`, `LOGGING_VIEWER_CONSOLE_FORMAT_ID`, `LOGGING_VIEWER_WEB_FORMAT_ID`, `LOGGING_VIEWER_PROFILE_ID`, `LOGGING_VIEWER_SPECIALIZATION_CONFIG_ID`; functions: `build_logging_viewer_specialization_pack`, `map_record_to_viewer_envelope_and_content`, `register_logging_viewer_specialization_pack`, `build_logging_viewer_specialization_profile_config`, `upsert_logging_viewer_specialization_profile_config`, `apply_logging_viewer_specialization_profile_config`, `_load_ovs_logging_specialization_module`

## Maintenance Rule
- Regenerate this snapshot whenever any file under `03_DigitalTwin/logging_system/` changes.
- Treat this document as SSOT inventory evidence for implementation structure.
