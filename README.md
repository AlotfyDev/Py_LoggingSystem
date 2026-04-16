# LoggingSystem

## Purpose
Portable injectable subsystem for logging with strict contracts-first governance.

## Contract-first scope
- Freeze top generic templated types/functions layer.
- Freeze role-separated API surfaces: administrative, managerial, consuming.
- Freeze OpenTelemetry integration boundary through adapters/ports.
- Freeze specialized pipelines, slot lifecycle, resolver pipelines, and dedicated level APIs.
- Freeze independent `LogContainerModule` boundary and injected provider-port consumption.
- Freeze `ResourceManagementClient` lease-binding model for container assignment.
- Freeze provider/connection/persistence catalogs for capability-conformant backend selection.
- Freeze CLI command surface synchronized with contracts wave `08..12`.

## Dependency policy
- No peer-internal dependency. Provider-port dependency only.
- Fail-closed when mandatory ports or schema bindings are missing.

## CLI command groups
- Baseline: `status`, `list-adapters`, `evidence`, `query`, `emit`, `bind-adapter`, `bind-container-assignment`, `unbind-container-assignment`, `container-assignment-status`, `dispatch`, `safepoint`
- Dedicated level APIs: `log-debug`, `log-info`, `log-warn`, `log-error`, `log-fatal`, `log-trace`
- Schema catalog CRUD: `schema-list`, `schema-get`, `schema-create`, `schema-update`, `schema-delete`
- Policy CRUD: `policy-list`, `policy-get`, `policy-create`, `policy-update`, `policy-delete`
- Runtime profile CRUD: `profile-list`, `profile-get`, `profile-create`, `profile-update`, `profile-delete`
- Specialized policy setup:
  - `set-dispatch-failure-policy`
  - `set-signal-qos-profile`
  - `set-mandatory-label-schema`
  - `set-slot-lifecycle-policy`
  - `set-level-container-policy`
  - `set-resolver-pipeline-policy`
  - `set-previewer-profile`
  - `set-loglevel-api-policy`
- Preview commands:
  - `preview-console`
  - `preview-web`
- Typed configuration supports: `schema`, `policy`, `retention`, `previewer_profile`, `adapter_binding`, `container_binding`
- Catalog governance supports:
  - log container provider catalog
  - connections catalog
  - persistence catalog
