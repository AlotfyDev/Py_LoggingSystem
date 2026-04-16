# 00.01_KnowledgeGraph - LoggingSystem Knowledge Graph

**Version:** 1.0  
**Date:** 2026-04-15  
**Parent System:** 03.0020_LoggingSystem  
**Purpose:** Modular knowledge graph for LoggingSystem exploration

---

## Overview

This directory contains a self-contained knowledge graph for the LoggingSystem subsystem. It provides:

- **Persistent structure** - Relationships survive across sessions
- **Audit trail** - EXTRACTED/INFERRED confidence tags
- **Community detection** - Automatically groups related concepts
- **Queryable** - Answer questions without re-reading all files

## Quick Start

### View the Graph Report
```
graphify-out/GRAPH_REPORT.md
```

### Run a Query
```bash
python -m graphify query "port adapter pattern" --graph graphify-out/graph.json
```

### Find a Path
```bash
python -m graphify path "LoggingService" "StateStorePort" --graph graphify-out/graph.json
```

### Explain a Node
```bash
python -m graphify explain "AdministrativePort" --graph graphify-out/graph.json
```

## Graph Statistics

| Metric | Value |
|--------|-------|
| Files Processed | 401 |
| Code Files | 169 |
| Documentation | 232 |
| Graph Nodes | 922 |
| Graph Edges | 2,176 |
| Communities | 21 |
| Extraction Ratio | 61% EXTRACTED / 39% INFERRED |

## God Nodes (Top 10)

| Rank | Node | Edges | Purpose |
|------|------|-------|---------|
| 1 | `LoggingService` | 157 | Core service |
| 2 | `run_cli()` | 70 | CLI entry point |
| 3 | `AdministrativePort` | 51 | Schema management |
| 4 | `_validate_identifier()` | 44 | Validation |
| 5 | `ThreadPoolResourceManagementClient` | 43 | Resource management |
| 6 | `ManagerialPort` | 31 | Policy management |
| 7 | `ProviderCatalogService` | 29 | Catalog management |
| 8 | `InMemoryStateStore` | 28 | State persistence |
| 9 | `LogContainerModuleService` | 25 | Container lifecycle |
| 10 | `ConsolePreviewer` | 22 | Console output |

## Directory Structure

```
00.01_KnowledgeGraph/
├── SKILL.md                      # Skill definition for AI assistants
├── README.md                     # This file
├── graphify-out/
│   ├── graph.json               # Raw graph (NetworkX JSON)
│   ├── GRAPH_REPORT.md          # Full analysis report
│   ├── .graphify_ast.json       # AST extraction cache
│   └── .graphify_detect.json    # File detection cache
└── queries/                     # Custom query scripts (optional)
```

## Community Map

| Community | Cohesion | Key Components |
|-----------|----------|----------------|
| 0 | 0.04 | LoggingService, AdministrativePort, ManagerialPort, ConsumingPort |
| 1 | 0.03 | LogContainer*Ports, LogDebug/Info/Warn/Error/Fatal/Trace |
| 2 | 0.06 | Validators, ProviderCatalog, DTOs |
| 3 | 0.05 | InMemoryResourceManagementClient, Tests |
| 4 | 0.05 | All DTOs, Factory methods |
| 5 | 0.03 | LoggingViewerSpecialization |
| 6 | 0.05 | Catalog Entries, Production Profiles |
| 7 | 0.07 | AdapterRegistry, OpenTelemetryAdapter, NoOpAdapter |
| 8 | 0.06 | LevelContainers, LogContainerModuleService |
| 9 | 0.04 | AdministrativePort (isolated) |
| 10 | 0.07 | FileStateStore, Schema validation |
| 11 | 0.07 | DispatcherResolverPipeline |
| 12 | 0.09 | LogRecord, LogEnvelope, Previewers |

## Architecture Context

LoggingSystem follows **Hexagonal Architecture (Ports & Adapters)**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        LoggingSystem                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    03_DigitalTwin/                         │   │
│  │                                                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ models/  │  │  ports/  │  │ services/│            │   │
│  │  └──────────┘  └──────────┘  └──────────┘            │   │
│  │       │              │             │                      │   │
│  │       └──────────────┴─────────────┘                      │   │
│  │                      │                                    │   │
│  │                      ▼                                    │   │
│  │              ┌────────────────┐                        │   │
│  │              │ LoggingService │  ◄── CORE             │   │
│  │              └────────────────┘                        │   │
│  │                                                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │adapters/ │  │   cli/   │  │  tests/  │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘            │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Related Systems

| System | Relationship |
|--------|--------------|
| CentralLoggingSystem | Peer-central pattern |
| TracerSystem | Shared pattern (reuses Logging patterns) |
| MetricsSystem | Shared pattern |
| HealthCheckerSystem | Shared pattern |
| ObservabilitySystem | Unified facade |

## Updating the Graph

When code changes:
```bash
python -m graphify . --update
```

When adding new documentation:
```bash
python -m graphify . --update
```

## Known Gaps

- 15 isolated nodes with ≤1 connection
- Communities 17-20 have 0 nodes (empty clusters)

---

**Document Status:** Complete  
**Last Updated:** 2026-04-15
