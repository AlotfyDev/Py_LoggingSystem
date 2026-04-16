# 00 Architecture DigitalTwin FileSystem (LoggingSystem)

## Purpose
Define canonical architecture-to-filesystem digital twin mapping for LoggingSystem with per-object implementation granularity.

## Scope
Covers contract templates and runtime implementation artifacts under `03.0020_LoggingSystem` with canonical implementation root `03_DigitalTwin`.

## Canonical Mapping Rule
Every architecture component maps to exactly one canonical repository path and declared representation mode; no runtime mappings are allowed under `03_Runtime` or legacy `DigitalTwin` roots.

## Representation Granularity Policy
- `folder_only`: ownership boundary folders only.
- `file_only`: leaf object implementation files (one file per port/class/function where applicable).
- `folder_and_file`: concern folder plus anchored object files.

## Modularity and Separation-of-Concerns Policy
- Ports are split per object file to expose architecture contracts explicitly.
- Runtime service logic is isolated in `services/logging_service.py`.
- Model entities are separated into `utc_now_iso.py`, `envelope.py`, and `record.py`.
- CLI control-plane is split into parser, payload parser, and runner modules.
- Contract files remain under `02_Contracts`; runtime code remains under `03_DigitalTwin`.

## Initial Twin Mapping
| Architecture Component | Type | Canonical Repo Path | Representation Mode | Canonical File Anchors | Status |
|---|---|---|---|---|---|
| Schema Contract | Contract | `03.0020_LoggingSystem/02_Contracts/00_LoggingSystem_Schema_Contract.template.yaml` | `file_only` | `contract.contract_id` | implemented |
| Contract Templates Folder | Module | `03.0020_LoggingSystem/02_Contracts` | `folder_only` | `contract:*` | implemented |
| Default Content Schema Catalog Contract | Contract | `03.0020_LoggingSystem/02_Contracts/05_LoggingSystem_Default_ContentSchema_Catalog_Contract.template.yaml` | `file_only` | `catalog:default_content_schema_catalog_entries` | implemented |
| Component Classification and Specialized Pipelines Contract | Contract | `03.0020_LoggingSystem/02_Contracts/06_LoggingSystem_Component_Classification_And_SpecializedPipelines_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-006` | implemented |
| OTel Integrated Export Policy Contract | Contract | `03.0020_LoggingSystem/02_Contracts/07_LoggingSystem_OTel_Integrated_Export_Policy_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-007` | implemented |
| Logger Previewer Profile Contract | Contract | `03.0020_LoggingSystem/02_Contracts/08_LoggingSystem_LoggerPreviewer_Profile_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-008` | implemented |
| Level Containers and Slot Lifecycle Contract | Contract | `03.0020_LoggingSystem/02_Contracts/09_LoggingSystem_LevelContainers_And_SlotLifecycle_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-009` | implemented |
| Specialized Resolver Pipelines Contract | Contract | `03.0020_LoggingSystem/02_Contracts/10_LoggingSystem_Specialized_Resolver_Pipelines_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-010` | implemented |
| Dedicated LogLevel API Objects Contract | Contract | `03.0020_LoggingSystem/02_Contracts/11_LoggingSystem_Dedicated_LogLevel_API_Objects_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-011` | implemented |
| CLI Command Surface Contract | Contract | `03.0020_LoggingSystem/02_Contracts/12_LoggingSystem_CLI_Command_Surface_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-012` | implemented |
| ObservabilityViewer Specialization Pack Contract | Contract | `03.0020_LoggingSystem/02_Contracts/13_LoggingSystem_ObservabilityViewer_SpecializationPack_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-013` | implemented |
| Configuration Surface Contract | Contract | `03.0020_LoggingSystem/02_Contracts/14_LoggingSystem_Configuration_Surface_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-014` | implemented |
| LogContainerModule Boundary Contract | Contract | `03.0020_LoggingSystem/02_Contracts/15_LoggingSystem_LogContainerModule_Boundary_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-015` | implemented |
| ResourceManagementClient Lease Binding Contract | Contract | `03.0020_LoggingSystem/02_Contracts/16_LoggingSystem_ResourceManagementClient_LeaseBinding_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-016` | implemented |
| LogContainer Provider Catalog Contract | Contract | `03.0020_LoggingSystem/02_Contracts/17_LoggingSystem_LogContainerProvider_Catalog_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-017` | implemented |
| Connections Catalog Contract | Contract | `03.0020_LoggingSystem/02_Contracts/18_LoggingSystem_Connections_Catalog_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-018` | implemented |
| Persistence Catalog Contract | Contract | `03.0020_LoggingSystem/02_Contracts/19_LoggingSystem_Persistence_Catalog_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-019` | implemented |
| ClientSide Ports/Adapters Injection Contract | Contract | `03.0020_LoggingSystem/02_Contracts/20_LoggingSystem_ClientSide_Ports_Adapters_Injection_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-020` | implemented |
| Catalog Integrity Validator Gate Contract | Contract | `03.0020_LoggingSystem/02_Contracts/21_LoggingSystem_Catalog_Integrity_Validator_Gate_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-021` | implemented |
| ExecutionPool Client Lease Binding Contract | Contract | `03.0020_LoggingSystem/02_Contracts/22_LoggingSystem_ExecutionPool_Client_LeaseBinding_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-022` | implemented |
| Threading Scheduling Backpressure Contract | Contract | `03.0020_LoggingSystem/02_Contracts/23_LoggingSystem_Threading_Scheduling_Backpressure_Contract.template.yaml` | `file_only` | `contract:LOGSYS-C-023` | implemented |
| Catalog Integrity Gate Validator Script | Automation | `03.0020_LoggingSystem/00_Project_Management/automation/validate_catalog_integrity_gate.py` | `file_only` | `script:LOGSYS-VAL-001` | implemented |
| Catalog Integrity Gate Evidence Report | Evidence | `03.0020_LoggingSystem/00_Project_Management/05_LOGSYS_VAL_Catalog_Integrity_Report.json` | `file_only` | `report:LOGSYS-VAL-001` | implemented |
| Threading Conformance Gate Validator Script | Automation | `03.0020_LoggingSystem/00_Project_Management/automation/validate_threading_conformance_gate.py` | `file_only` | `script:LOGSYS-VAL-002` | implemented |
| Threading Conformance Gate Evidence Report | Evidence | `03.0020_LoggingSystem/00_Project_Management/06_LOGSYS_VAL_Threading_Conformance_Report.json` | `file_only` | `report:LOGSYS-VAL-002` | implemented |
| DigitalTwin Package Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system` | `folder_only` | `package:logging_system` | implemented |
| Models Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/models` | `folder_and_file` | `utc_now_iso.py,envelope.py,record.py,default_content_schema_catalog.py` | implemented |
| UTC Clock Model | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/models/utc_now_iso.py` | `file_only` | `function:utc_now_iso` | implemented |
| Envelope Model | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/models/envelope.py` | `file_only` | `class:LogEnvelope` | implemented |
| Record Model | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/models/record.py` | `file_only` | `class:LogRecord` | implemented |
| Default Content Schema Catalog | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/models/default_content_schema_catalog.py` | `file_only` | `function:build_default_content_schema_catalog` | implemented |
| Ports Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports` | `folder_and_file` | `administrative_port.py,managerial_port.py,consuming_port.py,open_telemetry_adapter_port.py,adapter_registry_port.py,state_store_port.py,observability_viewer_provider_port.py,previewer_integration_port.py` | implemented |
| Administrative Port | Interface | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports/administrative_port.py` | `file_only` | `class:AdministrativePort` | implemented |
| Managerial Port | Interface | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports/managerial_port.py` | `file_only` | `class:ManagerialPort` | implemented |
| Consuming Port | Interface | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports/consuming_port.py` | `file_only` | `class:ConsumingPort` | implemented |
| Open Telemetry Adapter Port | Interface | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports/open_telemetry_adapter_port.py` | `file_only` | `class:OpenTelemetryAdapterPort` | implemented |
| Adapter Registry Port | Interface | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports/adapter_registry_port.py` | `file_only` | `class:AdapterRegistryPort` | implemented |
| State Store Port | Interface | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports/state_store_port.py` | `file_only` | `class:StateStorePort` | implemented |
| Observability Viewer Provider Port | Interface | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports/observability_viewer_provider_port.py` | `file_only` | `class:ObservabilityViewerProviderPort` | implemented |
| Previewer Integration Port | Interface | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports/previewer_integration_port.py` | `file_only` | `class:PreviewerIntegrationPort` | implemented |
| Adapters Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters` | `folder_and_file` | `no_op_adapter.py,unavailable_open_telemetry_adapter.py,open_telemetry_adapter.py,adapter_registry.py,default_registry_factory.py,file_state_store.py,default_state_store_factory.py,observability_viewer_adapter.py` | implemented |
| No Op Adapter | Adapter | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters/no_op_adapter.py` | `file_only` | `class:NoOpAdapter` | implemented |
| Unavailable Open Telemetry Adapter | Adapter | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters/unavailable_open_telemetry_adapter.py` | `file_only` | `class:UnavailableOpenTelemetryAdapter` | implemented |
| Open Telemetry Adapter | Adapter | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters/open_telemetry_adapter.py` | `file_only` | `class:OpenTelemetryAdapter` | implemented |
| Observability Viewer Adapter | Adapter | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters/observability_viewer_adapter.py` | `file_only` | `class:ObservabilityViewerAdapter` | implemented |
| Adapter Registry | Adapter | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters/adapter_registry.py` | `file_only` | `class:AdapterRegistry` | implemented |
| Default Registry Factory | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters/default_registry_factory.py` | `file_only` | `function:build_default_adapter_registry` | implemented |
| File State Store Adapter | Adapter | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters/file_state_store.py` | `file_only` | `class:FileStateStore` | implemented |
| Default State Store Factory | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters/default_state_store_factory.py` | `file_only` | `function:build_default_state_store` | implemented |
| Service Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/services` | `folder_and_file` | `__init__.py,logging_service.py` | implemented |
| Service Module Export | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/services/__init__.py` | `file_only` | `module:__init__` | implemented |
| Runtime Service | Service | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/services/logging_service.py` | `file_only` | `class:LoggingService,method:log` | implemented |
| CLI Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/cli` | `folder_and_file` | `json_payload_parser.py,parser.py,run_cli.py` | implemented |
| CLI JSON Parser | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/cli/json_payload_parser.py` | `file_only` | `function:parse_json_object` | implemented |
| CLI Parser | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/cli/parser.py` | `file_only` | `function:build_parser` | implemented |
| CLI Runner | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/cli/run_cli.py` | `file_only` | `function:run_cli` | implemented |
| Runtime Package Export | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/__init__.py` | `file_only` | `module:__init__` | implemented |
| Specialization Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/specialization` | `folder_and_file` | `logging_viewer_specialization.py` | implemented |
| Logging Viewer Specialization Wrapper | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/specialization/logging_viewer_specialization.py` | `file_only` | `function:build_logging_viewer_specialization_pack` | implemented |
| OVS Logging Specialization SSOT | External Component Ref | `03.0061_ObservabilityViewerSystem/03_DigitalTwin/observability_viewer_system/specialized/logging/logging_specialization_pack.py` | `file_only` | `function:build_pack` | implemented |
| Provider Catalogs Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/provider_catalogs` | `folder_and_file` | `models.py,default_entries.py,service.py` | implemented |
| Provider Catalog Models | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/provider_catalogs/models.py` | `file_only` | `class:ProviderCatalogEntry,class:ConnectionCatalogEntry,class:PersistenceCatalogEntry` | implemented |
| Provider Catalog Default Entries | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/provider_catalogs/default_entries.py` | `file_only` | `function:build_default_provider_entries` | implemented |
| Provider Catalog Service | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/provider_catalogs/service.py` | `file_only` | `class:ProviderCatalogService` | implemented |
| Production Profiles Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/production_profiles` | `folder_and_file` | `service.py` | implemented |
| Production Profile Catalog Service | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/production_profiles/service.py` | `file_only` | `class:ProductionProfileCatalogService` | implemented |
| Previewers Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/previewers` | `folder_and_file` | `console_previewer.py,web_previewer.py` | implemented |
| Console Previewer | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/previewers/console_previewer.py` | `file_only` | `class:ConsolePreviewer` | implemented |
| Web Previewer | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/previewers/web_previewer.py` | `file_only` | `class:WebPreviewer` | implemented |
| Level Containers Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/containers` | `folder_and_file` | `level_containers.py,slot_lifecycle.py` | implemented |
| Level Containers Surface | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/containers/level_containers.py` | `file_only` | `class:LevelContainers` | implemented |
| Slot Lifecycle Surface | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/containers/slot_lifecycle.py` | `file_only` | `class:SlotLifecycle` | implemented |
| Resolver Pipelines Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/resolvers` | `folder_and_file` | `writer_resolver_pipeline.py,dispatcher_resolver_pipeline.py,readonly_resolver_pipeline.py` | implemented |
| Writer Resolver Pipeline | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/resolvers/writer_resolver_pipeline.py` | `file_only` | `class:WriterResolverPipeline` | implemented |
| Dispatcher Resolver Pipeline | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/resolvers/dispatcher_resolver_pipeline.py` | `file_only` | `class:DispatcherResolverPipeline` | implemented |
| ReadOnly Resolver Pipeline | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/resolvers/readonly_resolver_pipeline.py` | `file_only` | `class:ReadOnlyResolverPipeline` | implemented |
| LogLevel API Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/level_api` | `folder_and_file` | `e_log_level.py,log_debug.py,log_info.py,log_warn.py,log_error.py,log_fatal.py,log_trace.py` | implemented |
| E LogLevel Enum | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/level_api/e_log_level.py` | `file_only` | `class:ELogLevel` | implemented |
| Log Debug API | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/level_api/log_debug.py` | `file_only` | `class:LogDebug` | implemented |
| Log Info API | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/level_api/log_info.py` | `file_only` | `class:LogInfo` | implemented |
| Log Warn API | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/level_api/log_warn.py` | `file_only` | `class:LogWarn` | implemented |
| Log Error API | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/level_api/log_error.py` | `file_only` | `class:LogError` | implemented |
| Log Fatal API | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/level_api/log_fatal.py` | `file_only` | `class:LogFatal` | implemented |
| Log Trace API | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/level_api/log_trace.py` | `file_only` | `class:LogTrace` | implemented |
| Handlers Folder | Module | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/handlers` | `folder_and_file` | `log_level_handler.py` | implemented |
| LogLevel Handler | Component | `03.0020_LoggingSystem/03_DigitalTwin/logging_system/handlers/log_level_handler.py` | `file_only` | `class:LogLevelHandler` | implemented |

## Layered ASCII Twin Trees
Tree A: Contracts Layer
```text
03.0020_LoggingSystem/
└── 02_Contracts/
    ├── 00_LoggingSystem_Schema_Contract.template.yaml
    ├── 01_LoggingSystem_Templated_Types_And_Functions_Contract.template.yaml
    ├── 02_LoggingSystem_Admin_Manager_Consumer_Ports_Contract.template.yaml
    ├── 03_LoggingSystem_OpenTelemetry_Adapter_Boundary_Contract.template.yaml
    ├── 04_LoggingSystem_ArchitectureDigitalTwin_Filesystem_Contract.template.yaml
    ├── 05_LoggingSystem_Default_ContentSchema_Catalog_Contract.template.yaml
    ├── 06_LoggingSystem_Component_Classification_And_SpecializedPipelines_Contract.template.yaml
    ├── 07_LoggingSystem_OTel_Integrated_Export_Policy_Contract.template.yaml
    ├── 08_LoggingSystem_LoggerPreviewer_Profile_Contract.template.yaml
    ├── 09_LoggingSystem_LevelContainers_And_SlotLifecycle_Contract.template.yaml
    ├── 10_LoggingSystem_Specialized_Resolver_Pipelines_Contract.template.yaml
    ├── 11_LoggingSystem_Dedicated_LogLevel_API_Objects_Contract.template.yaml
    ├── 12_LoggingSystem_CLI_Command_Surface_Contract.template.yaml
    ├── 13_LoggingSystem_ObservabilityViewer_SpecializationPack_Contract.template.yaml
    ├── 14_LoggingSystem_Configuration_Surface_Contract.template.yaml
    ├── 15_LoggingSystem_LogContainerModule_Boundary_Contract.template.yaml
    ├── 16_LoggingSystem_ResourceManagementClient_LeaseBinding_Contract.template.yaml
    ├── 17_LoggingSystem_LogContainerProvider_Catalog_Contract.template.yaml
    ├── 18_LoggingSystem_Connections_Catalog_Contract.template.yaml
    ├── 19_LoggingSystem_Persistence_Catalog_Contract.template.yaml
    ├── 20_LoggingSystem_ClientSide_Ports_Adapters_Injection_Contract.template.yaml
    ├── 21_LoggingSystem_Catalog_Integrity_Validator_Gate_Contract.template.yaml
    ├── 22_LoggingSystem_ExecutionPool_Client_LeaseBinding_Contract.template.yaml
    └── 23_LoggingSystem_Threading_Scheduling_Backpressure_Contract.template.yaml
```

Tree B: Runtime Root One-Layer
```text
03.0020_LoggingSystem/
└── 03_DigitalTwin/
    └── logging_system/
        ├── __init__.py
        ├── models/
        ├── ports/
        ├── adapters/
        ├── services/
        ├── cli/
        ├── tests/
        ├── provider_catalogs/
        ├── production_profiles/
        ├── previewers/
        ├── containers/
        ├── resolvers/
        ├── level_api/
        ├── handlers/
        ├── configurator/
        └── specialization/
```

Tree C: Models Depth (to class/function level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/models/
├── __init__.py
├── default_content_schema_catalog.py
│   ↳ const:DEFAULT_CONTENT_SCHEMA_ID
│   ↳ const:AUDIT_CONTENT_SCHEMA_ID
│   ↳ const:ERROR_CONTENT_SCHEMA_ID
│   ↳ function:build_default_content_schema_catalog
├── envelope.py
│   ↳ class:LogEnvelope
├── record.py
│   ↳ class:LogRecord
└── utc_now_iso.py
    ↳ function:utc_now_iso
```

Tree D: Ports Depth (to class level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/ports/
├── __init__.py
├── adapter_registry_port.py
│   ↳ class:AdapterRegistryPort
├── administrative_port.py
│   ↳ class:AdministrativePort
├── consuming_port.py
│   ↳ class:ConsumingPort
├── managerial_port.py
│   ↳ class:ManagerialPort
├── open_telemetry_adapter_port.py
│   ↳ class:OpenTelemetryAdapterPort
├── observability_viewer_provider_port.py
│   ↳ class:ObservabilityViewerProviderPort
├── previewer_integration_port.py
│   ↳ class:PreviewerIntegrationPort
└── state_store_port.py
    ↳ class:StateStorePort
```

Tree E: Adapters Depth (to class/function level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/adapters/
├── __init__.py
├── adapter_registry.py
│   ↳ class:AdapterRegistry
├── default_registry_factory.py
│   ↳ function:build_default_adapter_registry
├── default_state_store_factory.py
│   ↳ const:DEFAULT_STATE_ENV_VAR
│   ↳ function:build_default_state_store
├── file_state_store.py
│   ↳ class:FileStateStore
├── no_op_adapter.py
│   ↳ class:NoOpAdapter
├── open_telemetry_adapter.py
│   ↳ class:OpenTelemetryAdapter
├── observability_viewer_adapter.py
│   ↳ class:ObservabilityViewerAdapter
└── unavailable_open_telemetry_adapter.py
    ↳ class:UnavailableOpenTelemetryAdapter
```

Tree F: Services Depth (to class level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/services/
├── __init__.py
└── logging_service.py
    ↳ class:LoggingService
```

Tree G: CLI Depth (to function level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/cli/
├── __init__.py
├── json_payload_parser.py
│   ↳ function:parse_json_object
├── parser.py
│   ↳ function:build_parser
└── run_cli.py
    ↳ function:run_cli
```

Tree H: Tests Depth (to class level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/tests/
├── __init__.py
├── support.py
│   ↳ class:InMemoryStateStore
├── test_adapters_behavior.py
│   ↳ class:AdapterRegistryBehaviorTests
│   ↳ class:AdapterBehaviorTests
├── test_cli_behavior.py
│   ↳ class:CliBehaviorTests
├── test_end_to_end_behavior.py
│   ↳ class:CollectingAdapter
│   ↳ class:FailingAdapter
│   ↳ class:EndToEndBehaviorTests
├── test_logging_service.py
│   ↳ class:LoggingServiceTests
│   ↳ class:AdapterRegistryTests
├── test_models_behavior.py
│   ↳ class:LogEnvelopeBehaviorTests
│   ↳ class:LogRecordBehaviorTests
└── test_ports_contracts_behavior.py
    ↳ class:PortsContractBehaviorTests
```

Tree I: Previewers Planned Depth (to class level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/previewers/
├── __init__.py
├── console_previewer.py
│   ↳ class:ConsolePreviewer
└── web_previewer.py
    ↳ class:WebPreviewer
```

Tree J: Containers Planned Depth (to class level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/containers/
├── __init__.py
├── level_containers.py
│   ↳ class:LevelContainers
└── slot_lifecycle.py
    ↳ class:SlotLifecycle
```

Tree K: Resolver Pipelines Planned Depth (to class level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/resolvers/
├── __init__.py
├── writer_resolver_pipeline.py
│   ↳ class:WriterResolverPipeline
├── dispatcher_resolver_pipeline.py
│   ↳ class:DispatcherResolverPipeline
└── readonly_resolver_pipeline.py
    ↳ class:ReadOnlyResolverPipeline
```

Tree L: Level API Planned Depth (to class level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/level_api/
├── __init__.py
├── e_log_level.py
│   ↳ class:ELogLevel
├── log_debug.py
│   ↳ class:LogDebug
├── log_info.py
│   ↳ class:LogInfo
├── log_warn.py
│   ↳ class:LogWarn
├── log_error.py
│   ↳ class:LogError
├── log_fatal.py
│   ↳ class:LogFatal
└── log_trace.py
    ↳ class:LogTrace
```

Tree M: Handlers Planned Depth (to class level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/handlers/
├── __init__.py
└── log_level_handler.py
    ↳ class:LogLevelHandler
```

Tree N: Runtime Package Layer (full)
```text
03.0020_LoggingSystem/
└── 03_DigitalTwin/
    └── logging_system/
        ├── __init__.py
        ├── models/
        │   ├── __init__.py
        │   ├── utc_now_iso.py
        │   ├── envelope.py
        │   ├── record.py
        │   └── default_content_schema_catalog.py
        ├── ports/
        ├── adapters/
        ├── services/
        ├── cli/
        ├── tests/
        ├── provider_catalogs/
        ├── production_profiles/
        ├── previewers/
        ├── containers/
        ├── resolvers/
        ├── level_api/
        ├── handlers/
        ├── configurator/
        └── specialization/
```

Tree O: LogContainerModule + ResourceManagement Depth (new)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/
├── log_container_module/
│   ├── __init__.py
│   └── service.py
│       ↳ class:LogContainerModuleService
├── resource_management/
│   ├── __init__.py
│   └── adapters/
│       ├── __init__.py
│       ├── in_memory_resource_management_client.py
│       │   ↳ class:InMemoryResourceManagementClient
│       └── thread_pool_resource_management_client.py
│           ↳ class:ThreadPoolResourceManagementClient
├── provider_catalogs/
│   ├── __init__.py
│   ├── models.py
│   │   ↳ class:ProviderCatalogEntry
│   │   ↳ class:ConnectionCatalogEntry
│   │   ↳ class:PersistenceCatalogEntry
│   ├── default_entries.py
│   │   ↳ function:build_default_provider_entries
│   │   ↳ function:build_default_connection_entries
│   │   ↳ function:build_default_persistence_entries
│   └── service.py
│       ↳ class:ProviderCatalogService
├── production_profiles/
│   ├── __init__.py
│   ├── service.py
│   │   ↳ class:ProductionProfileCatalogService
│   ├── dtos/
│   │   └── production_profile_dto.py
│   │       ↳ class:ProductionProfileDTO
│   ├── validators/
│   │   └── production_profile_validator.py
│   │       ↳ class:ProductionProfileValidator
│   └── mappers/
│       └── production_profile_mapper.py
│           ↳ function:to_runtime_payload
└── ports/
    ├── log_container_administrative_port.py
    │   ↳ class:LogContainerAdministrativePort
    ├── log_container_managerial_port.py
    │   ↳ class:LogContainerManagerialPort
    ├── log_container_consuming_port.py
    │   ↳ class:LogContainerConsumingPort
    ├── log_container_provider_port.py
    │   ↳ class:LogContainerProviderPort
    └── resource_management_client_port.py
        ↳ class:ResourceManagementClientPort
```

Tree P: Specialization Depth (to function level)
```text
03.0020_LoggingSystem/03_DigitalTwin/logging_system/specialization/
├── __init__.py
└── logging_viewer_specialization.py
    ↳ const:LOGGING_VIEWER_SCHEMA_ID
    ↳ const:LOGGING_VIEWER_CONSOLE_FORMAT_ID
    ↳ const:LOGGING_VIEWER_WEB_FORMAT_ID
    ↳ const:LOGGING_VIEWER_PROFILE_ID
    ↳ function:build_logging_viewer_specialization_pack
    ↳ function:map_record_to_viewer_envelope_and_content
    ↳ function:register_logging_viewer_specialization_pack
```

Tree Q: External SSOT Reference for Logging Specialization
```text
03.0061_ObservabilityViewerSystem/03_DigitalTwin/observability_viewer_system/specialized/logging/
├── __init__.py
└── logging_specialization_pack.py
    ↳ function:build_pack
    ↳ function:register_pack
    ↳ function:map_record
```

## Representation Mode to Tree Semantics
| Representation Mode | Required ASCII Node Type | Enforcement |
|---|---|---|
| `folder_only` | directory node only | canonical path must resolve to directory node |
| `file_only` | file leaf node only | canonical path must resolve to file node |
| `folder_and_file` | directory node + anchored file nodes | canonical folder and anchors must both resolve in tree |

## Canonical Internal Module Map
| Module / Concern | Responsibility | Must Not Contain |
|---|---|---|
| `models/*.py` | typed entities, envelopes, immutable records | adapter/provider integrations |
| `ports/*.py` | pure administrative/managerial/consuming/provider contracts | concrete integration logic |
| `adapters/*.py` | third-party boundary wiring and registries | domain orchestration/policies |
| `previewers/*.py` | local and remote preview rendering surfaces | core write-path mutation |
| `containers/*.py` | level-partitioned container and slot-lifecycle surfaces | vendor SDK calls |
| `resolvers/*.py` | specialized writer/dispatcher/readonly resolver pipelines | collapsed shared authority service |
| `level_api/*.py` | dedicated log-level API objects and enum surfaces | generic mandatory `log()` policy |
| `handlers/*.py` | templated level handler orchestration | transport-specific SDK internals |
| `services/*.py` | orchestration and policy application through ports | transport-specific SDK internals |
| `configurator/*` | typed DTO config CRUD, validation, mapping, apply orchestration | direct transport emission and domain write-path mutation |
| `provider_catalogs/*` | provider/connection/persistence catalogs and cross-catalog integrity checks as standalone concern | log emission write-path orchestration |
| `cli/*.py` | control-plane parsing and command routing | subsystem policy ownership |
| `03_DigitalTwin/logging_system/__init__.py` | package export boundary | business runtime logic |

## Conformance Rules
1. All `implemented` mapped canonical paths must resolve to existing files/folders.
2. All `planned` mapped canonical paths must be generated before migration/runtime conformance closure.
3. Layered ASCII trees are mandatory and must be machine-parseable.
4. Per-object port/class/function files are mandatory for mapped contract-critical concerns.
5. Any mapping to `03_Runtime` or legacy `DigitalTwin` runtime roots is fail-closed.
6. `folder_and_file` mappings must include non-empty canonical file anchors.

## Change Control
- Any new runtime object file requires twin mapping update first.
- Any path move requires architecture document + contract update and validator pass.
- Concern-boundary changes require update of representation mode and tree semantics.
