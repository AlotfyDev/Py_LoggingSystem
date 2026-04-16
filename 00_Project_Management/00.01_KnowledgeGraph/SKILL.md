---
name: logging-system-graph
description: Knowledge graph exploration for LoggingSystem (03.0020) - Hexagonal Architecture with Ports & Adapters
trigger: /loggraph
---

# /loggraph - LoggingSystem Knowledge Graph

Knowledge graph for **LoggingSystem** (03.0020) - A complete observability subsystem following hexagonal architecture.

## Graph Statistics
- **Nodes:** 922
- **Edges:** 2,176  
- **Communities:** 21
- **Files:** 401 (169 code, 232 docs)

## System Architecture

```
LoggingSystem (Hexagonal Architecture)
├── Core
│   ├── LoggingService (157 connections) - Main service
│   ├── AdministrativePort (51 connections) - Schema management
│   ├── ManagerialPort (31 connections) - Policy/profile management
│   └── ConsumingPort - Log emission
│
├── Ports (13 total)
│   ├── Input Ports: Administrative, Managerial, Consuming
│   ├── Container Ports: LogContainer* (Admin, Manager, Consume, Provider)
│   └── Output Ports: OpenTelemetry, StateStore, AdapterRegistry, Viewer, Previewer
│
├── Adapters
│   ├── Telemetry: OpenTelemetryAdapter, NoOpAdapter, UnavailableOTelAdapter
│   ├── State: FileStateStore, InMemoryStateStore
│   └── Resource: InMemoryResourceManagement, ThreadPoolResourceManagement
│
├── Level API (6 log levels)
│   └── LogDebug, LogInfo, LogWarn, LogError, LogFatal, LogTrace
│
└── Specialization
    └── LoggingViewerSpecialization - Viewer integration
```

## God Nodes (Most Connected)

| Node | Edges | Purpose |
|------|-------|---------|
| `LoggingService` | 157 | Core service |
| `run_cli()` | 70 | CLI entry point |
| `AdministrativePort` | 51 | Schema CRUD |
| `_validate_identifier()` | 44 | Validation |
| `ThreadPoolResourceManagementClient` | 43 | Resource mgmt |
| `ManagerialPort` | 31 | Policy management |
| `ProviderCatalogService` | 29 | Catalog management |
| `InMemoryStateStore` | 28 | State persistence |
| `LogContainerModuleService` | 25 | Container lifecycle |

## Key Communities

| Community | Cohesion | Key Components |
|------------|----------|----------------|
| 0 | 0.04 | LoggingService, Ports, Level APIs |
| 1 | 0.03 | ConsumingPort, LogContainer ports, LogLevels |
| 2 | 0.06 | Validators, DTOs, ProviderCatalog |
| 3 | 0.05 | Resource Management, Tests |
| 4 | 0.05 | DTOs, Factory methods |
| 5 | 0.03 | Viewer Specialization |
| 6 | 0.05 | Catalog Entries, Production Profiles |
| 7 | 0.07 | AdapterRegistry, Adapters |
| 8 | 0.06 | LevelContainers, LogContainerModule |
| 10 | 0.07 | FileStateStore, Schema validation |
| 12 | 0.09 | LogRecord, LogEnvelope, Previewers |

## Recommended Queries

### Port-Adapter Pattern
```
/loggraph query "port adapter pattern"
```

### Service Dependencies
```
/loggraph query "LoggingService dependencies"
```

### Level API Structure
```
/loggraph query "level api debug info warn error"
```

### Container Module
```
/loggraph path "LevelContainers" "LogContainerModuleService"
```

### State Management
```
/loggraph path "StateStorePort" "LoggingService"
```

### Specialization
```
/loggraph explain "LoggingViewerSpecialization"
```

## How to Use This Graph

### 1. View the Report
Read `graphify-out/GRAPH_REPORT.md` for:
- God nodes (most connected abstractions)
- Surprising connections
- Community structure

### 2. Run Specific Queries

Query the graph:
```bash
python -m graphify query "your question" --graph graphify-out/graph.json
```

Find paths:
```bash
python -m graphify path "NodeA" "NodeB" --graph graphify-out/graph.json
```

Explain a node:
```bash
python -m graphify explain "NodeName" --graph graphify-out/graph.json
```

### 3. Explore Communities

Each community represents a coherent subsystem:
- **Community 0:** Core service and ports
- **Community 1:** Consumer interface and log levels
- **Community 7:** Adapter layer
- **Community 8:** Container management
- **Community 12:** Data models and previewers

## Integration with CentralLoggingSystem

```
LoggingSystem (Singular) ←→ CentralLoggingSystem (Central)

Singular: Owns data-plane + control-plane, injectable
Central: Control-plane only, multi-tenant governance
```

## Files

```
00_Project_Management/00.01_KnowledgeGraph/
├── SKILL.md                    ← This file
├── README.md                   ← Overview
├── graphify-out/
│   ├── graph.json             ← Raw graph data
│   ├── GRAPH_REPORT.md       ← Full report
│   └── .graphify_*.json     ← Extraction cache
└── queries/
    └── (custom query scripts)
```

## Related Documentation

- `01_Architecture/` - System architecture
- `02_Contracts/` - Port contracts (YAML)
- `03_DigitalTwin/logging_system/` - Implementation
- `00_Project_Management/00.02_ArchitecturalDesign/` - Full design docs
