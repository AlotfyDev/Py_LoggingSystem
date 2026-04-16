# 03 LoggingSystem MandatoryCore vs OptionalProfile Matrix

## Purpose
Lock architectural decisions before the next contract-freeze wave, using explicit component-by-component classification.

## Decision Baseline
- Use specialized pipelines where requested.
- Keep adapter-based communication boundaries.
- Separate preview/render concerns from core logging ingestion/dispatch concerns.
- Keep fail-closed governance for schema, policy, and boundary violations.

## Component Decision Matrix
| # | Component | Classification | Final Decision | Freeze Notes |
|---|---|---|---|---|
| 1 | Logger Previewer subsystem | optional_profile | accepted | Separate subsystem. Consumes logging outputs via ports and adapters only. |
| 2 | Console Previewer (displayer/formatter/mode_controller) | optional_profile | accepted | Keep split objects. No coupling to core emit/dispatch internals. |
| 3 | Web Previewer (API/WebSocket adapter profile) | optional_profile | accepted | Adapter profile, not mandatory core runtime requirement. |
| 4 | LogMessage Envelope (`message_id`, `schema_id`, `correlation_id`, `trace_id`, `span_id`) | mandatory_core | accepted | Envelope fields become strict schema-governed contract fields. |
| 5 | Content Schema + versioned catalog + emit-time validation | mandatory_core | accepted | Validation on emit is fail-closed and must be contract-enforced. |
| 6 | ILogContainers per level with configurable partition strategy (`by_level`, `by_tenant`, `hybrid`) | mandatory_core | accepted | Core supports multiple partition strategies through policy. |
| 7 | ILogContainerSlot lifecycle states | mandatory_core | accepted_with_scope | Canonical states: `NEW`, `WRITING`, `READY`, `DISPATCHING`, `DISPATCHED`, `FAILED`, `EVICTED`. Extended substates allowed only as profile metadata. |
| 8 | Notify/Listeners | mandatory_core | accepted | Listener failures must be isolated from write path. |
| 9 | Receivers Registry + Dispatcher | mandatory_core | accepted | Retry/ack policy required for dispatch plane contracts. |
| 10 | Resolver pipelines (writer/dispatcher/read-only) | mandatory_core | modified | Keep separate specialized resolver pipelines (no single shared ReferenceIndexService authority). |
| 11 | ILogger + LogLevelHandler | mandatory_core | modified | No mandatory generic `log()` API; use dedicated level pipelines with generic templated handler contracts. |
| 12 | LogLevel APIs (`LogError`, `LogDebug`, ...) | mandatory_core | modified | Keep direct specialized level entry points; do not require facade-over-generic `log()`. |
| 13 | `E_LogLevel` enum | mandatory_core | accepted | Freeze canonical ordering + stable string mapping. |
| 14 | Metadata (writer/default mode/eviction/schema/retention/privacy-redaction) | mandatory_core | accepted | Privacy/redaction and retention class are required policy fields. |
| 15 | Preview modes (`pop_single`, `collective`, `system_pause`) | optional_profile | accepted | Belongs to previewer subsystem, not logging core contracts. |

## Pipeline and Boundary Policy (Frozen for Next Contracts)
1. Core logging plane uses specialized pipelines per concern and per log-level container.
2. Resolver responsibilities remain separated by role domain:
   - writer resolution pipeline
   - dispatcher resolution pipeline
   - read-only resolution pipeline
3. Previewers consume through dedicated output/provider ports, never direct service internals.
4. Adapter boundary remains mandatory for external integrations.

## Gap Readiness Summary vs Current Implementation
- Present now:
  - core schema catalog + validation path
  - role-separated admin/manager/consumer ports
  - dispatch and adapter registry foundation
  - retention/eviction baseline
- Missing or under-modeled for next freeze:
  - explicit previewer subsystem contracts (console/web and modes)
  - explicit level-container and slot-lifecycle contract surfaces
  - explicit specialized resolver pipeline contracts as first-class components
  - explicit dedicated level API object contracts

## Contract Freeze Readiness Verdict
- Verdict: ready_for_contract_freeze_with_expansion
- Reason: architectural direction is now converged; missing items are explicit and scoped for contractization.

## OTel Integrated Profile Freeze Inputs
1. Require OTLP capabilities for `logs`, `metrics`, and `traces` in adapter contracts.
2. Freeze mandatory attributes: `service`, `subsystem`, `tenant`, `environment`, `level`, `correlation_id`, `trace_id`, `span_id`.
3. Freeze collector-unavailable fail-closed behavior with severity-aware queue/retry/drop policy.
4. Freeze signal-specific QoS policy (`logs=at_least_once`, `metrics=at_most_once`, `traces=at_most_once`).
5. Enforce no direct vendor SDK dependencies in core service layer (adapter scope only).
