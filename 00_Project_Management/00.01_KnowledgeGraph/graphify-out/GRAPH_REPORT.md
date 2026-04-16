# Graph Report - 03.0020_LoggingSystem  (2026-04-15)

## Corpus Check
- 401 files · ~89,682 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 922 nodes · 2176 edges · 21 communities detected
- Extraction: 61% EXTRACTED · 39% INFERRED · 0% AMBIGUOUS · INFERRED: 839 edges (avg confidence: 0.75)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]

## God Nodes (most connected - your core abstractions)
1. `LoggingService` - 157 edges
2. `run_cli()` - 70 edges
3. `AdministrativePort` - 51 edges
4. `_validate_identifier()` - 44 edges
5. `ThreadPoolResourceManagementClient` - 43 edges
6. `ManagerialPort` - 31 edges
7. `ProviderCatalogService` - 29 edges
8. `ThreadPoolResourceManagementBehaviorTests` - 29 edges
9. `InMemoryStateStore` - 28 edges
10. `LogContainerModuleService` - 25 edges

## Surprising Connections (you probably didn't know these)
- `LoggingService` --uses--> `AdapterRegistry`  [INFERRED]
  03.0020_LoggingSystem\03_DigitalTwin\logging_system_Obsolete\services\logging_service.py → 03.0020_LoggingSystem\03_DigitalTwin\logging_system_Obsolete\adapters\adapter_registry.py
- `LoggingServiceTests` --uses--> `AdapterRegistry`  [INFERRED]
  03.0020_LoggingSystem\03_DigitalTwin\logging_system_Obsolete\tests\test_logging_service.py → 03.0020_LoggingSystem\03_DigitalTwin\logging_system_Obsolete\adapters\adapter_registry.py
- `run_cli()` --calls--> `build_default_state_store()`  [INFERRED]
  03.0020_LoggingSystem\03_DigitalTwin\logging_system_Obsolete\cli\run_cli.py → 03.0020_LoggingSystem\03_DigitalTwin\logging_system_Obsolete\adapters\default_state_store_factory.py
- `FileStateStore` --uses--> `StateStorePort`  [INFERRED]
  03.0020_LoggingSystem\03_DigitalTwin\logging_system_Obsolete\adapters\file_state_store.py → 03.0020_LoggingSystem\03_DigitalTwin\logging_system_Obsolete\ports\state_store_port.py
- `LoggingServiceTests` --uses--> `FileStateStore`  [INFERRED]
  03.0020_LoggingSystem\03_DigitalTwin\logging_system_Obsolete\tests\test_logging_service.py → 03.0020_LoggingSystem\03_DigitalTwin\logging_system_Obsolete\adapters\file_state_store.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (16): AdministrativePort, ConsumingPort, LogContainerManagerialPort, LogWarn, Auto-generated stub from 03_DigitalTwin mapping., LoggingService, _sample_records(), ManagerialPort (+8 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (22): ConsumingPort, ELogLevel, Auto-generated stub from 03_DigitalTwin mapping., Enum, LogContainerAdministrativePort, LogContainerProviderPort, LogDebug, Auto-generated stub from 03_DigitalTwin mapping. (+14 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (11): ensure_identifier(), ensure_payload_mapping(), ensure_supported_config_type(), _copy_mapping(), _validate_identifier(), _validate_schema_payload(), ProviderCatalogEntryDTO, RetentionDTO (+3 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (30): InMemoryResourceManagementClient, str, Test that container lease requires container_backend_profile_id., Test retrieving execution profile., Test that getting invalid profile raises KeyError., Test that getting profile with empty ID raises ValueError., Test that dispatch tasks execute and return correct results., Test that task error raises RuntimeError and cancels pending tasks. (+22 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (44): AdapterBindingDTO, from_existing(), from_mapping(), adapter_binding_from_existing(), connection_catalog_entry_from_existing(), container_binding_from_existing(), execution_binding_from_existing(), persistence_catalog_entry_from_existing() (+36 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (14): apply_logging_viewer_specialization_profile_config(), build_logging_viewer_specialization_pack(), build_logging_viewer_specialization_profile_config(), _load_ovs_logging_specialization_module(), map_record_to_viewer_envelope_and_content(), register_logging_viewer_specialization_pack(), upsert_logging_viewer_specialization_profile_config(), ManagerialPort (+6 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (15): build_default_connection_entries(), build_default_persistence_entries(), build_default_provider_entries(), build_default_production_profiles(), LogContainerConsumingPort, ConnectionCatalogEntry, from_mapping(), PersistenceCatalogEntry (+7 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (12): AdapterRegistry, AdapterRegistryPort, build_default_adapter_registry(), NoOpAdapter, OpenTelemetryAdapter, OpenTelemetryAdapterPort, OpenTelemetryAdapterPort, AdapterBehaviorTests (+4 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (9): LevelContainers, Auto-generated stub from 03_DigitalTwin mapping., LogContainerModuleService, _parse_record_payload(), _parse_utc(), _serialize_record(), _normalize_slot_id(), Auto-generated stub from 03_DigitalTwin mapping. (+1 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (1): AdministrativePort

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (10): build_default_content_schema_catalog(), build_default_state_store(), FileStateStore, parse_json_object(), _parse_utc(), _validate_payload_against_schema(), _value_matches_type(), _add_log_payload_args() (+2 more)

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (16): DispatcherResolverPipeline, Auto-generated stub from 03_DigitalTwin mapping., parse(), _collect_symbols(), _group_key(), _line_for(), main(), _render_markdown() (+8 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (9): ConsolePreviewer, Auto-generated stub from 03_DigitalTwin mapping., LogEnvelope, _parse_record_payload(), LogRecord, LogEnvelopeBehaviorTests, LogRecordBehaviorTests, Auto-generated stub from 03_DigitalTwin mapping. (+1 more)

### Community 13 - "Community 13"
Cohesion: 0.33
Nodes (2): _project_root(), ValidatorGatesBehaviorTests

### Community 14 - "Community 14"
Cohesion: 0.42
Nodes (8): _ack_compatible(), _as_list(), _build_parser(), _entry_id_map(), _load_yaml(), main(), _utc_now(), Violation

### Community 15 - "Community 15"
Cohesion: 0.46
Nodes (7): _as_list(), _build_parser(), _load_yaml(), main(), _profile_map(), _utc_now(), Violation

### Community 16 - "Community 16"
Cohesion: 0.48
Nodes (2): Auto-generated stub from 03_DigitalTwin mapping., # TODO: replace with implementation.

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (0): 

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (0): 

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (0): 

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **15 isolated node(s):** `Auto-generated stub from 03_DigitalTwin mapping.`, `Auto-generated stub from 03_DigitalTwin mapping.`, `Auto-generated stub from 03_DigitalTwin mapping.`, `Auto-generated stub from 03_DigitalTwin mapping.`, `Auto-generated stub from 03_DigitalTwin mapping.` (+10 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 17`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LoggingService` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.532) - this node is a cross-community bridge._
- **Why does `AdministrativePort` connect `Community 9` to `Community 0`, `Community 1`, `Community 10`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Why does `run_cli()` connect `Community 2` to `Community 0`, `Community 3`, `Community 5`, `Community 7`, `Community 8`, `Community 10`, `Community 12`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Are the 54 inferred relationships involving `LoggingService` (e.g. with `AdapterRegistry` and `LevelContainers`) actually correct?**
  _`LoggingService` has 54 INFERRED edges - model-reasoned connections that need verification._
- **Are the 103 inferred relationships involving `str` (e.g. with `_build_parser()` and `main()`) actually correct?**
  _`str` has 103 INFERRED edges - model-reasoned connections that need verification._
- **Are the 68 inferred relationships involving `run_cli()` (e.g. with `build_parser()` and `LoggingService`) actually correct?**
  _`run_cli()` has 68 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `AdministrativePort` (e.g. with `LoggingService` and `PortsContractBehaviorTests`) actually correct?**
  _`AdministrativePort` has 2 INFERRED edges - model-reasoned connections that need verification._