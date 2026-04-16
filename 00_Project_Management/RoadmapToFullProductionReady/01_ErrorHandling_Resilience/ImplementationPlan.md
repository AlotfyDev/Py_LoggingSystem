# Error Handling & Resilience - Implementation Roadmap

**Current Score:** 5/10  
**Target Score:** 9/10  
**Priority:** CRITICAL

---

## Executive Summary

The logging system currently lacks robust error handling mechanisms. When adapter failures occur, the system may cascade failures without isolation. Additionally, there's no dead letter queue (DLQ) for failed messages, and retry mechanisms with backoff are missing entirely.

---

## Gap Analysis

| Gap | Severity | Current State | Target State |
|-----|----------|---------------|--------------|
| Circuit Breaker | CRITICAL | None | Per-adapter circuit breaker with 3 states |
| Dead Letter Queue | CRITICAL | Failed logs requeued only | Persistent DLQ with retry capability |
| Retry Mechanisms | CRITICAL | No retry | Exponential backoff with jitter |
| Timeout Handling | HIGH | Implicit timeouts | Configurable timeouts per operation |
| Error Classification | MEDIUM | Generic errors | Typed error hierarchy |

---

## Implementation Phases (Dependency-Ordered)

### Phase 1: Foundation Layer (No Dependencies)

These are the core components that everything else builds upon.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 1: FOUNDATION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  1.1 Error Classification Hierarchy                                         │
│      ├── EErrorCategory enum (TRANSIENT, PERMANENT, PARTIAL)              │
│      ├── ERetryableError enum (NETWORK, TIMEOUT, SERVICE_UNAVAILABLE)     │
│      ├── ELogErrorCode enum (DISPATCH_FAILED, SCHEMA_VIOLATION, etc.)     │
│      └── ErrorContext dataclass (timestamp, original_error, metadata)     │
│                                                                             │
│  1.2 Error Result Types                                                    │
│      ├── Success[T] result type                                            │
│      ├── ErrorResult dataclass                                             │
│      └── Result[T] union type with is_ok(), is_err() methods               │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 1.1.1 Error Classification Hierarchy

**File:** `logging_system/errors/error_hierarchy.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class EErrorCategory(str, Enum):
    TRANSIENT = "transient"           # May succeed on retry
    PERMANENT = "permanent"          # Will never succeed
    PARTIAL = "partial"              # Succeeded partially


class ERetryableError(str, Enum):
    NETWORK_TIMEOUT = "network_timeout"
    CONNECTION_REFUSED = "connection_refused"
    SERVICE_UNAVAILABLE = "service_unavailable"
    RATE_LIMITED = "rate_limited"
    RESOURCE_BUSY = "resource_busy"
    UNKNOWN = "unknown"


class ELogErrorCode(str, Enum):
    ADAPTER_EMIT_FAILED = "adapter_emit_failed"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    BINDING_NOT_ESTABLISHED = "binding_not_established"
    CONTAINER_LEASE_INVALID = "container_lease_invalid"
    EXECUTION_LEASE_INVALID = "execution_lease_invalid"
    QUEUE_BOUNDS_EXCEEDED = "queue_bounds_exceeded"
    BACKPRESSURE_TRIGGERED = "backpressure_triggered"
    SAFEPOINTS_VIOLATION = "safepoints_violation"


@dataclass(frozen=True)
class ErrorContext:
    timestamp_utc: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error_code: ELogErrorCode | None = None
    category: EErrorCategory | None = None
    retryable: ERetryableError | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    original_error: str | None = None
    stack_trace: str | None = None

    def is_retryable(self) -> bool:
        return self.category == EErrorCategory.TRANSIENT and self.retryable is not None
```

#### 1.1.2 Result Type Pattern

**File:** `logging_system/errors/result.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import TypeVar, Generic, Callable

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True, slots=True)
class Success(Generic[T]):
    value: T


@dataclass(frozen=True, slots=True)
class ErrorResult:
    code: str
    message: str
    context: ErrorContext | None = None

    def __bool__(self) -> bool:
        return False


Result = Success[T] | ErrorResult


class ResultOps:
    @staticmethod
    def ok(value: T) -> Success[T]:
        return Success(value)

    @staticmethod
    def err(code: str, message: str, context: ErrorContext | None = None) -> ErrorResult:
        return ErrorResult(code=code, message=message, context=context)

    @staticmethod
    def bind(result: Result[T], f: Callable[[T], Result[U]]) -> Result[U]:
        if isinstance(result, ErrorResult):
            return result
        return f(result.value)
```

---

### Phase 2: Circuit Breaker (Depends on Phase 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 2: CIRCUIT BREAKER                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  2.1 Circuit Breaker State Machine                                         │
│      ├── ECircuitState enum (CLOSED, OPEN, HALF_OPEN)                    │
│      ├── CircuitBreakerConfig dataclass                                    │
│      └── CircuitBreakerMetrics dataclass                                   │
│                                                                             │
│  2.2 Circuit Breaker Implementation                                        │
│      ├── CircuitBreaker class with state transitions                       │
│      ├── Failure threshold and timeout configuration                       │
│      └── Thread-safe state management with RLock                           │
│                                                                             │
│  2.3 Adapter Circuit Breaker Integration                                    │
│      ├── Per-adapter circuit breaker registry                              │
│      └── Automatic fallback to NoOpAdapter when OPEN                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.1.1 Circuit Breaker State Machine

**File:** `logging_system/errors/circuit_breaker.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from threading import RLock
from typing import Callable, TypeVar
import random

T = TypeVar("T")


class ECircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject all
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 3          # Successes to close from half-open
    open_timeout_seconds: float = 30.0  # Time before half-open
    half_open_max_calls: int = 3         # Max test calls in half-open
    sliding_window_size: int = 10       # Recent failures to consider


@dataclass
class CircuitBreakerMetrics:
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: str | None = None
    last_success_time: str | None = None
    state_transitions: int = 0


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> None:
        self.name = name
        self._config = config or CircuitBreakerConfig()
        self._state = ECircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._opened_at: datetime | None = None
        self._lock = RLock()
        self._metrics = CircuitBreakerMetrics()
        self._recent_failures: list[datetime] = []

    @property
    def state(self) -> ECircuitState:
        with self._lock:
            self._check_state_transition()
            return self._state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        with self._lock:
            return CircuitBreakerMetrics(
                total_calls=self._metrics.total_calls,
                successful_calls=self._metrics.successful_calls,
                failed_calls=self._metrics.failed_calls,
                rejected_calls=self._metrics.rejected_calls,
                last_failure_time=self._metrics.last_failure_time,
                last_success_time=self._metrics.last_success_time,
                state_transitions=self._metrics.state_transitions,
            )

    def call(self, func: Callable[..., T], *args: ..., **kwargs: ...) -> T:
        if self.state == ECircuitState.OPEN:
            self._metrics.rejected_calls += 1
            raise CircuitBreakerOpenError(f"Circuit '{self.name}' is OPEN")

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise

    def _record_success(self) -> None:
        with self._lock:
            self._metrics.successful_calls += 1
            self._metrics.last_success_time = datetime.utcnow().isoformat()
            self._failure_count = 0

            if self._state == ECircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._config.success_threshold:
                    self._transition_to(ECircuitState.CLOSED)

    def _record_failure(self) -> None:
        with self._lock:
            self._metrics.failed_calls += 1
            self._metrics.last_failure_time = datetime.utcnow().isoformat()
            self._failure_count += 1
            self._success_count = 0
            self._recent_failures.append(datetime.utcnow())

            # Trim to sliding window
            cutoff = datetime.utcnow() - timedelta(minutes=5)
            self._recent_failures = [f for f in self._recent_failures if f > cutoff]

            if self._state == ECircuitState.HALF_OPEN:
                self._transition_to(ECircuitState.OPEN)
            elif self._failure_count >= self._config.failure_threshold:
                self._transition_to(ECircuitState.OPEN)

    def _transition_to(self, new_state: ECircuitState) -> None:
        if self._state != new_state:
            self._state = new_state
            self._metrics.state_transitions += 1
            self._success_count = 0
            self._half_open_calls = 0

            if new_state == ECircuitState.OPEN:
                self._opened_at = datetime.utcnow()
            elif new_state == ECircuitState.CLOSED:
                self._failure_count = 0
                self._recent_failures.clear()

    def _check_state_transition(self) -> None:
        if self._state == ECircuitState.OPEN and self._opened_at:
            elapsed = (datetime.utcnow() - self._opened_at).total_seconds()
            if elapsed >= self._config.open_timeout_seconds:
                self._transition_to(ECircuitState.HALF_OPEN)


class CircuitBreakerOpenError(Exception):
    pass
```

#### 2.2.1 Adapter Circuit Breaker Registry

**File:** `logging_system/errors/circuit_breaker_registry.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, ECircuitState


@dataclass
class CircuitBreakerRegistry:
    _breakers: dict[str, CircuitBreaker] = field(default_factory=dict)
    _default_config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _lock: RLock = field(default_factory=RLock)

    def get_or_create(self, adapter_key: str, config: CircuitBreakerConfig | None = None) -> CircuitBreaker:
        with self._lock:
            if adapter_key not in self._breakers:
                self._breakers[adapter_key] = CircuitBreaker(
                    name=adapter_key,
                    config=config or self._default_config,
                )
            return self._breakers[adapter_key]

    def get_state(self, adapter_key: str) -> ECircuitState | None:
        with self._lock:
            breaker = self._breakers.get(adapter_key)
            return breaker.state if breaker else None

    def is_available(self, adapter_key: str) -> bool:
        state = self.get_state(adapter_key)
        return state != ECircuitState.OPEN

    def list_all_states(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {
                key: {
                    "state": breaker.state.value,
                    "metrics": breaker.metrics.__dict__,
                }
                for key, breaker in self._breakers.items()
            }
```

---

### Phase 3: Retry Mechanisms (Depends on Phases 1, 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 3: RETRY MECHANISMS                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  3.1 Retry Strategy Enumeration                                             │
│      ├── ERetryStrategy enum (IMMEDIATE, LINEAR, EXPONENTIAL, FIBONACCI)  │
│      └── RetryConfig dataclass                                             │
│                                                                             │
│  3.2 Backoff Calculator                                                     │
│      ├── Exponential backoff with jitter                                   │
│      ├── Max delay cap configuration                                       │
│      └── Retry budget tracking                                             │
│                                                                             │
│  3.3 Retry Executor                                                         │
│      ├── execute_with_retry() with retry policies                          │
│      ├── Circuit breaker integration                                       │
│      └── Cancellation token support                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.1.1 Retry Configuration

**File:** `logging_system/errors/retry_policy.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TypeVar
import random
import time
from threading import Event

T = TypeVar("T")


class ERetryStrategy(str, Enum):
    IMMEDIATE = "immediate"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"


class EJitterMode(str, Enum):
    NONE = "none"
    FULL = "full"           # Random within window
    DECORRELATED = "decorrelated"  # Gradual decrease


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 3
    initial_delay_seconds: float = 0.1
    max_delay_seconds: float = 30.0
    strategy: ERetryStrategy = ERetryStrategy.EXPONENTIAL
    jitter_mode: EJitterMode = EJitterMode.FULL
    retryable_categories: frozenset[str] = frozenset({"transient"})
    timeout_seconds: float | None = None
    on_retry: Callable[[int, Exception], None] | None = None


@dataclass
class RetryAttempt:
    attempt_number: int
    delay_seconds: float
    error: Exception
    timestamp_utc: str


@dataclass
class RetryBudget:
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_delay_seconds: float = 0.0
    attempts: list[RetryAttempt] = field(default_factory=list)
```

#### 3.2.1 Backoff Calculator

**File:** `logging_system/errors/backoff_calculator.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import random

from .retry_policy import ERetryStrategy, EJitterMode, RetryConfig


class BackoffCalculator:
    def __init__(self, config: RetryConfig) -> None:
        self._config = config
        self._fib_cache: dict[int, float] = {0: 1, 1: 1}

    def calculate_delay(self, attempt: int) -> float:
        base_delay = self._calculate_base_delay(attempt)
        delay_with_jitter = self._apply_jitter(base_delay, attempt)
        return min(delay_with_jitter, self._config.max_delay_seconds)

    def _calculate_base_delay(self, attempt: int) -> float:
        match self._config.strategy:
            case ERetryStrategy.IMMEDIATE:
                return 0.0

            case ERetryStrategy.LINEAR:
                return self._config.initial_delay_seconds * attempt

            case ERetryStrategy.EXPONENTIAL:
                return self._config.initial_delay_seconds * (2 ** (attempt - 1))

            case ERetryStrategy.FIBONACCI:
                return self._config.initial_delay_seconds * self._fibonacci(attempt)

        return self._config.initial_delay_seconds

    def _apply_jitter(self, base_delay: float, attempt: int) -> float:
        match self._config.jitter_mode:
            case EJitterMode.NONE:
                return base_delay

            case EJitterMode.FULL:
                return base_delay * (0.5 + random.random())

            case EJitterMode.DECORRELATED:
                # Decorrelated jitter: grows more slowly
                return min(base_delay * (0.5 + random.random() * 1.5), self._config.max_delay_seconds)

        return base_delay

    def _fibonacci(self, n: int) -> float:
        if n in self._fib_cache:
            return self._fib_cache[n]
        result = self._fibonacci(n - 1) + self._fibonacci(n - 2)
        self._fib_cache[n] = result
        return result
```

#### 3.3.1 Retry Executor

**File:** `logging_system/errors/retry_executor.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from threading import Event
from typing import Callable, TypeVar
import time

from .backoff_calculator import BackoffCalculator
from .circuit_breaker import CircuitBreaker
from .retry_policy import RetryAttempt, RetryBudget, RetryConfig, EErrorCategory
from .result import ErrorResult, Result

T = TypeVar("T")


class RetryExecutor:
    def __init__(
        self,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._circuit_breaker = circuit_breaker
        self._budget = RetryBudget()

    def execute(
        self,
        func: Callable[[], T],
        config: RetryConfig,
        cancel_token: Event | None = None,
    ) -> Result[T]:
        self._budget = RetryBudget()
        calculator = BackoffCalculator(config)
        start_time = time.monotonic()

        for attempt in range(1, config.max_attempts + 1):
            if cancel_token and cancel_token.is_set():
                return ErrorResult(
                    code="cancelled",
                    message="Operation cancelled",
                )

            if config.timeout_seconds:
                elapsed = time.monotonic() - start_time
                if elapsed >= config.timeout_seconds:
                    return ErrorResult(
                        code="timeout",
                        message=f"Retry timeout exceeded after {elapsed:.2f}s",
                    )

            try:
                if self._circuit_breaker:
                    result = self._circuit_breaker.call(func)
                else:
                    result = func()

                self._budget.successful_attempts += 1
                return ResultOps.ok(result)

            except Exception as e:
                self._budget.failed_attempts += 1
                self._budget.total_attempts += 1

                # Calculate delay
                delay = calculator.calculate_delay(attempt)
                self._budget.total_delay_seconds += delay

                # Record attempt
                self._budget.attempts.append(RetryAttempt(
                    attempt_number=attempt,
                    delay_seconds=delay,
                    error=e,
                    timestamp_utc=datetime.utcnow().isoformat(),
                ))

                # On retry callback
                if config.on_retry:
                    config.on_retry(attempt, e)

                # Check if should retry
                if attempt < config.max_attempts:
                    if e.category == EErrorCategory.PERMANENT:
                        break
                    if e.category not in [c for c in config.retryable_categories]:
                        break
                    time.sleep(delay)

        return ErrorResult(
            code="max_retries_exceeded",
            message=f"Failed after {config.max_attempts} attempts",
            context=e.context if hasattr(e, 'context') else None,
        )

    @property
    def budget(self) -> RetryBudget:
        return self._budget
```

---

### Phase 4: Dead Letter Queue (Depends on Phases 1, 2, 3)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 4: DEAD LETTER QUEUE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  4.1 DLQ Contract Definition                                               │
│      ├── DLQEntry dataclass                                               │
│      ├── DLQConfig dataclass                                              │
│      └── IDeadLetterQueue port interface                                  │
│                                                                             │
│  4.2 DLQ Implementation                                                    │
│      ├── InMemoryDeadLetterQueue                                          │
│      ├── FileBasedDeadLetterQueue                                         │
│      └── DLQ entry lifecycle (store, retry, discard, expire)              │
│                                                                             │
│  4.3 DLQ Integration with Dispatch                                         │
│      ├── Dispatcher integration with DLQ                                  │
│      ├── Automatic retry scheduling                                        │
│      └── DLQ metrics and monitoring                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 4.1.1 DLQ Contract

**File:** `logging_system/errors/dlq_contract.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from .error_hierarchy import ErrorContext, ELogErrorCode


class EDLQStatus(str, Enum):
    PENDING = "pending"       # Awaiting retry
    RETRYING = "retrying"     # Currently retrying
    FAILED = "failed"         # Exhausted retries, awaiting manual action
    EXPIRED = "expired"       # Past TTL, can be discarded
    DISCARDED = "discarded"   # Manually discarded


@dataclass(frozen=True)
class DLQEntry:
    entry_id: str
    original_record_id: str
    payload: dict[str, Any]
    error_context: ErrorContext
    status: EDLQStatus
    attempt_count: int = 0
    max_attempts: int = 3
    next_retry_at_utc: str | None = None
    created_at_utc: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_error_message: str | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class DLQConfig:
    max_entries: int = 10000
    default_max_attempts: int = 3
    retry_delay_seconds: float = 60.0
    expiration_seconds: float = 604800.0  # 7 days
    enable_auto_retry: bool = True
    retry_backoff_multiplier: float = 2.0


@dataclass
class DLQStatistics:
    total_entries: int
    pending_count: int
    retrying_count: int
    failed_count: int
    expired_count: int
    discarded_count: int
    total_retries: int
    successful_recoveries: int


class IDeadLetterQueue(Protocol):
    def enqueue(self, entry: DLQEntry) -> str:
        ...

    def dequeue(self) -> DLQEntry | None:
        ...

    def mark_retrying(self, entry_id: str) -> None:
        ...

    def mark_failed(self, entry_id: str, error_message: str) -> None:
        ...

    def mark_discarded(self, entry_id: str) -> None:
        ...

    def get(self, entry_id: str) -> DLQEntry | None:
        ...

    def list_by_status(self, status: EDLQStatus) -> list[DLQEntry]:
        ...

    def get_statistics(self) -> DLQStatistics:
        ...

    def purge_expired(self) -> int:
        ...

    def retry_entry(self, entry_id: str) -> bool:
        ...
```

#### 4.2.1 DLQ Implementation

**File:** `logging_system/errors/file_based_dlq.py`

```python
from __future__ import annotations
from dataclasses import asdict
from datetime import datetime, timedelta
import json
from pathlib import Path
from threading import RLock
from typing import Any
import uuid

from .dlq_contract import (
    DLQConfig,
    DLQEntry,
    DLQStatistics,
    EDLQStatus,
    IDeadLetterQueue,
)
from .retry_policy import RetryConfig, ERetryStrategy


class FileBasedDeadLetterQueue(IDeadLetterQueue):
    def __init__(
        self,
        storage_path: Path,
        config: DLQConfig | None = None,
    ) -> None:
        self._path = storage_path
        self._config = config or DLQConfig()
        self._lock = RLock()
        self._entries: dict[str, DLQEntry] = {}
        self._status_index: dict[EDLQStatus, set[str]] = {status: set() for status in EDLQStatus}
        self._total_retries = 0
        self._successful_recoveries = 0
        self._load()

    def enqueue(self, entry: DLQEntry) -> str:
        with self._lock:
            if entry.entry_id in self._entries:
                raise KeyError(f"Entry {entry.entry_id} already exists")

            if len(self._entries) >= self._config.max_entries:
                self._evict_oldest_failed()

            entry_id = entry.entry_id or str(uuid.uuid4())
            new_entry = DLQEntry(
                entry_id=entry_id,
                original_record_id=entry.original_record_id,
                payload=entry.payload,
                error_context=entry.error_context,
                status=EDLQStatus.PENDING,
                attempt_count=0,
                max_attempts=entry.max_attempts,
                next_retry_at_utc=self._calculate_next_retry(0),
                created_at_utc=datetime.utcnow().isoformat(),
                last_error_message=entry.last_error_message,
                tags=entry.tags,
            )

            self._entries[entry_id] = new_entry
            self._status_index[EDLQStatus.PENDING].add(entry_id)
            self._persist()
            return entry_id

    def dequeue(self) -> DLQEntry | None:
        with self._lock:
            for status in [EDLQStatus.PENDING, EDLQStatus.RETRYING]:
                ready = [
                    eid for eid in self._status_index[status]
                    if self._is_ready_for_retry(self._entries[eid])
                ]
                if ready:
                    entry_id = ready[0]
                    entry = self._entries[entry_id]
                    self._status_index[status].discard(entry_id)
                    self._status_index[EDLQStatus.RETRYING].add(entry_id)
                    entry = DLQEntry(
                        entry_id=entry.entry_id,
                        original_record_id=entry.original_record_id,
                        payload=entry.payload,
                        error_context=entry.error_context,
                        status=EDLQStatus.RETRYING,
                        attempt_count=entry.attempt_count,
                        max_attempts=entry.max_attempts,
                        next_retry_at_utc=None,
                        created_at_utc=entry.created_at_utc,
                        last_error_message=entry.last_error_message,
                        tags=entry.tags,
                    )
                    self._entries[entry_id] = entry
                    self._persist()
                    return entry
            return None

    def mark_retrying(self, entry_id: str) -> None:
        with self._lock:
            entry = self._entries.get(entry_id)
            if not entry:
                raise KeyError(f"Entry {entry_id} not found")

            entry.attempt_count += 1
            self._total_retries += 1

            if entry.attempt_count >= entry.max_attempts:
                entry.status = EDLQStatus.FAILED
                entry.next_retry_at_utc = None
            else:
                entry.status = EDLQStatus.PENDING
                entry.next_retry_at_utc = self._calculate_next_retry(entry.attempt_count)

            self._persist()

    def mark_failed(self, entry_id: str, error_message: str) -> None:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry:
                entry.status = EDLQStatus.FAILED
                entry.last_error_message = error_message
                self._persist()

    def mark_discarded(self, entry_id: str) -> None:
        self._update_status(entry_id, EDLQStatus.DISCARDED)

    def get(self, entry_id: str) -> DLQEntry | None:
        with self._lock:
            return self._entries.get(entry_id)

    def list_by_status(self, status: EDLQStatus) -> list[DLQEntry]:
        with self._lock:
            return [self._entries[eid] for eid in self._status_index[status]]

    def get_statistics(self) -> DLQStatistics:
        with self._lock:
            return DLQStatistics(
                total_entries=len(self._entries),
                pending_count=len(self._status_index[EDLQStatus.PENDING]),
                retrying_count=len(self._status_index[EDLQStatus.RETRYING]),
                failed_count=len(self._status_index[EDLQStatus.FAILED]),
                expired_count=len(self._status_index[EDLQStatus.EXPIRED]),
                discarded_count=len(self._status_index[EDLQStatus.DISCARDED]),
                total_retries=self._total_retries,
                successful_recoveries=self._successful_recoveries,
            )

    def purge_expired(self) -> int:
        with self._lock:
            expired = []
            for entry_id, entry in self._entries.items():
                if entry.status == EDLQStatus.EXPIRED:
                    expired.append(entry_id)

            for entry_id in expired:
                del self._entries[entry_id]
                for status_set in self._status_index.values():
                    status_set.discard(entry_id)

            self._persist()
            return len(expired)

    def retry_entry(self, entry_id: str) -> bool:
        with self._lock:
            entry = self._entries.get(entry_id)
            if not entry or entry.status != EDLQStatus.FAILED:
                return False
            entry.status = EDLQStatus.PENDING
            entry.attempt_count = 0
            entry.next_retry_at_utc = self._calculate_next_retry(0)
            self._status_index[EDLQStatus.FAILED].discard(entry_id)
            self._status_index[EDLQStatus.PENDING].add(entry_id)
            self._persist()
            return True

    def _calculate_next_retry(self, attempt: int) -> str:
        delay = self._config.retry_delay_seconds * (self._config.retry_backoff_multiplier ** attempt)
        next_time = datetime.utcnow() + timedelta(seconds=min(delay, 3600))
        return next_time.isoformat()

    def _is_ready_for_retry(self, entry: DLQEntry) -> bool:
        if not entry.next_retry_at_utc:
            return False
        retry_time = datetime.fromisoformat(entry.next_retry_at_utc)
        return datetime.utcnow() >= retry_time

    def _update_status(self, entry_id: str, new_status: EDLQStatus) -> None:
        entry = self._entries.get(entry_id)
        if entry:
            old_status = entry.status
            self._status_index[old_status].discard(entry_id)
            entry.status = new_status
            self._status_index[new_status].add(entry_id)
            self._persist()

    def _evict_oldest_failed(self) -> None:
        failed = [
            (eid, self._entries[eid].created_at_utc)
            for eid in self._status_index[EDLQStatus.FAILED]
        ]
        if failed:
            oldest = min(failed, key=lambda x: x[1])
            del self._entries[oldest[0]]
            self._status_index[EDLQStatus.FAILED].discard(oldest[0])

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "entries": {k: asdict(v) for k, v in self._entries.items()},
            "status_index": {k.value: list(v) for k, v in self._status_index.items()},
            "total_retries": self._total_retries,
            "successful_recoveries": self._successful_recoveries,
        }
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._entries = {k: DLQEntry(**v) for k, v in data.get("entries", {}).items()}
            self._status_index = {
                EDLQStatus(k): set(v) for k, v in data.get("status_index", {}).items()
            }
            self._total_retries = data.get("total_retries", 0)
            self._successful_recoveries = data.get("successful_recoveries", 0)
        except Exception:
            pass
```

---

### Phase 5: Integration (Depends on All Previous Phases)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 5: INTEGRATION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  5.1 Dispatcher Integration                                                 │
│      ├── Inject circuit breaker into dispatch                              │
│      ├── Add DLQ on adapter failure                                       │
│      └── Wrap with retry executor                                         │
│                                                                             │
│  5.2 LoggingService Integration                                             │
│      ├── Add circuit_breaker_registry field                               │
│      ├── Add dead_letter_queue field                                      │
│      └── Add retry_executor field                                         │
│                                                                             │
│  5.3 Health Endpoint Enhancement                                           │
│      ├── Add DLQ health check                                             │
│      ├── Add circuit breaker status                                        │
│      └── Add retry metrics to evidence                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 5.1.1 Dispatcher with Error Handling

**File:** `logging_system/dispatch/dispatcher_with_error_handling.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logging_system.errors.circuit_breaker import CircuitBreaker
    from logging_system.errors.dlq_contract import IDeadLetterQueue
    from logging_system.errors.retry_policy import RetryConfig
    from logging_system.errors.retry_executor import RetryExecutor
    from logging_system.models.record import LogRecord


@dataclass
class ErrorHandlingConfig:
    enable_circuit_breaker: bool = True
    enable_dead_letter_queue: bool = True
    enable_retry: bool = True
    circuit_breaker_config: dict | None = None
    retry_config: RetryConfig | None = None


@dataclass
class DispatchResult:
    success: bool
    dispatched_count: int = 0
    failed_count: int = 0
    dlq_enqueued_count: int = 0
    circuit_broken_adapters: list[str] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


class ErrorHandlingDispatcher:
    def __init__(
        self,
        base_dispatcher,
        circuit_breaker_registry,
        dlq: IDeadLetterQueue | None = None,
        retry_executor: RetryExecutor | None = None,
        config: ErrorHandlingConfig | None = None,
    ) -> None:
        self._base = base_dispatcher
        self._cb_registry = circuit_breaker_registry
        self._dlq = dlq
        self._retry_executor = retry_executor
        self._config = config or ErrorHandlingConfig()

    def dispatch_with_error_handling(
        self,
        records: list[LogRecord],
        adapter_key: str,
    ) -> DispatchResult:
        result = DispatchResult(success=True)

        for record in records:
            try:
                if self._config.enable_circuit_breaker:
                    breaker = self._cb_registry.get_or_create(adapter_key)
                    breaker.call(self._emit_via_adapter, record, adapter_key)
                else:
                    self._emit_via_adapter(record, adapter_key)

                result.dispatched_count += 1

            except Exception as e:
                result.failed_count += 1
                result.errors.append({
                    "record_id": record.record_id,
                    "error": str(e),
                    "adapter_key": adapter_key,
                })

                if self._config.enable_dead_letter_queue and self._dlq:
                    self._enqueue_to_dlq(record, e)
                    result.dlq_enqueued_count += 1

                if self._config.enable_circuit_breaker:
                    if self._cb_registry.get_state(adapter_key) == ECircuitState.OPEN:
                        result.circuit_broken_adapters.append(adapter_key)

        result.success = result.failed_count == 0
        return result

    def _emit_via_adapter(self, record: LogRecord, adapter_key: str) -> None:
        # Implementation details...
        pass

    def _enqueue_to_dlq(self, record: LogRecord, error: Exception) -> None:
        from logging_system.errors.dlq_contract import DLQEntry
        from logging_system.errors.error_hierarchy import ErrorContext, ELogErrorCode, EErrorCategory

        entry = DLQEntry(
            entry_id=str(uuid.uuid4()),
            original_record_id=record.record_id,
            payload=record.to_projection(),
            error_context=ErrorContext(
                error_code=ELogErrorCode.ADAPTER_EMIT_FAILED,
                category=EErrorCategory.TRANSIENT,
                original_error=str(error),
            ),
            status=EDLQStatus.PENDING,
        )
        self._dlq.enqueue(entry)
```

---

## File Structure After Implementation

```
logging_system/
├── errors/
│   ├── __init__.py
│   ├── error_hierarchy.py          # Phase 1
│   ├── result.py                   # Phase 1
│   ├── circuit_breaker.py         # Phase 2
│   ├── circuit_breaker_registry.py # Phase 2
│   ├── retry_policy.py            # Phase 3
│   ├── backoff_calculator.py      # Phase 3
│   ├── retry_executor.py          # Phase 3
│   ├── dlq_contract.py            # Phase 4
│   ├── in_memory_dlq.py           # Phase 4
│   ├── file_based_dlq.py          # Phase 4
│   └── dispatcher_with_error_handling.py # Phase 5
```

---

## Contract Additions

### New Contracts to Add

1. **Contract 26:** `26_LoggingSystem_ErrorHandling_AndResilience_Contract.template.yaml`
2. **Contract 27:** `27_LoggingSystem_CircuitBreaker_Contract.template.yaml`
3. **Contract 28:** `28_LoggingSystem_DeadLetterQueue_Contract.template.yaml`
4. **Contract 29:** `29_LoggingSystem_RetryPolicy_Contract.template.yaml`

---

## Test Plan

| Phase | Tests | Focus |
|-------|-------|-------|
| 1 | 15 | Error hierarchy validation, Result type operations |
| 2 | 20 | Circuit breaker state transitions, thread safety |
| 3 | 25 | Backoff calculations, retry limits, cancellation |
| 4 | 20 | DLQ CRUD, auto-retry scheduling, expiration |
| 5 | 15 | Integration with existing dispatch flow |

---

## Metrics to Track

| Metric | Description | Target |
|--------|-------------|--------|
| circuit_breaker_open_count | Times circuit opened | < 10/day |
| dlq_entries_total | Current DLQ size | < 1000 |
| dlq_recovery_rate | % recovered after DLQ | > 80% |
| retry_success_rate | % successful after retry | > 90% |
| avg_retry_attempts | Average attempts per failure | < 3 |

---

**Estimated Implementation Time:** 2-3 weeks  
**Estimated Effort:** ~1500 lines of new code  
**Risk Level:** Medium (affects critical dispatch path)
