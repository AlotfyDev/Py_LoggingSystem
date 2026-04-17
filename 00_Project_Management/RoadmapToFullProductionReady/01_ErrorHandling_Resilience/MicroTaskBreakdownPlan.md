# Micro-Task Breakdown Plan (MBTB)
## Area: Error Handling & Resilience

**Document Version:** 1.0  
**Created:** 2026-04-17  
**Status:** PLANNING  

---

## 1. Document Purpose

This document serves as a **blueprint** for granular, modular implementation of the Error Handling & Resilience area. It transforms high-level phases into traceable, testable, and recoverable micro-tasks.

---

## 2. Design Principles

| Principle | Description |
|-----------|-------------|
| **Granularity** | Tasks are small enough to complete in 2-4 hours |
| **Modularity** | Each task produces a complete, testable artifact |
| **Traceability** | Every task has clear acceptance criteria |
| **Recoverability** | Each task can be validated independently |
| **Sequential** | No parallel work - single focus per iteration |

---

## 3. Task Classification Schema

### 3.1 Task Types

```
TASK_TYPE
├── TYPE-A: Foundation (No dependencies)
│   └── Pure implementation, no external dependencies
│
├── TYPE-B: Contract (Depends on TYPE-A)
│   └── Interface/Protocol definition
│
├── TYPE-C: Implementation (Depends on TYPE-A, TYPE-B)
│   └── Concrete implementation of contracts
│
├── TYPE-D: Integration (Depends on TYPE-B, TYPE-C)
│   └── Wiring components together
│
└── TYPE-E: Validation (Depends on TYPE-D)
    └── Tests, benchmarks, verification
```

### 3.2 Task Metadata Schema

```yaml
task_id: ERR-FND-001
task_name: "Define Error Classification Hierarchy"
task_type: TYPE-A  # Foundation

description: |
  Define the complete error classification system including:
  - EErrorCategory enum
  - ERetryableError enum  
  - ELogErrorCode enum
  - ErrorContext dataclass

dependencies:
  - []  # No dependencies - TYPE-A

acceptance_criteria:
  - [ ] EErrorCategory contains: TRANSIENT, PERMANENT, PARTIAL
  - [ ] ERetryableError contains network, timeout, service errors
  - [ ] ELogErrorCode covers all system error scenarios
  - [ ] ErrorContext is frozen dataclass
  - [ ] ErrorContext.is_retryable() returns correct boolean
  - [ ] Unit tests pass for all enum values
  - [ ] Type hints are complete and correct

test_requirements:
  - test_error_category_values
  - test_retryable_error_coverage
  - test_error_context_frozen
  - test_is_retryable_logic

implementation_notes:
  - Location: logging_system/errors/error_hierarchy.py
  - Export from: logging_system/errors/__init__.py
  - No runtime dependencies

estimated_effort:
  - LOC: ~100
  - Hours: 2-3
  - Complexity: LOW

risk_level: LOW

validation_checklist:
  - [ ] Code compiles without errors
  - [ ] All type hints pass mypy
  - [ ] Unit tests pass (100%)
  - [ ] No hardcoded values
  - [ ] Error messages are descriptive
```

---

## 4. Dependency Graph Schema

### 4.1 Dependency Types

```
DEPENDENCY_TYPE
├── D-IMPL: Implementation Dependency
│   └── Task B cannot start without Task A implementation
│
├── D-CONTRACT: Contract Dependency
│   └── Task B cannot start without Task A contract definition
│
├── D-TEST: Test Dependency
│   └── Task B tests cannot pass without Task A
│
└── D-INTEGRATION: Integration Dependency
    └── Task B integrates with Task A
```

### 4.2 Dependency Graph Format

```yaml
dependency_graph:
  task_id: ERR-FND-001
  depends_on: []
  depended_by:
    - task_id: ERR-RTY-001
      dependency_type: D-IMPL
      reason: "Result types use ErrorContext"
    - task_id: ERR-CB-001
      dependency_type: D-CONTRACT
      reason: "Circuit breaker uses EErrorCategory"
    - task_id: ERR-DLQ-001
      dependency_type: D-CONTRACT
      reason: "DLQ uses ErrorContext for error tracking"
```

---

## 5. Phase Breakdown Templates

### 5.1 Phase Template

```yaml
phase:
  id: PHASE-1
  name: "Foundation Layer"
  description: "Core error types and result patterns"
  
  task_order: SEQUENTIAL  # All tasks in order
  
  tasks:
    - task_id: ...
    - task_id: ...
    - task_id: ...
  
  phase_acceptance:
    - "All TYPE-A tasks complete"
    - "All TYPE-B contracts defined"
    - "Integration tests pass"
    - "No breaking changes to existing code"
  
  exit_criteria:
    - [ ] All tasks in phase complete
    - [ ] All acceptance criteria met
    - [ ] Phase tests pass
    - [ ] Documentation updated
```

---

## 6. Current ImplementationPlan Structure

### 6.1 Existing Phases

| Phase | Name | Tasks | Dependencies |
|-------|------|-------|--------------|
| Phase 1 | Foundation Layer | 2 | None |
| Phase 2 | Circuit Breaker | 3 | Phase 1 |
| Phase 3 | Retry Mechanisms | 3 | Phase 1, Phase 2 |
| Phase 4 | Dead Letter Queue | 3 | Phase 1, 2, 3 |
| Phase 5 | Integration | 1 | All |

**Total: 12 high-level tasks**

### 6.2 Current → Micro-Task Transformation

```
Phase 1: Foundation Layer
├── 1.1 → ERR-FND-001: Define Error Hierarchy
├── 1.1 → ERR-FND-002: Implement ErrorContext
├── 1.2 → ERR-FND-003: Define Result Type Base
└── 1.2 → ERR-FND-004: Implement Result Operations

Phase 2: Circuit Breaker
├── 2.1 → ERR-CB-001: Define Circuit Breaker States
├── 2.1 → ERR-CB-002: Implement Circuit Breaker Config
├── 2.2 → ERR-CB-003: Implement Circuit Breaker Core
├── 2.2 → ERR-CB-004: Implement Circuit Breaker Registry
└── 2.2 → ERR-CB-005: Add Circuit Breaker Metrics

Phase 3: Retry Mechanisms
├── 3.1 → ERR-RT-001: Define Retry Strategies
├── 3.1 → ERR-RT-002: Implement Backoff Calculator
├── 3.2 → ERR-RT-003: Implement Retry Config
├── 3.3 → ERR-RT-004: Implement Retry Executor Core
└── 3.3 → ERR-RT-005: Implement Cancellation Support

Phase 4: Dead Letter Queue
├── 4.1 → ERR-DLQ-001: Define DLQ Contract
├── 4.1 → ERR-DLQ-002: Define DLQ Config
├── 4.2 → ERR-DLQ-003: Implement In-Memory DLQ
├── 4.2 → ERR-DLQ-004: Implement File-Based DLQ
└── 4.2 → ERR-DLQ-005: Implement DLQ Persistence

Phase 5: Integration
├── 5.1 → ERR-INT-001: Integrate Circuit Breaker
├── 5.1 → ERR-INT-002: Integrate DLQ
├── 5.1 → ERR-INT-003: Add Retry to Dispatch
└── 5.1 → ERR-INT-004: End-to-End Tests

TOTAL: 22 micro-tasks
```

---

## 7. Detailed Micro-Task Inventory

### 7.1 Phase 1: Foundation Layer

#### ERR-FND-001: Define Error Classification Hierarchy

```yaml
task_id: ERR-FND-001
task_name: "Define Error Classification Hierarchy"
task_type: TYPE-A (Foundation)
phase: PHASE-1
order: 1

description: |
  Define the complete error classification system as described in 
  ImplementationPlan.md Phase 1.1.1
  
  Includes:
  - EErrorCategory enum (TRANSIENT, PERMANENT, PARTIAL)
  - ERetryableError enum (NETWORK, TIMEOUT, SERVICE_UNAVAILABLE, etc.)
  - ELogErrorCode enum (all system error codes)
  
deliverables:
  - File: logging_system/errors/error_hierarchy.py
  - Exports: EErrorCategory, ERetryableError, ELogErrorCode

dependencies: []

acceptance_criteria:
  - [ ] EErrorCategory contains exactly: TRANSIENT, PERMANENT, PARTIAL
  - [ ] ERetryableError covers all retryable error types
  - [ ] ELogErrorCode covers adapter, schema, binding, queue errors
  - [ ] All enums have string values for serialization
  - [ ] Documentation strings for each enum value
  - [ ] Unit tests for all enum values

test_requirements:
  - test_error_category_enum_values
  - test_retryable_error_enum_values
  - test_log_error_code_enum_values
  - test_enum_string_serialization

estimated_effort:
  hours: 1-2
  loc: 80-100

risk_level: LOW

implementation_notes: |
  - Use @enum.unique decorator
  - All enums inherit from str and Enum
  - Add docstrings to each enum and value
```

#### ERR-FND-002: Implement ErrorContext Dataclass

```yaml
task_id: ERR-FND-002
task_name: "Implement ErrorContext Dataclass"
task_type: TYPE-A (Foundation)
phase: PHASE-1
order: 2

description: |
  Implement ErrorContext frozen dataclass for error metadata tracking.
  
deliverables:
  - File: logging_system/errors/error_hierarchy.py (extends ERR-FND-001)

dependencies:
  - ERR-FND-001

acceptance_criteria:
  - [ ] ErrorContext is @dataclass(frozen=True)
  - [ ] Contains: timestamp_utc, error_code, category, retryable, metadata, original_error, stack_trace
  - [ ] is_retryable() method works correctly
  - [ ] Can serialize to dict
  - [ ] Rejects None for required fields
  - [ ] Unit tests pass

test_requirements:
  - test_error_context_creation
  - test_error_context_frozen
  - test_is_retryable_transient
  - test_is_retryable_permanent
  - test_error_context_to_dict

estimated_effort:
  hours: 1-2
  loc: 60-80

risk_level: LOW
```

#### ERR-FND-003: Define Result Type Base

```yaml
task_id: ERR-FND-003
task_name: "Define Result Type Base"
task_type: TYPE-B (Contract)
phase: PHASE-1
order: 3

description: |
  Define the Result type pattern for explicit error handling.
  Based on ImplementationPlan.md Phase 1.1.2.
  
deliverables:
  - File: logging_system/errors/result.py

dependencies:
  - ERR-FND-001
  - ERR-FND-002

acceptance_criteria:
  - [ ] Success[T] dataclass with value property
  - [ ] ErrorResult dataclass with code, message, context
  - [ ] Result = Success[T] | ErrorResult union type
  - [ ] ErrorResult.__bool__() returns False
  - [ ] Type hints complete for Success.value
  - [ ] Unit tests for type behavior

test_requirements:
  - test_success_creation
  - test_error_result_creation
  - test_result_bool_success
  - test_result_bool_error
  - test_result_type_hints

estimated_effort:
  hours: 2-3
  loc: 100-120

risk_level: LOW
```

#### ERR-FND-004: Implement Result Operations

```yaml
task_id: ERR-FND-004
task_name: "Implement Result Operations"
task_type: TYPE-C (Implementation)
phase: PHASE-1
order: 4

description: |
  Implement ResultOps utility class for Result type manipulation.
  
deliverables:
  - File: logging_system/errors/result.py (extends ERR-FND-003)

dependencies:
  - ERR-FND-003

acceptance_criteria:
  - [ ] ResultOps.ok(value) returns Success
  - [ ] ResultOps.err(code, message) returns ErrorResult
  - [ ] ResultOps.err with context works
  - [ ] bind() function chains Results correctly
  - [ ] map() transforms Success values
  - [ ] or_else() provides fallback
  - [ ] All operations have type hints
  - [ ] Unit tests pass

test_requirements:
  - test_result_ops_ok
  - test_result_ops_err
  - test_result_ops_bind_success
  - test_result_ops_bind_error
  - test_result_ops_map
  - test_result_ops_or_else

estimated_effort:
  hours: 2-3
  loc: 120-150

risk_level: LOW

implementation_notes: |
  - Follow functional programming patterns
  - Preserve type information through bind/map
  - Error propagation should preserve original context
```

### 7.2 Phase 2: Circuit Breaker

#### ERR-CB-001: Define Circuit Breaker States

```yaml
task_id: ERR-CB-001
task_name: "Define Circuit Breaker States"
task_type: TYPE-B (Contract)
phase: PHASE-2
order: 1

description: |
  Define CircuitBreaker state machine types.
  
deliverables:
  - File: logging_system/errors/circuit_breaker.py

dependencies:
  - ERR-FND-001  # Uses EErrorCategory

acceptance_criteria:
  - [ ] ECircuitState enum: CLOSED, OPEN, HALF_OPEN
  - [ ] CircuitBreakerConfig dataclass
  - [ ] CircuitBreakerMetrics dataclass
  - [ ] CircuitBreakerOpenError exception class
  - [ ] All types documented

test_requirements:
  - test_circuit_state_enum
  - test_circuit_config_defaults
  - test_circuit_metrics_defaults

estimated_effort:
  hours: 1-2
  loc: 80-100

risk_level: LOW
```

#### ERR-CB-002: Implement Circuit Breaker Config

```yaml
task_id: ERR-CB-002
task_name: "Implement Circuit Breaker Config"
task_type: TYPE-C (Implementation)
phase: PHASE-2
order: 2

description: |
  Implement CircuitBreakerConfig validation and defaults.
  
deliverables:
  - File: logging_system/errors/circuit_breaker.py (extends ERR-CB-001)

dependencies:
  - ERR-CB-001

acceptance_criteria:
  - [ ] Config validates failure_threshold > 0
  - [ ] Config validates success_threshold > 0
  - [ ] Config validates open_timeout_seconds > 0
  - [ ] Default values are sensible
  - [ ] Config is frozen

test_requirements:
  - test_circuit_config_validation
  - test_circuit_config_defaults
  - test_circuit_config_mutable_fails

estimated_effort:
  hours: 1-2
  loc: 60-80

risk_level: LOW
```

#### ERR-CB-003: Implement Circuit Breaker Core

```yaml
task_id: ERR-CB-003
task_name: "Implement Circuit Breaker Core"
task_type: TYPE-C (Implementation)
phase: PHASE-2
order: 3

description: |
  Implement CircuitBreaker class with state machine.
  This is the CORE implementation.
  
deliverables:
  - File: logging_system/errors/circuit_breaker.py (extends ERR-CB-002)

dependencies:
  - ERR-CB-002
  - ERR-FND-002  # Uses ErrorContext

acceptance_criteria:
  - [ ] CLOSED → OPEN after failure_threshold consecutive failures
  - [ ] OPEN → HALF_OPEN after open_timeout_seconds
  - [ ] HALF_OPEN → CLOSED after success_threshold successes
  - [ ] HALF_OPEN → OPEN on any failure
  - [ ] All state transitions are thread-safe
  - [ ] Metrics are updated on each transition
  - [ ] call() raises CircuitBreakerOpenError when OPEN
  - [ ] Sliding window tracks recent failures

test_requirements:
  - test_cb_closed_to_open
  - test_cb_open_to_half_open
  - test_cb_half_open_to_closed
  - test_cb_half_open_to_open
  - test_cb_call_when_open_raises
  - test_cb_sliding_window
  - test_cb_thread_safety
  - test_cb_metrics_updated

estimated_effort:
  hours: 4-6
  loc: 250-300

risk_level: MEDIUM

validation_checklist:
  - [ ] State machine diagram matches implementation
  - [ ] All edge cases tested
  - [ ] Thread safety verified under concurrent load
```

#### ERR-CB-004: Implement Circuit Breaker Registry

```yaml
task_id: ERR-CB-004
task_name: "Implement Circuit Breaker Registry"
task_type: TYPE-C (Implementation)
phase: PHASE-2
order: 4

description: |
  Implement per-adapter circuit breaker registry.
  
deliverables:
  - File: logging_system/errors/circuit_breaker_registry.py

dependencies:
  - ERR-CB-003

acceptance_criteria:
  - [ ] Registry creates breakers on demand
  - [ ] Registry returns existing breakers
  - [ ] is_available() returns False when OPEN
  - [ ] list_all_states() shows all breakers
  - [ ] Thread-safe operations
  - [ ] Default config for new breakers

test_requirements:
  - test_registry_creates_on_demand
  - test_registry_returns_existing
  - test_registry_is_available
  - test_registry_list_states

estimated_effort:
  hours: 2-3
  loc: 100-120

risk_level: LOW
```

#### ERR-CB-005: Add Circuit Breaker Metrics

```yaml
task_id: ERR-CB-005
task_name: "Add Circuit Breaker Metrics"
task_type: TYPE-D (Enhancement)
phase: PHASE-2
order: 5

description: |
  Enhance CircuitBreaker with comprehensive metrics.
  
deliverables:
  - File: logging_system/errors/circuit_breaker.py (extends ERR-CB-003)

dependencies:
  - ERR-CB-003

acceptance_criteria:
  - [ ] Track total_calls, successful_calls, failed_calls
  - [ ] Track rejected_calls when OPEN
  - [ ] Track last_failure_time, last_success_time
  - [ ] Track state_transitions count
  - [ ] Metrics are read-only snapshot
  - [ ] Serializes to dict

test_requirements:
  - test_metrics_tracking
  - test_metrics_serialization

estimated_effort:
  hours: 1-2
  loc: 60-80

risk_level: LOW
```

### 7.3 Phase 3: Retry Mechanisms

#### ERR-RT-001: Define Retry Strategies

```yaml
task_id: ERR-RT-001
task_name: "Define Retry Strategies"
task_type: TYPE-B (Contract)
phase: PHASE-3
order: 1

description: |
  Define retry strategy types and configuration.
  
deliverables:
  - File: logging_system/errors/retry_policy.py

dependencies:
  - ERR-FND-001  # Uses EErrorCategory

acceptance_criteria:
  - [ ] ERetryStrategy enum: IMMEDIATE, LINEAR, EXPONENTIAL, FIBONACCI
  - [ ] EJitterMode enum: NONE, FULL, DECORRELATED
  - [ ] RetryConfig dataclass with all fields
  - [ ] RetryAttempt dataclass
  - [ ] RetryBudget dataclass
  - [ ] All types documented

test_requirements:
  - test_retry_strategy_enum
  - test_jitter_mode_enum
  - test_retry_config_defaults

estimated_effort:
  hours: 1-2
  loc: 80-100

risk_level: LOW
```

#### ERR-RT-002: Implement Backoff Calculator

```yaml
task_id: ERR-RT-002
task_name: "Implement Backoff Calculator"
task_type: TYPE-C (Implementation)
phase: PHASE-3
order: 2

description: |
  Implement backoff calculation with jitter.
  
deliverables:
  - File: logging_system/errors/backoff_calculator.py

dependencies:
  - ERR-RT-001

acceptance_criteria:
  - [ ] IMMEDIATE returns 0 for all attempts
  - [ ] LINEAR returns initial_delay * attempt
  - [ ] EXPONENTIAL returns initial_delay * 2^(attempt-1)
  - [ ] FIBONACCI returns initial_delay * fib(attempt)
  - [ ] FULL jitter multiplies by (0.5 + random)
  - [ ] DECORRELATED jitter decreases slowly
  - [ ] Respects max_delay_seconds cap
  - [ ] Unit tests for each strategy

test_requirements:
  - test_backoff_immediate
  - test_backoff_linear
  - test_backoff_exponential
  - test_backoff_fibonacci
  - test_backoff_jitter_none
  - test_backoff_jitter_full
  - test_backoff_jitter_decorrelated
  - test_backoff_max_delay_cap

estimated_effort:
  hours: 2-3
  loc: 120-150

risk_level: LOW
```

#### ERR-RT-003: Implement Retry Config

```yaml
task_id: ERR-RT-003
task_name: "Implement Retry Config"
task_type: TYPE-C (Implementation)
phase: PHASE-3
order: 3

description: |
  Implement RetryConfig validation and helpers.
  
deliverables:
  - File: logging_system/errors/retry_policy.py (extends ERR-RT-001)

dependencies:
  - ERR-RT-001

acceptance_criteria:
  - [ ] Config validates max_attempts >= 1
  - [ ] Config validates initial_delay >= 0
  - [ ] Config validates timeout if set
  - [ ] Default values are sensible
  - [ ] Frozen dataclass

test_requirements:
  - test_retry_config_validation
  - test_retry_config_defaults

estimated_effort:
  hours: 1-2
  loc: 60-80

risk_level: LOW
```

#### ERR-RT-004: Implement Retry Executor Core

```yaml
task_id: ERR-RT-004
task_name: "Implement Retry Executor Core"
task_type: TYPE-C (Implementation)
phase: PHASE-3
order: 4

description: |
  Implement RetryExecutor with backoff.
  This is the CORE implementation.
  
deliverables:
  - File: logging_system/errors/retry_executor.py

dependencies:
  - ERR-RT-002  # Uses BackoffCalculator
  - ERR-RT-003  # Uses RetryConfig
  - ERR-CB-003  # Can use CircuitBreaker

acceptance_criteria:
  - [ ] execute() retries failed operations
  - [ ] Respects max_attempts limit
  - [ ] Applies correct backoff delay
  - [ ] Records attempt history in budget
  - [ ] Returns Result type (Success or ErrorResult)
  - [ ] Handles non-retryable errors
  - [ ] Respects timeout if configured

test_requirements:
  - test_retry_success_first_attempt
  - test_retry_success_after_retries
  - test_retry_max_attempts_exceeded
  - test_retry_non_retryable_error
  - test_retry_timeout
  - test_retry_budget_tracking
  - test_retry_with_circuit_breaker

estimated_effort:
  hours: 4-6
  loc: 300-350

risk_level: MEDIUM

validation_checklist:
  - [ ] Retry count matches expected
  - [ ] Delay between retries matches backoff
  - [ ] Budget reflects all attempts
  - [ ] Error propagation correct
```

#### ERR-RT-005: Implement Cancellation Support

```yaml
task_id: ERR-RT-005
task_name: "Implement Cancellation Support"
task_type: TYPE-C (Implementation)
phase: PHASE-3
order: 5

description: |
  Add cancellation token support to RetryExecutor.
  
deliverables:
  - File: logging_system/errors/retry_executor.py (extends ERR-RT-004)

dependencies:
  - ERR-RT-004

acceptance_criteria:
  - [ ] CancellationEvent parameter in execute()
  - [ ] Checks cancellation before each attempt
  - [ ] Returns cancelled error result when cancelled
  - [ ] Clean abort without partial state

test_requirements:
  - test_retry_cancellation_mid_retry
  - test_retry_no_cancellation

estimated_effort:
  hours: 1-2
  loc: 50-70

risk_level: LOW
```

### 7.4 Phase 4: Dead Letter Queue

#### ERR-DLQ-001: Define DLQ Contract

```yaml
task_id: ERR-DLQ-001
task_name: "Define DLQ Contract"
task_type: TYPE-B (Contract)
phase: PHASE-4
order: 1

description: |
  Define DLQ interface and types.
  
deliverables:
  - File: logging_system/errors/dlq_contract.py

dependencies:
  - ERR-FND-002  # Uses ErrorContext

acceptance_criteria:
  - [ ] EDLQStatus enum: PENDING, RETRYING, FAILED, EXPIRED, DISCARDED
  - [ ] DLQEntry dataclass
  - [ ] DLQConfig dataclass
  - [ ] DLQStatistics dataclass
  - [ ] IDeadLetterQueue Protocol interface

test_requirements:
  - test_dlq_status_enum
  - test_dlq_entry_creation
  - test_dlq_config_defaults

estimated_effort:
  hours: 2-3
  loc: 150-180

risk_level: LOW
```

#### ERR-DLQ-002: Define DLQ Config

```yaml
task_id: ERR-DLQ-002
task_name: "Define DLQ Config"
task_type: TYPE-C (Implementation)
phase: PHASE-4
order: 2

description: |
  Implement DLQ configuration validation.
  
deliverables:
  - File: logging_system/errors/dlq_contract.py (extends ERR-DLQ-001)

dependencies:
  - ERR-DLQ-001

acceptance_criteria:
  - [ ] Config validates max_entries >= 0
  - [ ] Config validates max_attempts >= 1
  - [ ] Config validates retry_delay > 0
  - [ ] Config validates expiration > 0
  - [ ] Frozen dataclass

test_requirements:
  - test_dlq_config_validation
  - test_dlq_config_defaults

estimated_effort:
  hours: 1-2
  loc: 60-80

risk_level: LOW
```

#### ERR-DLQ-003: Implement In-Memory DLQ

```yaml
task_id: ERR-DLQ-003
task_name: "Implement In-Memory DLQ"
task_type: TYPE-C (Implementation)
phase: PHASE-4
order: 3

description: |
  Implement IDeadLetterQueue with in-memory storage.
  
deliverables:
  - File: logging_system/errors/in_memory_dlq.py

dependencies:
  - ERR-DLQ-001  # Implements IDeadLetterQueue
  - ERR-DLQ-002  # Uses DLQConfig

acceptance_criteria:
  - [ ] enqueue() adds entry to DLQ
  - [ ] dequeue() returns oldest pending entry
  - [ ] mark_retrying() updates attempt count
  - [ ] mark_failed() sets FAILED status
  - [ ] mark_discarded() sets DISCARDED status
  - [ ] list_by_status() returns filtered entries
  - [ ] get_statistics() returns correct counts
  - [ ] Thread-safe operations
  - [ ] Respects max_entries limit

test_requirements:
  - test_dlq_enqueue_dequeue
  - test_dlq_mark_retrying
  - test_dlq_mark_failed
  - test_dlq_mark_discarded
  - test_dlq_list_by_status
  - test_dlq_statistics
  - test_dlq_max_entries_eviction
  - test_dlq_thread_safety

estimated_effort:
  hours: 4-6
  loc: 300-350

risk_level: MEDIUM
```

#### ERR-DLQ-004: Implement File-Based DLQ

```yaml
task_id: ERR-DLQ-004
task_name: "Implement File-Based DLQ"
task_type: TYPE-C (Implementation)
phase: PHASE-4
order: 4

description: |
  Implement persistent DLQ with file storage.
  
deliverables:
  - File: logging_system/errors/file_based_dlq.py

dependencies:
  - ERR-DLQ-003  # Extends InMemoryDLQ behavior

acceptance_criteria:
  - [ ] Inherits all InMemoryDLQ behavior
  - [ ] Writes to file on every change
  - [ ] Loads state on initialization
  - [ ] Handles corrupted file gracefully
  - [ ] purge_expired() removes old entries
  - [ ] retry_entry() resets failed entry

test_requirements:
  - test_dlq_persistence_roundtrip
  - test_dlq_corrupted_file_handling
  - test_dlq_purge_expired
  - test_dlq_retry_entry

estimated_effort:
  hours: 3-4
  loc: 200-250

risk_level: MEDIUM
```

#### ERR-DLQ-005: Implement DLQ Persistence

```yaml
task_id: ERR-DLQ-005
task_name: "Implement DLQ Persistence"
task_type: TYPE-D (Enhancement)
phase: PHASE-4
order: 5

description: |
  Add advanced persistence features to DLQ.
  
deliverables:
  - File: logging_system/errors/file_based_dlq.py (extends ERR-DLQ-004)

dependencies:
  - ERR-DLQ-004

acceptance_criteria:
  - [ ] Atomic writes (write to temp, rename)
  - [ ] Backup before write
  - [ ] Recovery from backup on corruption
  - [ ] Batch write optimization

test_requirements:
  - test_dlq_atomic_write
  - test_dlq_backup_recovery

estimated_effort:
  hours: 2-3
  loc: 100-150

risk_level: LOW
```

### 7.5 Phase 5: Integration

#### ERR-INT-001: Integrate Circuit Breaker

```yaml
task_id: ERR-INT-001
task_name: "Integrate Circuit Breaker"
task_type: TYPE-D (Integration)
phase: PHASE-5
order: 1

description: |
  Wire CircuitBreaker into dispatch pipeline.
  
deliverables:
  - File: logging_system/dispatch/dispatcher_with_error_handling.py
  - Updates to: logging_system/services/logging_service.py

dependencies:
  - ERR-CB-004  # Uses CircuitBreakerRegistry
  - ERR-DLQ-003 # Uses DLQ for fallback

acceptance_criteria:
  - [ ] Dispatcher uses circuit breaker per adapter
  - [ ] OPEN breaker rejects dispatch
  - [ ] Circuit breaker state reflected in metrics
  - [ ] No adapter calls when circuit open

test_requirements:
  - test_dispatch_with_circuit_breaker
  - test_circuit_open_rejects_dispatch
  - test_circuit_half_open_allows_dispatch

estimated_effort:
  hours: 3-4
  loc: 150-200

risk_level: MEDIUM

integration_notes: |
  - Minimal changes to existing dispatch
  - Wrap existing adapter calls
  - Preserve existing error handling
```

#### ERR-INT-002: Integrate DLQ

```yaml
task_id: ERR-INT-002
task_name: "Integrate DLQ"
task_type: TYPE-D (Integration)
phase: PHASE-5
order: 2

description: |
  Wire DLQ into dispatch on adapter failure.
  
deliverables:
  - File: logging_system/dispatch/dispatcher_with_error_handling.py (extends ERR-INT-001)

dependencies:
  - ERR-INT-001
  - ERR-DLQ-004  # Uses FileBasedDLQ

acceptance_criteria:
  - [ ] Failed dispatch enqueues to DLQ
  - [ ] DLQ entry contains original record
  - [ ] DLQ entry contains error context
  - [ ] DLQ metrics available in evidence

test_requirements:
  - test_dispatch_failure_enqueues_dlq
  - test_dlq_entry_contains_record
  - test_dlq_entry_contains_error

estimated_effort:
  hours: 2-3
  loc: 100-150

risk_level: MEDIUM
```

#### ERR-INT-003: Add Retry to Dispatch

```yaml
task_id: ERR-INT-003
task_name: "Add Retry to Dispatch"
task_type: TYPE-D (Integration)
phase: PHASE-5
order: 3

description: |
  Add retry logic to dispatch with backoff.
  
deliverables:
  - File: logging_system/dispatch/dispatcher_with_error_handling.py (extends ERR-INT-002)

dependencies:
  - ERR-INT-002
  - ERR-RT-004  # Uses RetryExecutor

acceptance_criteria:
  - [ ] Retryable errors trigger retry
  - [ ] Non-retryable errors go directly to DLQ
  - [ ] Backoff applied between retries
  - [ ] Retry count tracked
  - [ ] DLQ only after max retries exceeded

test_requirements:
  - test_dispatch_retry_on_transient_error
  - test_dispatch_no_retry_on_permanent_error
  - test_dispatch_backoff_applied
  - test_dispatch_retry_count_tracked

estimated_effort:
  hours: 3-4
  loc: 150-200

risk_level: MEDIUM
```

#### ERR-INT-004: End-to-End Tests

```yaml
task_id: ERR-INT-004
task_name: "End-to-End Tests"
task_type: TYPE-E (Validation)
phase: PHASE-5
order: 4

description: |
  Comprehensive end-to-end tests for error handling.
  
deliverables:
  - File: logging_system/tests/test_error_handling_e2e.py

dependencies:
  - ERR-INT-003  # All components integrated

acceptance_criteria:
  - [ ] End-to-end flow: log → dispatch → failure → retry → success
  - [ ] End-to-end flow: log → dispatch → failure → DLQ
  - [ ] Circuit breaker: failure → open → rejection → recovery
  - [ ] Performance: retry overhead < 10% of dispatch time
  - [ ] All existing tests still pass

test_requirements:
  - test_e2e_retry_success
  - test_e2e_dlq_after_max_retries
  - test_e2e_circuit_breaker_open
  - test_e2e_circuit_breaker_recovery
  - test_e2e_backpressure_dlq
  - test_e2e_no_regression

estimated_effort:
  hours: 4-6
  loc: 300-400

risk_level: HIGH

validation_checklist: |
  - [ ] All acceptance criteria documented as tests
  - [ ] Tests are deterministic
  - [ ] Tests clean up after themselves
  - [ ] Performance benchmarks included
```

---

## 8. Execution Order

### 8.1 Sequential Task Execution

```
Task Execution Order (No Parallelism):

1. ERR-FND-001 → ERR-FND-002 → ERR-FND-003 → ERR-FND-004
                                                        ↓
2. ERR-CB-001 → ERR-CB-002 → ERR-CB-003 → ERR-CB-004 → ERR-CB-005
                                                        ↓
3. ERR-RT-001 → ERR-RT-002 → ERR-RT-003 → ERR-RT-004 → ERR-RT-005
                                                        ↓
4. ERR-DLQ-001 → ERR-DLQ-002 → ERR-DLQ-003 → ERR-DLQ-004 → ERR-DLQ-005
                                                        ↓
5. ERR-INT-001 → ERR-INT-002 → ERR-INT-003 → ERR-INT-004
```

### 8.2 Phase Gate Criteria

| Phase | Gate | Criteria |
|-------|------|----------|
| PHASE-1 | GATE-1 | ERR-FND-001 through ERR-FND-004 all complete |
| PHASE-2 | GATE-2 | ERR-CB-001 through ERR-CB-005 all complete |
| PHASE-3 | GATE-3 | ERR-RT-001 through ERR-RT-005 all complete |
| PHASE-4 | GATE-4 | ERR-DLQ-001 through ERR-DLQ-005 all complete |
| PHASE-5 | GATE-5 | ERR-INT-001 through ERR-INT-004 all complete |

---

## 9. Validation Gates

### 9.1 Gate Template

```yaml
gate:
  id: GATE-X
  phase: PHASE-X
  name: "Phase X Completion Gate"
  
  checklist:
    - [ ] All tasks in phase complete
    - [ ] All acceptance criteria met
    - [ ] Phase tests pass (100%)
    - [ ] No breaking changes to existing code
    - [ ] Documentation updated
    - [ ] Code passes linting
    - [ ] Type hints validated (mypy)
  
  signoff_required:
    - Developer: [ ]
    - Reviewer: [ ]
  
  blockers:
    - None / [List blockers]
  
  notes:
    - [Notes on completion]
```

---

## 10. Risk Register

| Task ID | Risk | Likelihood | Impact | Mitigation |
|---------|------|------------|--------|------------|
| ERR-CB-003 | Thread safety bugs | Medium | High | Extensive concurrent testing |
| ERR-RT-004 | Retry loop bugs | Medium | High | State machine testing |
| ERR-DLQ-003 | Data loss on crash | Medium | Critical | File persistence early |
| ERR-INT-001 | Breaking existing dispatch | High | High | Minimal changes, wrap not replace |
| ERR-INT-004 | Test flakiness | Medium | Medium | Deterministic test design |

---

## 11. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task Completion Rate | 100% | Tasks completed / Tasks planned |
| Test Coverage | > 95% | Lines covered by tests |
| Bug Rate (Post-Phase) | < 1 per phase | Issues filed per phase |
| Documentation Coverage | 100% | Tasks with docs / Total tasks |
| Type Hint Coverage | 100% | Typed functions / Total functions |

---

## 12. Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-17 | AI Assistant | Initial creation |

---

*This document is the source of truth for Error Handling & Resilience micro-tasks.*
