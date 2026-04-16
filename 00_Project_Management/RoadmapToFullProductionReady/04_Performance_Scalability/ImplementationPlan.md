# Performance & Scalability - Implementation Roadmap

**Current Score:** 5/10  
**Target Score:** 9/10  
**Priority:** HIGH

---

## Executive Summary

The logging system supports basic thread safety modes and partitioning strategies, but lacks advanced performance optimizations like connection pooling, async dispatch, batch optimization, and comprehensive performance benchmarks.

---

## Gap Analysis

| Gap | Severity | Current State | Target State |
|-----|----------|---------------|--------------|
| Connection Pooling | CRITICAL | None | Per-adapter connection pools |
| Async Dispatch | HIGH | Synchronous only | Async executor option |
| Batch Optimization | MEDIUM | Fixed batch size | Adaptive batching |
| Performance Benchmarks | HIGH | None | Comprehensive benchmarks |
| Memory Optimization | MEDIUM | Basic deque | Memory-mapped buffers |

---

## Implementation Phases (Dependency-Ordered)

### Phase 1: Connection Pooling (No Dependencies)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 1: CONNECTION POOLING                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  1.1 Connection Pool Types                                                   │
│      ├── ConnectionPoolConfig dataclass                                    │
│      ├── ConnectionPoolMetrics dataclass                                   │
│      └── ConnectionState enum                                              │
│                                                                             │
│  1.2 Connection Pool Interface                                              │
│      ├── IConnectionPool port interface                                     │
│      └── IConnection port interface                                        │
│                                                                             │
│  1.3 Connection Pool Implementation                                         │
│      ├── ThreadedConnectionPool                                            │
│      ├── Connection lifecycle (create, acquire, release, close)           │
│      └── Health checking and recovery                                      │
│                                                                             │
│  1.4 Adapter Pool Integration                                               │
│      └── Integrate pools into OpenTelemetry adapter                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 1.1.1 Connection Pool Types

**File:** `logging_system/performance/connection_pool/types.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, TypeVar
import threading

T = TypeVar("T")


class EConnectionState(str, Enum):
    IDLE = "idle"
    CHECKED_OUT = "checked_out"
    HEALTH_CHECKING = "health_checking"
    CLOSED = "closed"


@dataclass(frozen=True)
class ConnectionPoolConfig:
    min_size: int = 1
    max_size: int = 10
    max_idle_time_seconds: float = 300.0
    max_lifetime_seconds: float = 3600.0
    health_check_interval_seconds: float = 60.0
    acquire_timeout_seconds: float = 30.0
    validation_timeout_seconds: float = 5.0


@dataclass
class ConnectionPoolMetrics:
    total_connections: int = 0
    idle_connections: int = 0
    checked_out_connections: int = 0
    pending_acquires: int = 0
    connection_errors: int = 0
    health_check_failures: int = 0
    timeouts: int = 0
    created_connections: int = 0
    closed_connections: int = 0


@dataclass
class PooledConnection:
    connection_id: str
    state: EConnectionState = EConnectionState.IDLE
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: datetime = field(default_factory=datetime.utcnow)
    use_count: int = 0
    error_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### 1.2.1 Connection Pool Interface

**File:** `logging_system/performance/connection_pool/pool.py`

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import threading
import time
import uuid
from typing import TYPE_CHECKING, Any, Callable, Generator, TypeVar

if TYPE_CHECKING:
    pass

T = TypeVar("T")


class IConnection(ABC):
    """Interface for pooled connections."""

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        ...

    @abstractmethod
    def execute(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        """Execute an operation using this connection."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the connection."""
        ...


class IConnectionPool(ABC):
    """Interface for connection pools."""

    @abstractmethod
    async def acquire(self) -> IConnection:
        """Acquire a connection from the pool."""
        ...

    @abstractmethod
    async def release(self, connection: IConnection) -> None:
        """Release a connection back to the pool."""
        ...

    @abstractmethod
    def get_metrics(self) -> ConnectionPoolMetrics:
        """Get pool metrics."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close all connections and shutdown pool."""
        ...


class ThreadedConnectionPool(IConnectionPool):
    """Thread-safe connection pool implementation."""

    def __init__(
        self,
        config: ConnectionPoolConfig,
        factory: Callable[[], IConnection],
        health_check: Callable[[IConnection], bool] | None = None,
    ) -> None:
        self._config = config
        self._factory = factory
        self._health_check = health_check or (lambda c: c.is_healthy())
        self._connections: list[PooledConnection] = []
        self._available: list[PooledConnection] = []
        self._lock = threading.RLock()
        self._semaphore = threading.Semaphore(config.max_size)
        self._metrics = ConnectionPoolMetrics()
        self._closed = False
        self._health_check_task: threading.Thread | None = None

    async def acquire(self) -> IConnection:
        if self._closed:
            raise RuntimeError("Pool is closed")

        # Wait for semaphore
        acquired = self._semaphore.acquire(timeout=self._config.acquire_timeout_seconds)
        if not acquired:
            self._metrics.timeouts += 1
            raise TimeoutError(f"Failed to acquire connection within {self._config.acquire_timeout_seconds}s")

        with self._lock:
            self._metrics.pending_acquires += 1

            # Try to get an available connection
            while self._available:
                pooled = self._available.pop()
                
                # Check if connection is still valid
                if self._is_connection_valid(pooled):
                    pooled.state = EConnectionState.CHECKED_OUT
                    pooled.last_used_at = datetime.utcnow()
                    pooled.use_count += 1
                    self._metrics.checked_out_connections += 1
                    self._metrics.pending_acquires -= 1
                    return ConnectionWrapper(pooled, self)

                # Connection invalid, close and remove
                self._close_pooled(pooled)

            # Create new connection if under max
            if len(self._connections) < self._config.max_size:
                pooled = self._create_connection()
                self._metrics.pending_acquires -= 1
                return ConnectionWrapper(pooled, self)

            # Should not reach here with semaphore
            raise RuntimeError("Unexpected state in connection pool")

    async def release(self, connection: IConnection) -> None:
        if isinstance(connection, ConnectionWrapper):
            pooled = connection._pooled
        else:
            return

        with self._lock:
            if self._closed:
                self._close_pooled(pooled)
                return

            pooled.state = EConnectionState.IDLE
            self._metrics.checked_out_connections -= 1

            if self._is_connection_valid(pooled):
                self._available.append(pooled)
            else:
                self._close_pooled(pooled)

        self._semaphore.release()

    def get_metrics(self) -> ConnectionPoolMetrics:
        with self._lock:
            return ConnectionPoolMetrics(
                total_connections=len(self._connections),
                idle_connections=len(self._available),
                checked_out_connections=self._metrics.checked_out_connections,
                pending_acquires=self._metrics.pending_acquires,
                connection_errors=self._metrics.connection_errors,
                health_check_failures=self._metrics.health_check_failures,
                timeouts=self._metrics.timeouts,
                created_connections=self._metrics.created_connections,
                closed_connections=self._metrics.closed_connections,
            )

    async def close(self) -> None:
        with self._lock:
            self._closed = True
            for pooled in self._connections:
                self._close_pooled(pooled)
            self._connections.clear()
            self._available.clear()

    def _create_connection(self) -> PooledConnection:
        conn = self._factory()
        pooled = PooledConnection(
            connection_id=str(uuid.uuid4()),
            state=EConnectionState.CHECKED_OUT,
            metadata={"connection": conn},
        )
        self._connections.append(pooled)
        self._metrics.created_connections += 1
        self._metrics.checked_out_connections += 1
        return pooled

    def _is_connection_valid(self, pooled: PooledConnection) -> bool:
        if pooled.state == EConnectionState.CLOSED:
            return False

        now = datetime.utcnow()
        age = (now - pooled.created_at).total_seconds()
        if age > self._config.max_lifetime_seconds:
            return False

        idle_time = (now - pooled.last_used_at).total_seconds()
        if idle_time > self._config.max_idle_time_seconds:
            return False

        conn = pooled.metadata.get("connection")
        if conn and not self._health_check(conn):
            pooled.error_count += 1
            if pooled.error_count >= 3:
                return False

        return True

    def _close_pooled(self, pooled: PooledConnection) -> None:
        pooled.state = EConnectionState.CLOSED
        conn = pooled.metadata.pop("connection", None)
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        self._metrics.closed_connections += 1


@dataclass
class ConnectionWrapper(IConnection):
    """Wrapper that returns connection to pool on exit."""

    _pooled: PooledConnection
    _pool: ThreadedConnectionPool

    @property
    def connection(self) -> Any:
        return self._pooled.metadata.get("connection")

    def is_healthy(self) -> bool:
        conn = self.connection
        return conn is not None and conn.is_healthy()

    def execute(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        conn = self.connection
        if not conn:
            raise RuntimeError("Connection is not available")
        return getattr(conn, operation)(*args, **kwargs)

    def close(self) -> None:
        # Note: Don't close directly, release back to pool
        pass

    def __enter__(self) -> ConnectionWrapper:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Release back to pool on context exit
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._pool.release(self))
        except RuntimeError:
            pass
```

---

### Phase 2: Async Dispatch (Depends on Phase 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 2: ASYNC DISPATCH                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  2.1 Async Dispatch Types                                                   │
│      ├── DispatchMode enum (SYNC, ASYNC, BATCH_ASYNC)                      │
│      ├── AsyncDispatchConfig dataclass                                      │
│      └── DispatchJob dataclass                                             │
│                                                                             │
│  2.2 Async Dispatch Executor                                                │
│      ├── AsyncDispatchExecutor                                             │
│      ├── Job queue with priorities                                         │
│      └── Worker pool management                                           │
│                                                                             │
│  2.3 Async Dispatch Integration                                             │
│      └── Integrate with LoggingService dispatch_round()                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.1.1 Async Dispatch Types

**File:** `logging_system/performance/async_dispatch/types.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, TypeVar
import asyncio
import uuid

T = TypeVar("T")


class EDispatchMode(str, Enum):
    SYNC = "sync"                 # Synchronous dispatch (current behavior)
    ASYNC = "async"             # Async per-record dispatch
    BATCH_ASYNC = "batch_async"  # Batch async dispatch


class EJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncDispatchConfig:
    mode: EDispatchMode = EDispatchMode.SYNC
    max_concurrent_jobs: int = 10
    batch_size: int = 100
    batch_timeout_seconds: float = 1.0
    worker_pool_size: int = 4
    job_timeout_seconds: float = 30.0
    enable_priority: bool = True


@dataclass
class DispatchJob:
    job_id: str
    record_ids: list[str]
    adapter_key: str
    priority: int = 0
    status: EJobStatus = EJobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "record_ids": self.record_ids,
            "adapter_key": self.adapter_key,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }
```

#### 2.2.1 Async Dispatch Executor

**File:** `logging_system/performance/async_dispatch/executor.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from heapq import heappush, heappop
from typing import Any, Callable, Coroutine
import asyncio
import threading
import uuid
from contextlib import asynccontextmanager

from .types import AsyncDispatchConfig, DispatchJob, EDispatchMode, EJobStatus


class AsyncDispatchExecutor:
    """Executor for async dispatch operations."""

    def __init__(
        self,
        config: AsyncDispatchConfig,
        dispatch_handler: Callable[[list[str], str], Coroutine[Any, Any, Any]],
    ) -> None:
        self._config = config
        self._dispatch_handler = dispatch_handler
        self._jobs: list[DispatchJob] = []
        self._running_jobs: dict[str, asyncio.Task] = {}
        self._lock = threading.RLock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._worker_task: asyncio.Task | None = None
        self._closed = False
        self._metrics = AsyncDispatchMetrics()

    async def submit(self, record_ids: list[str], adapter_key: str, priority: int = 0) -> str:
        """Submit a dispatch job."""
        job_id = str(uuid.uuid4())
        job = DispatchJob(
            job_id=job_id,
            record_ids=record_ids,
            adapter_key=adapter_key,
            priority=priority,
        )

        with self._lock:
            heappush(self._jobs, (priority, job.created_at.timestamp(), job))
            self._metrics.jobs_submitted += 1

        # Start worker if not running
        if self._worker_task is None or self._worker_task.done():
            await self._ensure_worker()

        return job_id

    async def get_job_status(self, job_id: str) -> DispatchJob | None:
        """Get the status of a job."""
        with self._lock:
            for job in self._jobs:
                if job.job_id == job_id:
                    return job
            if job_id in self._running_jobs:
                return DispatchJob(job_id=job_id, record_ids=[], adapter_key="", status=EJobStatus.RUNNING)
            for job in self._jobs:
                if job.job_id == job_id:
                    return job
        return None

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or running job."""
        with self._lock:
            # Check pending jobs
            new_jobs = []
            cancelled = False
            for _, _, job in self._jobs:
                if job.job_id == job_id:
                    job.status = EJobStatus.CANCELLED
                    cancelled = True
                else:
                    new_jobs.append((job.priority, job.created_at.timestamp(), job))
            self._jobs = new_jobs

            # Cancel running job
            if job_id in self._running_jobs:
                self._running_jobs[job_id].cancel()
                cancelled = True

            if cancelled:
                self._metrics.jobs_cancelled += 1

            return cancelled

    async def _ensure_worker(self) -> None:
        """Ensure the worker loop is running."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

        if self._worker_task is None or self._worker_task.done():
            self._worker_task = self._loop.create_task(self._worker_loop())

    async def _worker_loop(self) -> None:
        """Main worker loop that processes jobs."""
        while not self._closed:
            job = await self._get_next_job()
            if job is None:
                await asyncio.sleep(0.1)
                continue

            task = self._loop.create_task(self._execute_job(job))
            self._running_jobs[job.job_id] = task

            # Limit concurrent jobs
            while len(self._running_jobs) >= self._config.max_concurrent_jobs:
                done, _ = await asyncio.wait(
                    self._running_jobs.values(),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                await self._cleanup_completed_jobs()

            await asyncio.sleep(0)

    async def _get_next_job(self) -> DispatchJob | None:
        """Get the next job from the queue."""
        with self._lock:
            while self._jobs:
                _, _, job = heappop(self._jobs)
                if job.status == EJobStatus.PENDING:
                    return job
        return None

    async def _execute_job(self, job: DispatchJob) -> None:
        """Execute a dispatch job."""
        job.status = EJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        self._metrics.jobs_running += 1

        try:
            result = await asyncio.wait_for(
                self._dispatch_handler(job.record_ids, job.adapter_key),
                timeout=self._config.job_timeout_seconds,
            )
            job.status = EJobStatus.COMPLETED
            job.result = result
            job.completed_at = datetime.utcnow()
            self._metrics.jobs_completed += 1

        except asyncio.CancelledError:
            job.status = EJobStatus.CANCELLED
            self._metrics.jobs_cancelled += 1

        except Exception as e:
            job.status = EJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            self._metrics.jobs_failed += 1

        finally:
            self._metrics.jobs_running -= 1
            if job.job_id in self._running_jobs:
                del self._running_jobs[job.job_id]

    async def _cleanup_completed_jobs(self) -> None:
        """Clean up completed job references."""
        completed = [jid for jid, task in self._running_jobs.items() if task.done()]
        for jid in completed:
            del self._running_jobs[jid]

    def get_metrics(self) -> AsyncDispatchMetrics:
        return AsyncDispatchMetrics(
            jobs_submitted=self._metrics.jobs_submitted,
            jobs_completed=self._metrics.jobs_completed,
            jobs_failed=self._metrics.jobs_failed,
            jobs_cancelled=self._metrics.jobs_cancelled,
            jobs_running=self._metrics.jobs_running,
            pending_jobs=len(self._jobs),
        )

    async def close(self) -> None:
        """Close the executor and cancel all pending jobs."""
        self._closed = True

        # Cancel all running jobs
        for task in self._running_jobs.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Cancel pending jobs
        with self._lock:
            for _, _, job in self._jobs:
                job.status = EJobStatus.CANCELLED


@dataclass
class AsyncDispatchMetrics:
    jobs_submitted: int = 0
    jobs_completed: int = 0
    jobs_failed: int = 0
    jobs_cancelled: int = 0
    jobs_running: int = 0
    pending_jobs: int = 0
```

---

### Phase 3: Adaptive Batching (Depends on Phases 1, 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 3: ADAPTIVE BATCHING                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  3.1 Batch Strategy Types                                                   │
│      ├── EBatchStrategy enum                                               │
│      ├── BatchConfig dataclass                                             │
│      └── BatchMetrics dataclass                                           │
│                                                                             │
│  3.2 Adaptive Batch Controller                                              │
│      ├── Monitor throughput and latency                                    │
│      ├── Adjust batch size dynamically                                     │
│      └── Optimize for throughput vs latency                                │
│                                                                             │
│  3.3 Batch Processor Integration                                             │
│      └── Integrate with async dispatch                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.1.1 Batch Strategy Types

**File:** `logging_system/performance/batching/types.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import threading


class EBatchStrategy(str, Enum):
    FIXED_SIZE = "fixed_size"           # Fixed batch size
    FIXED_TIMEOUT = "fixed_timeout"     # Fixed timeout batches
    ADAPTIVE_THROUGHPUT = "adaptive_throughput"  # Optimize throughput
    ADAPTIVE_LATENCY = "adaptive_latency"  # Optimize latency


@dataclass
class BatchConfig:
    strategy: EBatchStrategy = EBatchStrategy.ADAPTIVE_THROUGHPUT
    min_batch_size: int = 10
    max_batch_size: int = 1000
    target_throughput_rps: float = 1000.0
    target_latency_ms: float = 100.0
    adaptive_window_seconds: float = 10.0
    scale_up_threshold: float = 0.7
    scale_down_threshold: float = 0.3


@dataclass
class BatchMetrics:
    batches_created: int = 0
    records_batched: int = 0
    avg_batch_size: float = 0.0
    avg_latency_ms: float = 0.0
    throughput_rps: float = 0.0
    current_batch_size: int = 0


class AdaptiveBatchController:
    """Controller that adjusts batch size based on observed metrics."""

    def __init__(self, config: BatchConfig) -> None:
        self._config = config
        self._current_batch_size = config.max_batch_size // 2
        self._lock = threading.Lock()
        self._latency_history: list[float] = []
        self._throughput_history: list[float] = []
        self._last_adjustment = datetime.utcnow()

    def get_batch_size(self) -> int:
        """Get the current optimal batch size."""
        with self._lock:
            return self._current_batch_size

    def record_completion(self, batch_size: int, latency_ms: float) -> None:
        """Record batch completion for adaptive adjustment."""
        with self._lock:
            self._latency_history.append(latency_ms)
            self._throughput_history.append(batch_size / latency_ms * 1000)

            # Keep history bounded
            max_history = int(self._config.adaptive_window_seconds * 10)
            if len(self._latency_history) > max_history:
                self._latency_history = self._latency_history[-max_history:]
                self._throughput_history = self._throughput_history[-max_history:]

            # Adjust every adaptive_window_seconds
            if (datetime.utcnow() - self._last_adjustment).total_seconds() >= self._config.adaptive_window_seconds:
                self._adjust_batch_size()

    def _adjust_batch_size(self) -> None:
        """Adjust batch size based on recent metrics."""
        if not self._latency_history:
            return

        avg_latency = sum(self._latency_history) / len(self._latency_history)
        avg_throughput = sum(self._throughput_history) / len(self._throughput_history) if self._throughput_history else 0

        current_size = self._current_batch_size

        match self._config.strategy:
            case EBatchStrategy.ADAPTIVE_THROUGHPUT:
                # Scale up if below target throughput
                if avg_throughput < self._config.target_throughput_rps * self._config.scale_up_threshold:
                    new_size = min(int(current_size * 1.2), self._config.max_batch_size)
                    self._current_batch_size = new_size

                # Scale down if above target
                elif avg_throughput > self._config.target_throughput_rps * (2 - self._config.scale_down_threshold):
                    new_size = max(int(current_size * 0.8), self._config.min_batch_size)
                    self._current_batch_size = new_size

            case EBatchStrategy.ADAPTIVE_LATENCY:
                # Scale down if latency exceeds target
                if avg_latency > self._config.target_latency_ms * 1.5:
                    new_size = max(int(current_size * 0.8), self._config.min_batch_size)
                    self._current_batch_size = new_size

                # Scale up if latency is very low
                elif avg_latency < self._config.target_latency_ms * 0.5:
                    new_size = min(int(current_size * 1.2), self._config.max_batch_size)
                    self._current_batch_size = new_size

        self._last_adjustment = datetime.utcnow()
        self._latency_history.clear()
        self._throughput_history.clear()

    def get_metrics(self) -> BatchMetrics:
        with self._lock:
            avg_latency = sum(self._latency_history) / len(self._latency_history) if self._latency_history else 0
            avg_throughput = sum(self._throughput_history) / len(self._throughput_history) if self._throughput_history else 0

            return BatchMetrics(
                batches_created=0,
                records_batched=0,
                avg_batch_size=self._current_batch_size,
                avg_latency_ms=avg_latency,
                throughput_rps=avg_throughput,
                current_batch_size=self._current_batch_size,
            )
```

---

### Phase 4: Performance Benchmarks (Depends on Phases 1, 2, 3)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 4: PERFORMANCE BENCHMARKS                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  4.1 Benchmark Infrastructure                                              │
│      ├── BenchmarkConfig dataclass                                         │
│      ├── BenchmarkResult dataclass                                          │
│      └── BenchmarkRunner                                                    │
│                                                                             │
│  4.2 Benchmark Suites                                                       │
│      ├── ThroughputBenchmark                                               │
│      ├── LatencyBenchmark                                                  │
│      ├── ConcurrencyBenchmark                                             │
│      └── MemoryBenchmark                                                  │
│                                                                             │
│  4.3 Performance Regression Detection                                        │
│      ├── Baseline comparison                                               │
│      └── Alert on degradation                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 4.1.1 Benchmark Types

**File:** `logging_system/performance/benchmarks/types.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
import statistics


class EBenchmarkType(str, Enum):
    THROUGHPUT = "throughput"
    LATENCY = "latency"
    CONCURRENCY = "concurrency"
    MEMORY = "memory"
    END_TO_END = "end_to_end"


@dataclass
class BenchmarkConfig:
    benchmark_type: EBenchmarkType
    duration_seconds: float = 10.0
    warmup_seconds: float = 2.0
    concurrency: int = 1
    record_size_bytes: int = 512
    batch_size: int = 100
    iterations: int | None = None  # Override duration with iterations


@dataclass
class BenchmarkResult:
    benchmark_type: EBenchmarkType
    config: BenchmarkConfig
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    total_records: int
    total_operations: int
    
    # Throughput metrics
    records_per_second: float | None = None
    operations_per_second: float | None = None
    
    # Latency metrics
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    latency_p99_ms: float | None = None
    latency_p999_ms: float | None = None
    latency_max_ms: float | None = None
    latency_avg_ms: float | None = None
    
    # Memory metrics
    memory_peak_mb: float | None = None
    memory_avg_mb: float | None = None
    
    # Error metrics
    errors: int = 0
    error_rate: float = 0.0
    
    # Raw data
    latencies: list[float] = field(default_factory=list)
    
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.benchmark_type.value,
            "duration_seconds": self.duration_seconds,
            "total_records": self.total_records,
            "records_per_second": self.records_per_second,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "memory_peak_mb": self.memory_peak_mb,
            "errors": self.errors,
            "error_rate": self.error_rate,
        }


class BenchmarkRunner:
    """Runner for executing benchmarks."""

    def __init__(self) -> None:
        self._results: list[BenchmarkResult] = []

    async def run(
        self,
        config: BenchmarkConfig,
        operation: Callable[..., Any],
        setup: Callable[[], Any] | None = None,
        teardown: Callable[[Any], None] | None = None,
    ) -> BenchmarkResult:
        """Run a benchmark with the given configuration."""
        import time
        import asyncio

        context = setup() if setup else None
        start_time = datetime.utcnow()
        latencies: list[float] = []
        total_records = 0
        total_operations = 0
        errors = 0

        # Warmup
        await self._warmup(config, operation, context)

        # Main benchmark loop
        end_time = start_time + datetime.timedelta(seconds=config.duration_seconds)
        while datetime.utcnow() < end_time:
            iter_start = time.perf_counter()
            
            try:
                if asyncio.iscoroutinefunction(operation):
                    await operation(context)
                else:
                    operation(context)
                
                iter_end = time.perf_counter()
                latencies.append((iter_end - iter_start) * 1000)
                total_operations += 1
                total_records += config.batch_size
                
            except Exception:
                errors += 1

        if teardown and context:
            teardown(context)

        completed_at = datetime.utcnow()
        duration = (completed_at - start_time).total_seconds()

        # Calculate metrics
        result = self._calculate_metrics(
            config=config,
            start_time=start_time,
            completed_at=completed_at,
            duration=duration,
            total_records=total_records,
            total_operations=total_operations,
            latencies=latencies,
            errors=errors,
        )

        self._results.append(result)
        return result

    async def _warmup(
        self,
        config: BenchmarkConfig,
        operation: Callable,
        context: Any,
    ) -> None:
        """Warmup phase to stabilize JIT/cache."""
        import asyncio
        
        warmup_end = datetime.utcnow() + datetime.timedelta(seconds=config.warmup_seconds)
        warmup_ops = 0
        
        while datetime.utcnow() < warmup_end:
            try:
                if asyncio.iscoroutinefunction(operation):
                    await operation(context)
                else:
                    operation(context)
                warmup_ops += 1
            except Exception:
                pass

    def _calculate_metrics(
        self,
        config: BenchmarkConfig,
        start_time: datetime,
        completed_at: datetime,
        duration: float,
        total_records: int,
        total_operations: int,
        latencies: list[float],
        errors: int,
    ) -> BenchmarkResult:
        """Calculate benchmark metrics."""
        sorted_latencies = sorted(latencies) if latencies else []
        
        def percentile(data: list, p: float) -> float:
            if not data:
                return 0.0
            idx = int(len(data) * p)
            return data[min(idx, len(data) - 1)]

        return BenchmarkResult(
            benchmark_type=config.benchmark_type,
            config=config,
            started_at=start_time,
            completed_at=completed_at,
            duration_seconds=duration,
            total_records=total_records,
            total_operations=total_operations,
            records_per_second=total_records / duration if duration > 0 else 0,
            operations_per_second=total_operations / duration if duration > 0 else 0,
            latency_p50_ms=percentile(sorted_latencies, 0.50),
            latency_p95_ms=percentile(sorted_latencies, 0.95),
            latency_p99_ms=percentile(sorted_latencies, 0.99),
            latency_p999_ms=percentile(sorted_latencies, 0.999),
            latency_max_ms=max(latencies) if latencies else 0,
            latency_avg_ms=sum(latencies) / len(latencies) if latencies else 0,
            errors=errors,
            error_rate=errors / total_operations if total_operations > 0 else 0,
            latencies=sorted_latencies,
        )

    def compare_with_baseline(self, result: BenchmarkResult) -> dict[str, Any]:
        """Compare result with historical baseline."""
        if not self._results:
            return {"has_baseline": False}

        baseline = self._results[-1]
        
        return {
            "has_baseline": True,
            "baseline": baseline.to_dict(),
            "current": result.to_dict(),
            "throughput_delta_pct": (
                (result.records_per_second - baseline.records_per_second) / baseline.records_per_second * 100
                if baseline.records_per_second > 0 else 0
            ),
            "latency_delta_pct": (
                (result.latency_avg_ms - baseline.latency_avg_ms) / baseline.latency_avg_ms * 100
                if baseline.latency_avg_ms > 0 else 0
            ),
            "regression_detected": (
                result.records_per_second < baseline.records_per_second * 0.9 or
                result.latency_avg_ms > baseline.latency_avg_ms * 1.1
            ),
        }
```

---

## File Structure After Implementation

```
logging_system/
├── performance/
│   ├── __init__.py
│   ├── connection_pool/
│   │   ├── __init__.py
│   │   ├── types.py          # Phase 1
│   │   └── pool.py          # Phase 1
│   ├── async_dispatch/
│   │   ├── __init__.py
│   │   ├── types.py         # Phase 2
│   │   └── executor.py      # Phase 2
│   ├── batching/
│   │   ├── __init__.py
│   │   ├── types.py         # Phase 3
│   │   └── controller.py   # Phase 3
│   └── benchmarks/
│       ├── __init__.py
│       ├── types.py         # Phase 4
│       └── runner.py       # Phase 4
```

---

## Contract Additions

| Contract | Name | Purpose |
|----------|------|---------|
| 37 | `37_LoggingSystem_ConnectionPool_Contract.template.yaml` | Connection pool contract |
| 38 | `38_LoggingSystem_AsyncDispatch_Contract.template.yaml` | Async dispatch contract |
| 39 | `39_LoggingSystem_AdaptiveBatching_Contract.template.yaml` | Batching contract |

---

## Performance Targets

| Metric | Current | Target |
|--------|---------|--------|
| Throughput | ~500 RPS | > 5000 RPS |
| p99 Latency | ~100ms | < 50ms |
| Memory/1M records | ~500MB | < 200MB |
| Connection acquire | N/A | < 10ms |

---

**Estimated Implementation Time:** 3-4 weeks  
**Estimated Effort:** ~2500 lines of new code  
**Risk Level:** Medium (performance-critical changes)
