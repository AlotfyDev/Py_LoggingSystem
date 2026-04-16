# Logging System Architecture Analysis

## Table of Contents

1. [Filesystem Structure](#1-filesystem-structure)
2. [Holistic System Overview](#holistic-system-overview)
3. [Layer 1: Models (PODs - Data Transfer Objects)](#layer-1-models-pods---data-transfer-objects)
4. [Layer 2: Ports (Interfaces/Contracts)](#layer-2-ports-interfacescontracts)
5. [Layer 3: Services (Stateful Business Logic)](#layer-3-services-stateful-business-logic)
6. [Layer 4: Adapters, Handlers, Resolvers & Composables](#layer-4-adapters-handlers-resolvers--composables)
7. [Component Interaction Diagrams](#component-interaction-diagrams)
8. [Data Flow Architecture](#data-flow-architecture)
9. [CLI (Command Line Interface)](#cli-command-line-interface)
10. [Specialization Module](#specialization-module)
11. [Resource Management](#resource-management)
12. [System Capabilities Summary](#system-capabilities-summary)

---

## 1. Filesystem Structure

```
03.0020_LoggingSystem/
├── README.md
│
├── 00_Project_Management/
│   └── [Project Management Files]
│
├── 01_Architecture/
│   ├── 00_LoggingSystem_ArchitectureDigitalTwin_FileSystem.md
│   └── ArcAnalysis/
│       ├── LoggingSystem_Architecture_Analysis.md       ← (this document)
│       └── LoggingSystem_Architecture_Evaluation.md
│
├── 02_Contracts/
│   ├── 00_LoggingSystem_Schema_Contract.template.yaml
│   ├── 01_LoggingSystem_Templated_Types_And_Functions_Contract.template.yaml
│   ├── [25+ Contract Templates]
│   └── 25_LoggingSystem_ProviderCatalog_ProfileBinding_Contract.template.yaml
│
├── 03_DigitalTwin/
│   └── logging_system/                                  # Main Package
│       ├── __init__.py                                 # Package entry point
│       │
│       ├── cli/                                        # Layer 4: CLI Interface
│       │   ├── __init__.py
│       │   ├── json_payload_parser.py
│       │   ├── parser.py
│       │   └── run_cli.py
│       │
│       ├── configurator/                               # Layer 3: Configuration Service
│       │   ├── __init__.py
│       │   ├── service.py
│       │   ├── dtos/                                   # Data Transfer Objects
│       │   ├── mappers/
│       │   └── validators/
│       │
│       ├── containers/                                 # Layer 4: Container Management
│       │   ├── __init__.py
│       │   ├── level_containers.py
│       │   └── slot_lifecycle.py
│       │
│       ├── handlers/                                  # Layer 4: Event Handlers
│       │   ├── __init__.py
│       │   └── log_level_handler.py
│       │
│       ├── level_api/                                 # Layer 1: Level API Functions
│       │   ├── __init__.py
│       │   ├── e_log_level.py
│       │   ├── log_debug.py
│       │   ├── log_error.py
│       │   ├── log_fatal.py
│       │   ├── log_info.py
│       │   ├── log_trace.py
│       │   └── log_warn.py
│       │
│       ├── log_container_module/                      # Layer 3: Container Module Service
│       │   ├── __init__.py
│       │   └── service.py
│       │
│       ├── ports/                                      # Layer 2: Port Interfaces
│       │   ├── __init__.py
│       │   ├── administrative_port.py
│       │   ├── managerial_port.py
│       │   ├── consuming_port.py
│       │   ├── adapter_registry_port.py
│       │   ├── log_container_provider_port.py
│       │   ├── resource_management_client_port.py
│       │   ├── previewer_integration_port.py
│       │   └── state_store_port.py
│       │
│       ├── production_profiles/                       # Layer 3: Production Profiles
│       │   ├── __init__.py
│       │   ├── service.py
│       │   ├── catalog_entries/
│       │   │   └── defaults.py
│       │   ├── dtos/
│       │   ├── mappers/
│       │   └── validators/
│       │
│       ├── provider_catalogs/                          # Layer 3: Provider Catalogs
│       │   ├── __init__.py
│       │   ├── service.py
│       │   ├── models.py
│       │   └── default_entries.py
│       │
│       ├── resolvers/                                 # Layer 4: Resolver Pipelines
│       │   ├── __init__.py
│       │   ├── writer_resolver_pipeline.py
│       │   ├── dispatcher_resolver_pipeline.py
│       │   └── readonly_resolver_pipeline.py
│       │
│       ├── resource_management/                       # Layer 3: Resource Management
│       │   ├── __init__.py
│       │   └── adapters/
│       │       ├── in_memory_resource_management_client.py
│       │       └── thread_pool_resource_management_client.py
│       │
│       ├── services/                                  # Layer 3: Core Services
│       │   ├── __init__.py
│       │   └── logging_service.py                     # ← Main Logging Service
│       │
│       ├── specialization/                            # Layer 4: Specialization
│       │   ├── __init__.py
│       │   └── logging_viewer_specialization.py
│       │
│       ├── previewers/                               # Layer 4: Preview/Render
│       │   ├── __init__.py
│       │   ├── console_previewer.py
│       │   └── web_previewer.py
│       │
│       ├── adapters/                                 # Layer 4: Adapters
│       │   ├── __init__.py
│       │   ├── adapter_registry.py
│       │   ├── open_telemetry_adapter.py
│       │   ├── no_op_adapter.py
│       │   ├── observability_viewer_adapter.py
│       │   └── file_state_store.py
│       │
│       ├── models/                                   # Layer 1: Models (PODs)
│       │   ├── __init__.py
│       │   ├── record.py
│       │   ├── envelope.py
│       │   ├── utc_now_iso.py
│       │   └── default_content_schema_catalog.py
│       │
│       └── tests/                                    # Test Suite
│           ├── __init__.py
│           ├── support.py
│           ├── test_logging_service.py
│           ├── test_adapters_behavior.py
│           ├── test_cli_behavior.py
│           ├── test_container_assignment_behavior.py
│           ├── test_end_to_end_behavior.py
│           ├── test_models_behavior.py
│           ├── test_new_components_behavior.py
│           ├── test_ports_contracts_behavior.py
│           ├── test_production_profiles_behavior.py
│           ├── test_provider_catalogs_behavior.py
│           └── test_specialization_import_policy.py
│
├── 03_DigitalTwin/
│   └── logging_system_Obsolete/                      # Legacy Components
│       ├── adapters/
│       ├── cli/
│       ├── containers/
│       ├── handlers/
│       ├── level_api/
│       ├── models/
│       ├── ports/
│       ├── previewers/
│       ├── resolvers/
│       ├── services/
│       └── tests/
│
└── 04_Tests/
```

---

## Holistic System Overview

The Logging System is a comprehensive, multi-tier observability platform designed for financial trading environments. It provides structured logging with multi-level filtering, adapter-based telemetry dispatch, production profile management, and container-based log organization.

### System Architecture Block Diagram

```mermaid
graph TB
    subgraph "User/API Layer"
        CLI[CLI Interface]
        LEVEL[Level API<br/>log_info, log_debug, etc.]
    end

    subgraph "Layer 3: Services (Stateful)"
        LS[LoggingService]
        CCS[ConfiguratorService]
        PC[ProviderCatalogService]
        PP[ProductionProfileCatalogService]
        LCMS[LogContainerModuleService]
    end

    subgraph "Layer 2: Ports (Interfaces)"
        ADMIN[AdministrativePort]
        MGR[ManagerialPort]
        CONS[ConsumingPort]
        LCADMIN[LogContainerAdminPort]
        LCCONS[LogContainerConsumingPort]
        LCPROV[LogContainerProviderPort]
    end

    subgraph "Layer 1: Models (PODs)"
        LR[LogRecord]
        LE[LogEnvelope]
        SCH[Schema Catalog]
    end

    subgraph "Layer 4: Composables"
        subgraph "Adapters"
            OTA[OpenTelemetryAdapter]
            NOA[NoOpAdapter]
            OVA[ObservabilityViewerAdapter]
        end
        
        subgraph "Resolvers"
            WRP[WriterResolverPipeline]
            DRP[DispatcherResolverPipeline]
            RORP[ReadOnlyResolverPipeline]
        end
        
        subgraph "Containers"
            LVC[LevelContainers]
            SLC[SlotLifecycle]
        end
        
        subgraph "Handlers"
            LLH[LogLevelHandler]
        end
        
        AR[AdapterRegistry]
    end

    LEVEL --> LS
    CLI --> LS
    LS --> ADMIN
    LS --> MGR
    LS --> CONS
    LS --> LCMS
    LCMS --> LVC
    LCMS --> SLC
    LS --> AR
    AR --> OTA
    AR --> NOA
    AR --> OVA
    LS --> WRP
    LS --> DRP
    LS --> RORP
    LS --> CCS
    CCS --> PC
    CCS --> PP
```

### High-Level Component Dependencies

```graphviz
digraph LoggingSystemArchitecture {
    rankdir=TB;
    node [shape=box, style="rounded,filled", fontname="Helvetica"];
    
    color1="#e3f2fd" color2="#fff3e0" color3="#e8f5e9" color4="#fce4ec"
    
    subgraph cluster_layer1 {
        label="Layer 1: Models (PODs)";
        bgcolor=color1;
        LR[label="LogRecord"];
        LE[label="LogEnvelope"];
        SCH[label="Schema Catalog"];
    }
    
    subgraph cluster_layer2 {
        label="Layer 2: Ports (Interfaces)";
        bgcolor=color2;
        ADMIN[label="AdministrativePort"];
        MGR[label="ManagerialPort"];
        CONS[label="ConsumingPort"];
    }
    
    subgraph cluster_layer3 {
        label="Layer 3: Services (Stateful)";
        bgcolor=color3;
        LS[label="LoggingService"];
        CCS[label="ConfiguratorService"];
    }
    
    subgraph cluster_layer4 {
        label="Layer 4: Composables";
        bgcolor=color4;
        AR[label="AdapterRegistry"];
        WRP[label="WriterResolver"];
        HAND[label="LogLevelHandler"];
    }
    
    LS -> ADMIN;
    LS -> MGR;
    LS -> CONS;
    LS -> LR;
    LS -> LE;
    LS -> AR;
    LS -> WRP;
    LS -> HAND;
    CCS -> LR;
    CCS -> LE;
}
```

---

## Layer 1: Models (PODs - Data Transfer Objects)

Layer 1 contains pure data structures with no business logic. These are immutable by design and serve as the fundamental data carriers throughout the system.

### Core Components

| Component | File | Description |
|-----------|------|-------------|
| [`LogRecord`](03_DigitalTwin/logging_system/models/record.py:9) | `models/record.py` | Immutable log entry with record_id, payload, timestamps |
| [`LogEnvelope`](03_DigitalTwin/logging_system/models/envelope.py:14) | `models/envelope.py` | Generic envelope with content, context, metadata |
| [`utc_now_iso`](03_DigitalTwin/logging_system/models/utc_now_iso.py) | `models/utc_now_iso.py` | UTC timestamp utility |
| Schema Catalog | `models/default_content_schema_catalog.py` | Default schemas: DEFAULT, ERROR, AUDIT |

### LogRecord Structure

```python
@dataclass(frozen=True)
class LogRecord:
    record_id: str                           # Unique identifier
    payload: Mapping[str, Any]               # Log data
    created_at_utc: str                      # Creation timestamp
    dispatched_at_utc: str | None = None     # Dispatch timestamp
    adapter_key: str | None = None           # Target adapter
```

### LogEnvelope Generic Structure

```python
@dataclass(frozen=True)
class LogEnvelope(Generic[TContent, TContext, TMeta]):
    content: TContent    # The log message/data
    context: TContext    # Runtime context (level, tenant, etc.)
    metadata: TMeta      # Metadata (timestamps, IDs, etc.)
    created_at_utc: str  # Creation timestamp
```

### Schema Catalog Constants

```python
DEFAULT_CONTENT_SCHEMA_ID = "schema.logging.content.default"
ERROR_CONTENT_SCHEMA_ID   = "schema.logging.content.error"
AUDIT_CONTENT_SCHEMA_ID   = "schema.logging.content.audit"
```

### Layer 1 Class Diagram

```mermaid
classDiagram
    class LogRecord {
        +str record_id
        +Mapping~str, Any~ payload
        +str created_at_utc
        +str | None dispatched_at_utc
        +str | None adapter_key
        +to_projection() dict
        +matches(filters) bool
    }
    
    class LogEnvelope~TContent, TContext, TMeta~ {
        +TContent content
        +TContext context
        +TMeta metadata
        +str created_at_utc
    }
    
    class utc_now_iso {
        +__call__() str
    }
    
    class SchemaCatalog {
        +DEFAULT_CONTENT_SCHEMA_ID
        +ERROR_CONTENT_SCHEMA_ID
        +AUDIT_CONTENT_SCHEMA_ID
    }
    
    LogRecord --> utc_now_iso
    LogEnvelope --> utc_now_iso
```

---

## Layer 2: Ports (Interfaces/Contracts)

Layer 2 defines the interface contracts using Python Protocols with `runtime_checkable`. These define the boundaries between layers and enable dependency injection.

### Core Port Interfaces

| Port | File | Purpose |
|------|------|---------|
| [`AdministrativePort`](03_DigitalTwin/logging_system/ports/administrative_port.py:7) | `ports/administrative_port.py` | Schema, policy, profile, catalog CRUD |
| [`ManagerialPort`](03_DigitalTwin/logging_system/ports/managerial_port.py:8) | `ports/managerial_port.py` | Binding, dispatch, configuration management |
| [`ConsumingPort`](03_DigitalTwin/logging_system/ports/consuming_port.py:8) | `ports/consuming_port.py` | Log submission, querying, subscriptions |
| [`LogContainerProviderPort`](03_DigitalTwin/logging_system/ports/log_container_provider_port.py:11) | `ports/log_container_provider_port.py` | Combined container interface |
| [`AdapterRegistryPort`](03_DigitalTwin/logging_system/ports/adapter_registry_port.py:9) | `ports/adapter_registry_port.py` | Adapter registration/resolution |
| [`ResourceManagementClientPort`](03_DigitalTwin/logging_system/ports/resource_management_client_port.py:8) | `ports/resource_management_client_port.py` | Lease management |

### Port Interface Hierarchy

```mermaid
classDiagram
    class AdministrativePort {
        <<protocol>>
        +register_schema()
        +create_schema()
        +get_schema()
        +register_policy()
        +create_production_profile()
        +activate_production_profile()
    }
    
    class ManagerialPort {
        <<protocol>>
        +bind_adapter()
        +bind_container_assignment()
        +bind_execution_assignment()
        +dispatch_round()
        +enforce_safepoint()
        +configure_dispatch_failure_policy()
    }
    
    class ConsumingPort {
        <<protocol>>
        +submit_signal_or_request()
        +query_projection()
        +subscribe_notifications()
        +log_debug()
        +log_info()
        +log_error()
    }
    
    class LogContainerProviderPort {
        <<protocol>>
        +configure_retention()
        +enqueue_pending()
        +drain_pending()
        +commit_dispatched()
        +list_dispatched_records()
    }
    
    class AdapterRegistryPort {
        <<protocol>>
        +register()
        +resolve()
        +list_keys()
    }
    
    class ResourceManagementClientPort {
        <<protocol>>
        +request_container_lease()
        +validate_container_lease()
        +request_execution_lease()
    }
```

---

## Layer 3: Services (Stateful Business Logic)

Layer 3 contains the core stateful services that implement the port interfaces and contain business logic.

### Core Services

| Service | File | Implements |
|---------|------|------------|
| [`LoggingService`](03_DigitalTwin/logging_system/services/logging_service.py:73) | `services/logging_service.py` | AdministrativePort, ManagerialPort, ConsumingPort |
| [`ConfiguratorService`](03_DigitalTwin/logging_system/configurator/service.py:36) | `configurator/service.py` | Configuration management |
| [`ProviderCatalogService`](03_DigitalTwin/logging_system/provider_catalogs/service.py:11) | `provider_catalogs/service.py` | Provider/connection/persistence catalog |
| [`ProductionProfileCatalogService`](03_DigitalTwin/logging_system/production_profiles/service.py:12) | `production_profiles/service.py` | Production profile management |
| [`LogContainerModuleService`](03_DigitalTwin/logging_system/log_container_module/service.py:16) | `log_container_module/service.py` | Log storage and lifecycle |

### LoggingService Architecture

The [`LoggingService`](03_DigitalTwin/logging_system/services/logging_service.py:73) is the central orchestrator that:

1. **Manages State**: Records, pending queues, listeners, audit trail
2. **Implements Ports**: All AdministrativePort, ManagerialPort, ConsumingPort methods
3. **Coordinates Components**: Adapters, resolvers, containers, handlers
4. **Handles Thread Safety**: Uses `RLock` for thread-safe operations

```mermaid
classDiagram
    class LoggingService {
        <<dataclass>>
        -_schema_registry: dict
        -_policy_registry: dict
        -_runtime_profiles: dict
        -_production_profiles: dict
        -_records: deque~LogRecord~
        -_pending_records: deque~LogRecord~
        -_adapter_registry: AdapterRegistry
        -_log_container_module: LogContainerModuleService
        -_resource_management_client: ResourceManagementClientPort
        -_provider_catalog_service: ProviderCatalogService
        -_level_containers: LevelContainers
        -_slot_lifecycle: SlotLifecycle
        -_writer_resolver_pipeline: WriterResolverPipeline
        -_dispatcher_resolver_pipeline: DispatcherResolverPipeline
        -_log_level_handler: LogLevelHandler
        -_lock: RLock
        +__post_init__()
        +log() str
        +submit_signal_or_request() str
        +dispatch_round()
        +activate_production_profile()
    }
    
    LoggingService --|> AdministrativePort
    LoggingService --|> ManagerialPort
    LoggingService --|> ConsumingPort
    
    LoggingService --> AdapterRegistry
    LoggingService --> LogContainerModuleService
    LoggingService --> ProviderCatalogService
    LoggingService --> WriterResolverPipeline
    LoggingService --> LogLevelHandler
```

### Layer 3 Service Dependencies

```mermaid
graph LR
    LS[LoggingService] --> CCS[ConfiguratorService]
    LS --> PC[ProviderCatalogService]
    LS --> PP[ProductionProfileCatalogService]
    LS --> LCMS[LogContainerModuleService]
    
    CCS --> PC
    CCS --> PP
    
    PP --> PC
    
    LCMS --> LVC[LevelContainers]
    LCMS --> SLC[SlotLifecycle]
```

---

## Layer 4: Adapters, Handlers, Resolvers & Composables

Layer 4 contains the composable components that extend system capabilities.

### Adapters

| Adapter | File | Purpose |
|---------|------|---------|
| [`AdapterRegistry`](03_DigitalTwin/logging_system/adapters/adapter_registry.py:10) | `adapters/adapter_registry.py` | Central adapter registration and resolution |
| [`OpenTelemetryAdapter`](03_DigitalTwin/logging_system/adapters/open_telemetry_adapter.py:13) | `adapters/open_telemetry_adapter.py` | OpenTelemetry protocol emission |
| [`NoOpAdapter`](03_DigitalTwin/logging_system/adapters/no_op_adapter.py:10) | `adapters/no_op_adapter.py` | No-operation fallback adapter |
| [`ObservabilityViewerAdapter`](03_DigitalTwin/logging_system/adapters/observability_viewer_adapter.py) | `adapters/observability_viewer_adapter.py` | Observability viewer integration |
| [`FileStateStore`](03_DigitalTwin/logging_system/adapters/file_state_store.py) | `adapters/file_state_store.py` | File-based state persistence |

### Resolvers

| Resolver | File | Purpose |
|----------|------|---------|
| [`WriterResolverPipeline`](03_DigitalTwin/logging_system/resolvers/writer_resolver_pipeline.py:9) | `resolvers/writer_resolver_pipeline.py` | Resolves write targets by level/tenant |
| [`DispatcherResolverPipeline`](03_DigitalTwin/logging_system/resolvers/dispatcher_resolver_pipeline.py:9) | `resolvers/dispatcher_resolver_pipeline.py` | Resolves dispatch candidates and receivers |
| [`ReadOnlyResolverPipeline`](03_DigitalTwin/logging_system/resolvers/readonly_resolver_pipeline.py) | `resolvers/readonly_resolver_pipeline.py` | Read-only query resolution |

### Containers

| Container | File | Purpose |
|-----------|------|---------|
| [`LevelContainers`](03_DigitalTwin/logging_system/containers/level_containers.py:9) | `containers/level_containers.py` | Partitioned log storage by level/tenant |
| [`SlotLifecycle`](03_DigitalTwin/logging_system/containers/slot_lifecycle.py) | `containers/slot_lifecycle.py` | Slot state management |

### Handlers

| Handler | File | Purpose |
|---------|------|---------|
| [`LogLevelHandler`](03_DigitalTwin/logging_system/handlers/log_level_handler.py:11) | `handlers/log_level_handler.py` | Normalizes log levels and routes to containers |

### Level API

| Component | File | Purpose |
|-----------|------|---------|
| [`ELogLevel`](03_DigitalTwin/logging_system/level_api/e_log_level.py:6) | `level_api/e_log_level.py` | Enum: TRACE, DEBUG, INFO, WARN, ERROR, FATAL |
| [`LogInfo`](03_DigitalTwin/logging_system/level_api/log_info.py:11) | `level_api/log_info.py` | Level-specific submitter for INFO |
| LogDebug, LogWarn, LogError, LogFatal, LogTrace | `level_api/` | Level-specific submitters |

### Previewers

| Previewer | File | Purpose |
|-----------|------|---------|
| [`ConsolePreviewer`](03_DigitalTwin/logging_system/previewers/console_previewer.py) | `previewers/console_previewer.py` | Console output formatting |
| [`WebPreviewer`](03_DigitalTwin/logging_system/previewers/web_previewer.py) | `previewers/web_previewer.py` | Web/JSON output formatting |

### Layer 4 Component Interactions

```mermaid
graph TB
    subgraph "Adapters"
        AR[AdapterRegistry] --> OTA[OpenTelemetryAdapter]
        AR --> NOA[NoOpAdapter]
        AR --> OVA[ObservabilityViewerAdapter]
    end
    
    subgraph "Resolvers"
        WRP[WriterResolverPipeline] --> DRP[DispatcherResolverPipeline]
        DRP --> RORP[ReadOnlyResolverPipeline]
    end
    
    subgraph "Containers"
        LVC[LevelContainers] --> SLC[SlotLifecycle]
    end
    
    subgraph "Handlers"
        LLH[LogLevelHandler] --> WRP
    end
    
    LLH --> LVC
    LLH --> AR
```

---

## Component Interaction Diagrams

### Log Submission Flow

```mermaid
sequenceDiagram
    participant U as User/API
    participant LS as LoggingService
    participant LLH as LogLevelHandler
    participant LC as LevelContainers
    participant WRP as WriterResolverPipeline
    participant AR as AdapterRegistry
    participant LCMS as LogContainerModuleService
    
    U->>LS: log_info("message", attributes, context)
    LS->>LLH: emit(level, message, attributes, context)
    
    rect rgb(240, 248, 255)
        Note over LLH: Normalize Envelope
        LLH->>LLH: normalize_envelope(level, message)
    end
    
    rect rgb(255, 250, 240)
        Note over LLH: Schema Validation
        LLH->>LLH: apply_schema_validation(payload, context)
    end
    
    LLH->>LS: emit_callable(payload, context)
    
    rect rgb(232, 245, 233)
        Note over LS: Create LogRecord
        LS->>LCMS: enqueue_pending(record)
        LCMS->>LC: add_record(level, record_id, context)
    end
    
    LLH->>LC: route_to_level_container(level, record_id)
    LLH->>WRP: publish_dispatch_event(level, record_id)
    
    LS->>AR: resolve(active_adapter_key)
    AR-->>LS: adapter
    LS->>adapter: emit_signal(record)
```

### Production Profile Activation Flow

```mermaid
sequenceDiagram
    participant U as User
    participant LS as LoggingService
    participant PC as ProviderCatalogService
    participant PP as ProductionProfileCatalogService
    participant CCS as ConfiguratorService
    
    U->>LS: activate_production_profile(profile_id)
    
    rect rgb(255, 243, 224)
        Note over LS: Validate Profile
        LS->>PP: get_profile(profile_id)
        PP-->>LS: profile
        LS->>PP: validate_integrity()
    end
    
    rect rgb(224, 242, 255)
        Note over LS: Extract Bindings
        LS->>LS: extract container_binding_id, execution_binding_id, adapter_key
    end
    
    rect rgb(240, 248, 255)
        Note over LS: Apply Bindings
        LS->>LS: bind_container_assignment()
        LS->>LS: bind_execution_assignment()
        LS->>LS: bind_adapter(adapter_key)
    end
    
    LS->>PC: validate_provider_catalog_integrity()
    
    LS->>LS: _active_production_profile_id = profile_id
    LS-->>U: {profile_id, container_assignment, execution_assignment, adapter_key}
```

### Dispatch Round Flow

```mermaid
sequenceDiagram
    participant LS as LoggingService
    participant DRP as DispatcherResolverPipeline
    participant LCMS as LogContainerModuleService
    participant AR as AdapterRegistry
    
    LS->>LS: dispatch_round(round_id)
    
    rect rgb(232, 245, 233)
        Note over LS: Drain Pending
        LS->>LCMS: drain_pending()
        LCMS-->>LS: pending_records
    end
    
    rect rgb(255, 250, 240)
        Note over LS: Resolve Dispatch
        LS->>DRP: resolve_dispatch_candidate(round_id, pending_count)
        DRP-->>LS: dispatch_ready=true
    end
    
    rect rgb(240, 248, 255)
        Note over LS: Execute Dispatch
        loop for each record
            LS->>AR: resolve(active_adapter_key)
            AR-->>LS: adapter
            LS->>adapter: emit_signal(record)
        end
    end
    
    rect rgb(255, 243, 224)
        Note over LS: Commit Dispatched
        LS->>LCMS: commit_dispatched(records)
    end
```

---

## Data Flow Architecture

### Input → Storage → Output Pipeline

```mermaid
flowchart LR
    subgraph Input
        CLI[CLI] --> LS
        API[Level API<br/>log_info, etc.] --> LS
    end
    
    subgraph Processing
        LS --> LLH[LogLevelHandler]
        LLH --> VAL[Validation]
        VAL --> NORM[Normalization]
    end
    
    subgraph Storage
        NORM --> LCMS[LogContainerModule]
        LCMS --> LVC[LevelContainers]
        LCMS --> SLC[SlotLifecycle]
    end
    
    subgraph Resolution
        LVC --> WRP[WriterResolver]
        WRP --> DRP[DispatcherResolver]
    end
    
    subgraph Output
        DRP --> AR[AdapterRegistry]
        AR --> OTA[OpenTelemetry]
        AR --> NOA[NoOp]
        AR --> OVA[Viewer]
    end
```

---

## CLI (Command Line Interface)

The CLI provides a comprehensive command-line interface for interacting with the LoggingService. It's built using argparse and provides subcommands for all major operations.

| Component | File | Description |
|-----------|------|-------------|
| [`run_cli`](03_DigitalTwin/logging_system/cli/run_cli.py:12) | `cli/run_cli.py` | Main CLI entry point, handles all commands |
| [`build_parser`](03_DigitalTwin/logging_system/cli/parser.py:12) | `cli/parser.py` | Argument parser with all subcommands |
| [`parse_json_object`](03_DigitalTwin/logging_system/cli/json_payload_parser.py:6) | `cli/json_payload_parser.py` | JSON payload parsing utility |

### CLI Commands Overview

```mermaid
graph TB
    subgraph "Status & Info"
        ST[status] --> LS
        LA[list-adapters] --> LS
        EV[evidence] --> LS
    end
    
    subgraph "Logging"
        EM[emit] --> LS
        LD[log-debug] --> LS
        LI[log-info] --> LS
        LW[log-warn] --> LS
        LE[log-error] --> LS
        LF[log-fatal] --> LS
        LT[log-trace] --> LS
    end
    
    subgraph "Binding"
        BA[bind-adapter] --> LS
        BCA[bind-container-assignment] --> LS
        BEA[bind-execution-assignment] --> LS
    end
    
    subgraph "Schema Management"
        SL[schema-list] --> LS
        SG[schema-get] --> LS
        SC[schema-create] --> LS
    end
    
    subgraph "Production Profiles"
        PPA[production-profile-activate] --> LS
    end
    
    subgraph "Configuration"
        CL[config-list] --> LS
        CG[config-get] --> LS
        CA[config-apply] --> LS
    end
    
    LS[LoggingService]
```

### CLI Command Categories

| Category | Commands |
|----------|----------|
| **Status** | `status`, `list-adapters`, `evidence` |
| **Logging** | `emit`, `log-debug`, `log-info`, `log-warn`, `log-error`, `log-fatal`, `log-trace` |
| **Binding** | `bind-adapter`, `bind-container-assignment`, `bind-execution-assignment`, `unbind-container-assignment`, `unbind-execution-assignment`, `container-assignment-status`, `execution-assignment-status` |
| **Dispatch** | `dispatch`, `safepoint` |
| **Schema** | `schema-list`, `schema-get`, `schema-create`, `schema-update`, `schema-delete` |
| **Policy** | `policy-list`, `policy-get`, `policy-create`, `policy-update`, `policy-delete` |
| **Runtime Profiles** | `profile-list`, `profile-get`, `profile-create`, `profile-update`, `profile-delete` |
| **Production Profiles** | `production-profile-list`, `production-profile-get`, `production-profile-create`, `production-profile-update`, `production-profile-delete`, `production-profile-activate` |
| **Unified Config** | `config-list`, `config-get`, `config-create`, `config-update`, `config-delete`, `config-apply` |
| **Policy Configuration** | `set-dispatch-failure-policy`, `set-signal-qos-profile`, `set-mandatory-label-schema`, `set-slot-lifecycle-policy`, `set-level-container-policy`, `set-resolver-pipeline-policy`, `set-previewer-profile`, `set-loglevel-api-policy` |
| **Preview** | `preview-console`, `preview-web` |

### CLI Usage Example

```bash
# Emit a log entry
python -m logging_system.cli emit --level INFO --message "Application started"

# List available adapters
python -m logging_system.cli list-adapters

# Query logs
python -m logging_system.cli query --filters-json '{"level": "ERROR"}'

# Activate production profile
python -m logging_system.cli production-profile-activate --profile-id prod.logging.local.default
```

---

## Specialization Module

The Specialization module provides integration with the ObservabilityViewerSystem for advanced log viewing capabilities.

| Component | File | Description |
|-----------|------|-------------|
| [`LoggingViewerSpecialization`](03_DigitalTwin/logging_system/specialization/logging_viewer_specialization.py:1) | `specialization/logging_viewer_specialization.py` | Viewer integration facade |

### Specialization Constants

```python
LOGGING_VIEWER_SCHEMA_ID = "logging.schema.v1"
LOGGING_VIEWER_CONSOLE_FORMAT_ID = "logging.console.default.v1"
LOGGING_VIEWER_WEB_FORMAT_ID = "logging.web.default.v1"
LOGGING_VIEWER_PROFILE_ID = "logging.default"
LOGGING_VIEWER_SPECIALIZATION_CONFIG_ID = "logging.specialization_profile.default"
```

### Specialization Functions

```mermaid
classDiagram
    class LoggingViewerSpecialization {
        <<module>>
        +build_logging_viewer_specialization_pack()
        +map_record_to_viewer_envelope_and_content()
        +register_logging_viewer_specialization_pack()
        +build_logging_viewer_specialization_profile_config()
        +upsert_logging_viewer_specialization_profile_config()
        +apply_logging_viewer_specialization_profile_config()
    }
```

---

## Resource Management

The Resource Management module provides lease-based resource management for containers and execution contexts.

| Component | File | Description |
|-----------|------|-------------|
| [`InMemoryResourceManagementClient`](03_DigitalTwin/logging_system/resource_management/adapters/in_memory_resource_management_client.py) | `resource_management/adapters/in_memory_resource_management_client.py` | In-memory implementation |
| [`ThreadPoolResourceManagementClient`](03_DigitalTwin/logging_system/resource_management/adapters/thread_pool_resource_management_client.py) | `resource_management/adapters/thread_pool_resource_management_client.py` | Thread pool implementation |

### Resource Management Capabilities

```mermaid
classDiagram
    class ResourceManagementClientPort {
        <<protocol>>
        +request_container_lease()
        +validate_container_lease()
        +get_container_lease()
        +release_container_lease()
        +request_execution_lease()
        +validate_execution_lease()
        +get_execution_lease()
        +release_execution_lease()
        +get_execution_profile()
        +execute_dispatch_tasks()
    }
```

---

## System Capabilities Summary

### Configuration Management

| Capability | Description |
|------------|-------------|
| Schema Management | Create, read, update, delete log content schemas |
| Policy Management | Dispatch, retention, QoS policies |
| Production Profiles | Bundled configuration for production deployment |
| Provider Catalogs | Provider, connection, persistence catalog entries |

### Logging Operations

| Operation | Description |
|-----------|-------------|
| Submit Signal | Submit log with payload and context |
| Level-Based Logging | log_debug, log_info, log_warn, log_error, log_fatal, log_trace |
| Query Projection | Filter and paginate log records |
| Subscribe Notifications | Register listeners for log events |

### Container Management

| Feature | Description |
|---------|-------------|
| Level Partitioning | Organize logs by level (DEBUG, INFO, etc.) |
| Tenant Partitioning | Multi-tenant isolation by tenant ID |
| Hybrid Partitioning | Combined tenant + level partitioning |
| Slot Lifecycle | Track slot states through dispatch cycle |

### Dispatch & Resolution

| Feature | Description |
|---------|-------------|
| Writer Pipeline | Resolve write targets by level/tenant |
| Dispatcher Pipeline | Resolve dispatch candidates and receivers |
| Read-Only Pipeline | Query resolution for inspections |
| Handoff Events | Track record movement between pipelines |

### Adapter System

| Adapter | Key | Purpose |
|---------|-----|---------|
| OpenTelemetry | `telemetry.opentelemetry` | Standard OTel protocol emission |
| NoOp | `telemetry.noop` | Drop-all fallback |
| Observability Viewer | `viewer.observability` | Viewer integration |

### Thread Safety Modes

| Mode | Description |
|------|-------------|
| `single_writer_per_partition` | Default, optimized for single-writer per partition |
| `thread_safe_locked` | Full locking for multi-threaded access |
| `lock_free_cas` | Lock-free compare-and-swap operations |

### Backpressure Actions

| Action | Description |
|--------|-------------|
| `block` | Block when buffer full |
| `drop_oldest` | Drop oldest records |
| `drop_newest` | Drop newest records |
| `sample` | Sample percentage of logs |
| `retry_with_jitter` | Retry with random delay |

---

## File Reference Index

| Category | Files |
|----------|-------|
| **Models (Layer 1)** | `models/__init__.py`, `models/record.py`, `models/envelope.py`, `models/utc_now_iso.py`, `models/default_content_schema_catalog.py` |
| **Ports (Layer 2)** | `ports/administrative_port.py`, `ports/managerial_port.py`, `ports/consuming_port.py`, `ports/adapter_registry_port.py`, `ports/log_container_*.py`, `ports/resource_management_client_port.py` |
| **Services (Layer 3)** | `services/logging_service.py`, `configurator/service.py`, `provider_catalogs/service.py`, `production_profiles/service.py`, `log_container_module/service.py` |
| **Composables (Layer 4)** | `adapters/*.py`, `handlers/log_level_handler.py`, `resolvers/*.py`, `containers/*.py`, `level_api/*.py`, `previewers/*.py` |
| **CLI** | `cli/run_cli.py`, `cli/parser.py`, `cli/json_payload_parser.py` |
| **Specialization** | `specialization/logging_viewer_specialization.py` |
| **Resource Management** | `resource_management/adapters/*.py` |

---

*Document Version: 1.1*
*Generated: 2026-03-11*
*Architecture: Multi-Tier Object Architecture (PTOA)*
