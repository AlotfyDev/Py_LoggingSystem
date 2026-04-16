# LoggingSystem Architectural Taxonomy

**Version:** 1.0  
**Date:** 2026-04-15  
**System:** 03.0020_LoggingSystem  
**Architecture Style:** Multi-Tier Object Architecture (PTOA) - Hexagonal/Ports & Adapters

---

## Table of Contents

1. [System Layers](#1-system-layers)
2. [Domain Components](#2-domain-components)
3. [Port Hierarchy](#3-port-hierarchy)
4. [Adapter Hierarchy](#4-adapter-hierarchy)
5. [Data Flow](#5-data-flow)
6. [Dependency Injection](#6-dependency-injection)
7. [Cross-Cutting Concerns](#7-cross-cutting-concerns)
8. [Patterns Used](#8-patterns-used)

---

## 1. System Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LOGGINGSYSTEM ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 5: Infrastructure & Entry Points                              │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                  │   │
│  │  │    CLI     │ │  Level API │ │   Direct    │                  │   │
│  │  │  run_cli   │ │ LogDebug   │ │  Service    │                  │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 4: Composable Components                                     │   │
│  │                                                                      │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │   │
│  │  │   Adapters   │ │   Resolvers  │ │  Containers  │              │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘              │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │   │
│  │  │   Handlers   │ │  Level API   │ │  Previewers  │              │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 3: Services (Stateful Business Logic)                         │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │                    LoggingService                             │    │   │
│  │  │  (Central Orchestrator - Implements 3 Primary Ports)        │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │   │
│  │  │Configurator │ │  Provider   │ │Production   │              │   │
│  │  │  Service    │ │  Catalog    │ │  Profile    │              │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 2: Ports (Interface Contracts - Python Protocols)            │   │
│  │                                                                      │   │
│  │  ┌────────────────────────┐  ┌────────────────────────┐             │   │
│  │  │    INPUT PORTS        │  │    OUTPUT PORTS       │             │   │
│  │  │  (Driving/Primary)    │  │   (Driven/Secondary)  │             │   │
│  │  ├────────────────────────┤  ├────────────────────────┤             │   │
│  │  │ • AdministrativePort  │  │ • AdapterRegistryPort │             │   │
│  │  │ • ConsumingPort      │  │ • StateStorePort      │             │   │
│  │  │ • Container Ports    │  │ • OTelAdapterPort    │             │   │
│  │  └────────────────────────┘  └────────────────────────┘             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LAYER 1: Models (Pure Data Transfer Objects)                        │   │
│  │                                                                      │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │   │
│  │  │  LogRecord  │ │ LogEnvelope │ │SchemaCatalog│              │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Layer 1: Models (Data Transfer Objects)

**Responsibility:** Pure data structures with no business logic

| Component | File | Description |
|-----------|------|-------------|
| `LogRecord` | `models/record.py` | Immutable log entry with record_id, payload, timestamps |
| `LogEnvelope` | `models/envelope.py` | Generic envelope with content, context, metadata |
| `utc_now_iso` | `models/utc_now_iso.py` | UTC timestamp utility function |
| `SchemaCatalog` | `models/default_content_schema_catalog.py` | Default schemas: DEFAULT, ERROR, AUDIT |

---

### Layer 2: Ports (Interface Contracts)

**Responsibility:** Boundaries between layers using Python Protocols for dependency injection

#### Input Ports (Driving/Primary)

| Port | File | Methods |
|------|------|---------|
| `AdministrativePort` | `ports/administrative_port.py` | Schema CRUD, Policy CRUD, Profile activation |
| `ConsumingPort` | `ports/consuming_port.py` | Log submission, Querying, Subscriptions |
| `LogContainerAdministrativePort` | `ports/log_container_administrative_port.py` | Container config |
| `LogContainerConsumingPort` | `ports/log_container_consuming_port.py` | Container consuming ops |

#### Output Ports (Driven/Secondary)

| Port | File | Methods |
|------|------|---------|
| `ManagerialPort` | `ports/managerial_port.py` | Binding, Dispatch configuration |
| `LogContainerManagerialPort` | `ports/log_container_managerial_port.py` | Container lifecycle |
| `AdapterRegistryPort` | `ports/adapter_registry_port.py` | Adapter registration/resolution |
| `ResourceManagementClientPort` | `ports/resource_management_client_port.py` | Lease management |
| `StateStorePort` | `ports/state_store_port.py` | State persistence |
| `OpenTelemetryAdapterPort` | `ports/open_telemetry_adapter_port.py` | OTel emission |
| `ObservabilityViewerProviderPort` | `ports/observability_viewer_provider_port.py` | Viewer integration |
| `PreviewerIntegrationPort` | `ports/previewer_integration_port.py` | Preview formatting |

---

### Layer 3: Services (Stateful Business Logic)

**Responsibility:** Orchestrates components and implements port interfaces

| Service | File | Responsibility |
|---------|------|----------------|
| `LoggingService` | `services/logging_service.py` | Central orchestrator - implements AdministrativePort, ManagerialPort, ConsumingPort |
| `ConfiguratorService` | `configurator/service.py` | DTO CRUD, validation, mapping |
| `ProviderCatalogService` | `provider_catalogs/service.py` | Provider/connection/persistence catalog management |
| `ProductionProfileCatalogService` | `production_profiles/service.py` | Production profile management |
| `LogContainerModuleService` | `log_container_module/service.py` | Log storage and lifecycle management |

---

### Layer 4: Composable Components

#### Adapters (implement port interfaces)

| Adapter | Implements | Backend | Key |
|---------|-----------|---------|-----|
| `OpenTelemetryAdapter` | `OpenTelemetryAdapterPort` | OpenTelemetry | `telemetry.opentelemetry` |
| `NoOpAdapter` | `OpenTelemetryAdapterPort` | No-op | `telemetry.noop` |
| `UnavailableOpenTelemetryAdapter` | `OpenTelemetryAdapterPort` | Fallback | - |
| `ObservabilityViewerAdapter` | `ObservabilityViewerProviderPort` | Viewer | `viewer.observability` |
| `FileStateStore` | `StateStorePort` | File | - |
| `AdapterRegistry` | `AdapterRegistryPort` | Memory | - |

#### Resolvers (Pipeline Pattern)

| Resolver | File | Purpose |
|----------|------|---------|
| `WriterResolverPipeline` | `resolvers/writer_resolver_pipeline.py` | Write target resolution by level/tenant |
| `DispatcherResolverPipeline` | `resolvers/dispatcher_resolver_pipeline.py` | Dispatch candidate resolution |
| `ReadOnlyResolverPipeline` | `resolvers/readonly_resolver_pipeline.py` | Read-only query resolution |

#### Containers (Partitioned Storage)

| Container | File | Strategy |
|-----------|------|----------|
| `LevelContainers` | `containers/level_containers.py` | Partition by level + tenant |
| `SlotLifecycle` | `containers/slot_lifecycle.py` | Record lifecycle state machine |

#### Level API (6 Log Levels)

| Level | Class | Enum Value |
|-------|-------|------------|
| TRACE | `LogTrace` | `ELogLevel.TRACE` |
| DEBUG | `LogDebug` | `ELogLevel.DEBUG` |
| INFO | `LogInfo` | `ELogLevel.INFO` |
| WARN | `LogWarn` | `ELogLevel.WARN` |
| ERROR | `LogError` | `ELogLevel.ERROR` |
| FATAL | `LogFatal` | `ELogLevel.FATAL` |

#### Previewers

| Previewer | Output |
|-----------|--------|
| `ConsolePreviewer` | Terminal formatting |
| `WebPreviewer` | Web/JSON formatting |

#### Resource Management

| Client | Strategy |
|--------|----------|
| `InMemoryResourceManagementClient` | In-memory lease tracking |
| `ThreadPoolResourceManagementClient` | Thread pool with task execution |

---

## 2. Domain Components

### Core Services Dependency Graph

```
                    ┌─────────────────────────┐
                    │    LoggingService        │
                    │   (Central Orchestrator) │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│ Configurator    │  │ ProviderCatalog │  │ ProductionProfile   │
│ Service         │  │ Service        │  │ CatalogService     │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │    AdapterRegistry       │
                    └───────────┬─────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
          ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ OpenTelemetry   │  │   NoOpAdapter  │  │ Observability   │
│ Adapter         │  │                │  │ ViewerAdapter   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Data Models

```
LogRecord (Immutable)
├── record_id: str (UUID)
├── level: ELogLevel
├── payload: Mapping[str, Any]
├── timestamp_utc: str
├── context: Mapping[str, Any]
├── metadata: Mapping[str, Any]
├── dispatch_state: DispatchState
└── dispatch_metadata: Mapping[str, Any]

LogEnvelope (Generic)
├── content: TContent
├── context: TContext
└── metadata: TMeta
```

---

## 3. Port Hierarchy

### Classification Matrix

| Port | Type | Direction | Primary? |
|------|------|-----------|----------|
| `AdministrativePort` | Schema/Policy/Profile | Input | ✅ Primary |
| `ConsumingPort` | Log Emission | Input | ✅ Primary |
| `ManagerialPort` | Binding/Dispatch | Output | ❌ Secondary |
| `LogContainer*Port` | Container Ops | Mixed | ❌ Secondary |
| `AdapterRegistryPort` | Adapter Mgmt | Output | ❌ Secondary |
| `StateStorePort` | Persistence | Output | ❌ Secondary |
| `OpenTelemetryAdapterPort` | Telemetry | Output | ❌ Secondary |
| `ResourceManagementClientPort` | Leases | Output | ❌ Secondary |

### Port Method Summary

| Port | Key Methods |
|------|-------------|
| `AdministrativePort` | `create_schema`, `get_schema`, `create_policy`, `create_production_profile`, `activate_profile` |
| `ConsumingPort` | `submit_signal_or_request`, `query_projection`, `subscribe_notifications`, `log_debug`, `log_info` |
| `ManagerialPort` | `bind_adapter`, `dispatch_round`, `enforce_safepoint` |
| `LogContainerProviderPort` | `level_containers`, `slot_lifecycle`, `configure_retention` |

---

## 4. Adapter Hierarchy

### Adapter Implementation Map

```
                    ┌─────────────────────────────┐
                    │    AdapterRegistry           │
                    │   (Registry Pattern)         │
                    └─────────────┬───────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│ OpenTelemetryAdapter│  │   NoOpAdapter    │  │ Observability     │
│                   │  │                   │  │ ViewerAdapter     │
│ implements:       │  │ implements:       │  │                   │
│ • OTelAdapterPort │  │ • OTelAdapterPort │  │ implements:       │
│                   │  │                   │  │ • ViewerProvider  │
│ key: telemetry.   │  │ key: telemetry.   │  │                   │
│   opentelemetry   │  │   noop            │  │ key: viewer.      │
│                   │  │                   │  │   observability   │
└───────────────────┘  └───────────────────┘  └───────────────────┘

┌───────────────────┐  ┌───────────────────┐
│ UnavailableOTel   │  │   FileStateStore  │
│ Adapter           │  │                   │
│                   │  │ implements:       │
│ implements:       │  │ • StateStorePort │
│ • OTelAdapterPort │  │                   │
└───────────────────┘  └───────────────────┘
```

### Adapter Selection Keys

| Key | Adapter | Backend |
|-----|---------|---------|
| `telemetry.opentelemetry` | `OpenTelemetryAdapter` | OpenTelemetry SDK |
| `telemetry.noop` | `NoOpAdapter` | No-op (drop all) |
| `viewer.observability` | `ObservabilityViewerAdapter` | OVS System |

---

## 5. Data Flow

### Emit Flow (Input → Output)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           EMIT FLOW                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. ENTRY POINTS                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │    CLI      │  │  Level API  │  │   Direct    │                         │
│  │ run_cli()   │  │ log_debug() │  │ submit()    │                         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                         │
│         │                 │                 │                                │
│         └─────────────────┼─────────────────┘                                │
│                           ▼                                                  │
│  2. NORMALIZATION (LogLevelHandler)                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • Normalize envelope                                                 │   │
│  │  • Apply schema validation                                           │   │
│  │  • Determine log level                                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           ▼                                                  │
│  3. RECORD CREATION (LoggingService)                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • Generate record_id (UUID)                                        │   │
│  │  • Add timestamps                                                   │   │
│  │  • Create LogRecord                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           ▼                                                  │
│  4. CONTAINER ROUTING (LevelContainers)                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • Partition by level (DEBUG, INFO, WARN, ERROR, FATAL, TRACE)       │   │
│  │  • Partition by tenant (if multi-tenant)                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           ▼                                                  │
│  5. PENDING QUEUE (LogContainerModuleService)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • enqueue_pending(record)                                          │   │
│  │  • Update slot lifecycle                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Dispatch Flow (Processing → Export)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          DISPATCH FLOW                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. TRIGGER                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  dispatch_round() or safepoint() or automatic interval                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           ▼                                                  │
│  2. DRAIN PENDING (LogContainerModuleService)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • drain_pending() → list of records                                │   │
│  │  • Update dispatch state                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           ▼                                                  │
│  3. RESOLVE ADAPTER (DispatcherResolverPipeline)                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • resolve_dispatch_candidate()                                     │   │
│  │  • Check adapter availability                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           ▼                                                  │
│  4. LOOKUP ADAPTER (AdapterRegistry)                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  registry.resolve(active_adapter_key)                               │   │
│  │  → OpenTelemetryAdapter / NoOpAdapter / ViewerAdapter              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           ▼                                                  │
│  5. EMIT (Adapter)                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  adapter.emit_signal(record)                                         │   │
│  │  → OTel Collector / Drop / Viewer System                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           ▼                                                  │
│  6. COMMIT (LogContainerModuleService)                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • commit_dispatched(records)                                       │   │
│  │  • Update slot lifecycle to committed                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Dependency Injection

### Constructor Injection

```python
class LoggingService:
    def __init__(
        self,
        adapter_registry: AdapterRegistryPort,
        log_container_module: LogContainerProviderPort,
        resource_management_client: ResourceManagementClientPort,
        provider_catalog_service: ProviderCatalogService,
        level_containers: LevelContainers,
        slot_lifecycle: SlotLifecycle,
        writer_resolver_pipeline: WriterResolverPipeline,
        dispatcher_resolver_pipeline: DispatcherResolverPipeline,
        log_level_handler: LogLevelHandler,
    ):
        ...
```

### Factory Pattern

| Factory | Returns | Configuration |
|---------|---------|----------------|
| `build_default_adapter_registry()` | `AdapterRegistry` | Pre-configured with OTel, NoOp, Viewer adapters |
| `build_default_state_store()` | `StateStorePort` | FileStateStore (env: `LOGSYS_STATE_STORE_ENV_VAR`) |

### Registry Pattern

```python
# Registration
registry.register("telemetry.opentelemetry", OpenTelemetryAdapter())
registry.register("telemetry.noop", NoOpAdapter())

# Resolution
adapter = registry.resolve("telemetry.opentelemetry")
```

---

## 7. Cross-Cutting Concerns

### Validation Layers

| Validator | Location | Validates |
|----------|----------|-----------|
| Schema Validation | `LogLevelHandler` | Payload against content schema |
| Profile Validation | `production_profiles/validators/` | Production profile structure |
| Catalog Integrity | `ProviderCatalogService` | Cross-catalog consistency |
| Config Type | `configurator/validators/` | Configuration type support |

### Error Handling Strategy

| Strategy | Trigger | Action |
|----------|---------|--------|
| NoOp Fallback | Primary adapter unavailable | Drop signals silently |
| Unavailable OTel | OTel SDK unavailable | Log warning, continue |
| Dispatch Failure Policy | Export fails | Configurable: block/drop/retry |

### Thread Safety

| Mode | Description |
|------|-------------|
| `single_writer_per_partition` | One writer per partition |
| `thread_safe_locked` | RLock for all operations |
| `lock_free_cas` | Compare-and-swap |

### Backpressure Actions

| Action | Behavior |
|--------|----------|
| `block` | Block until capacity |
| `drop_oldest` | Drop oldest records |
| `drop_newest` | Drop newest record |
| `sample` | Sample a percentage |
| `retry_with_jitter` | Retry with random delay |

---

## 8. Patterns Used

### Hexagonal Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HEXAGONAL VIEW                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         ┌─────────────────────┐                             │
│                         │     LoggingService   │                             │
│                         │   (Application Core) │                             │
│                         └──────────┬──────────┘                             │
│                                    │                                        │
│         ┌─────────────────────────┼─────────────────────────┐              │
│         │                         │                         │              │
│         ▼                         ▼                         ▼              │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐         │
│  │   Admin    │          │   Consume   │          │  Manage    │         │
│  │   Port     │          │   Port      │          │   Port     │         │
│  └──────┬─────┘          └──────┬─────┘          └──────┬─────┘         │
│         │                       │                        │                 │
│         └───────────────────────┼────────────────────────┘                 │
│                                 │                                          │
│                                 ▼                                          │
│                    ┌─────────────────────────┐                            │
│                    │    AdapterRegistry       │                            │
│                    └─────────────┬───────────┘                            │
│                                  │                                         │
│    ┌─────────────────────────────┼─────────────────────────────┐           │
│    │                             │                             │           │
│    ▼                             ▼                             ▼           │
│ ┌──────────┐              ┌──────────┐                ┌──────────┐         │
│ │   OTel   │              │   NoOp  │                │  Viewer  │         │
│ │ Adapter  │              │ Adapter │                │ Adapter  │         │
│ └──────────┘              └──────────┘                └──────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pattern Summary

| Pattern | Usage | Benefit |
|---------|-------|---------|
| **Hexagonal** | Core → Ports → Adapters | Loose coupling, testability |
| **Registry** | `AdapterRegistry` | Runtime adapter selection |
| **Factory** | `build_default_*()` | Centralized creation |
| **Pipeline** | `*ResolverPipeline` | Composable strategies |
| **Container** | `LevelContainers` | Organized storage |
| **Generic Envelope** | `LogEnvelope<T>` | Type-safe flexibility |
| **Provider Catalog** | `*CatalogEntry` | Capability-based selection |

---

## Component Inventory Summary

| Category | Count | Key Components |
|----------|-------|----------------|
| **Models** | 4 | LogRecord, LogEnvelope, SchemaCatalog, utc_now_iso |
| **Input Ports** | 4 | Administrative, Consuming, LogContainerAdmin, LogContainerConsume |
| **Output Ports** | 8 | Managerial, LogContainerManage, AdapterRegistry, StateStore, OTel, Viewer, Previewer, Resource |
| **Services** | 5 | Logging, Configurator, ProviderCatalog, ProductionProfile, LogContainerModule |
| **Adapters** | 6 | OTel, NoOp, UnavailableOTel, Viewer, FileState, Registry |
| **Resolvers** | 3 | Writer, Dispatcher, ReadOnly |
| **Containers** | 2 | LevelContainers, SlotLifecycle |
| **Level API** | 7 | ELogLevel + 6 level classes |
| **Previewers** | 2 | Console, Web |
| **Resource Mgmt** | 2 | InMemory, ThreadPool |
| **Total** | **43** | |

---

## File Location

```
03.0020_LoggingSystem/00_Project_Management/00.01_KnowledgeGraph/
└── Architectural_Taxonomy.md
```

**Document Status:** Complete  
**Last Updated:** 2026-04-15
