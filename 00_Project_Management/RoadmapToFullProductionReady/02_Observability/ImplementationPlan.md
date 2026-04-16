# Observability - Implementation Roadmap

**Current Score:** 6/10  
**Target Score:** 9/10  
**Priority:** HIGH

---

## Executive Summary

The logging system has basic observability through audit trails and counters, but lacks comprehensive metrics export, health endpoints, and distributed tracing integration. Production deployments require deeper insight into system health, performance, and correlation capabilities.

---

## Gap Analysis

| Gap | Severity | Current State | Target State |
|-----|----------|---------------|--------------|
| Health Endpoint | CRITICAL | None | `/health`, `/ready`, `/live` endpoints |
| Metrics Export | CRITICAL | Basic counters | Prometheus/OpenTelemetry metrics |
| Distributed Tracing | HIGH | W3C referenced | Full trace context propagation |
| Structured Logging Enhancement | MEDIUM | Basic payload | Correlation IDs, spans |
| Alert Rules | MEDIUM | None | Predefined alerting rules |
| Dashboard Templates | LOW | None | Grafana dashboard JSON |

---

## Implementation Phases (Dependency-Ordered)

### Phase 1: Health Check System (No Dependencies)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: HEALTH CHECKS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  1.1 Health Status Enumeration                                             │
│      ├── EHealthStatus enum (HEALTHY, DEGRADED, UNHEALTHY)                │
│      ├── HealthCheckResult dataclass                                       │
│      └── HealthCheckConfig dataclass                                        │
│                                                                             │
│  1.2 Health Check Interface                                                 │
│      ├── IHealthCheck port interface                                       │
│      ├── CompositeHealthCheck for aggregates                                │
│      └── Dependency injection support                                       │
│                                                                             │
│  1.3 Built-in Health Checks                                                 │
│      ├── AdapterHealthCheck                                                │
│      ├── ContainerHealthCheck                                              │
│      ├── DLQHealthCheck                                                    │
│      └── StateStoreHealthCheck                                             │
│                                                                             │
│  1.4 Health Endpoint Implementation                                         │
│      ├── /health (aggregated health)                                      │
│      ├── /health/ready (readiness probe)                                  │
│      └── /health/live (liveness probe)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 1.1.1 Health Check Types

**File:** `logging_system/observability/health/types.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.request import urlopen
import time


class EHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class HealthCheckResult:
    name: str
    status: EHealthStatus
    message: str | None = None
    details: dict[str, Any] | None = None
    checked_at_utc: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    duration_ms: float | None = None

    def is_healthy(self) -> bool:
        return self.status == EHealthStatus.HEALTHY

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "checked_at_utc": self.checked_at_utc,
            "duration_ms": self.duration_ms,
        }


@dataclass
class HealthReport:
    overall_status: EHealthStatus
    checks: list[HealthCheckResult]
    timestamp_utc: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.overall_status.value,
            "checks": [c.to_dict() for c in self.checks],
            "timestamp_utc": self.timestamp_utc,
            "version": self.version,
        }
```

#### 1.2.1 Health Check Interface

**File:** `logging_system/observability/health/interfaces.py`

```python
from __future__ import annotations
from typing import Protocol

from .types import HealthCheckResult


class IHealthCheck(Protocol):
    def name(self) -> str:
        ...

    async def check(self) -> HealthCheckResult:
        ...

    def is_critical(self) -> bool:
        ...
```

#### 1.3.1 Built-in Health Checks

**File:** `logging_system/observability/health/checks.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
import asyncio

from .interfaces import IHealthCheck
from .types import EHealthStatus, HealthCheckResult

if TYPE_CHECKING:
    from logging_system.services.logging_service import LoggingService


class AdapterHealthCheck(IHealthCheck):
    def __init__(self, service: LoggingService) -> None:
        self._service = service

    def name(self) -> str:
        return "adapter"

    def is_critical(self) -> bool:
        return True

    async def check(self) -> HealthCheckResult:
        start = datetime.utcnow()
        try:
            evidence = self._service.collect_operational_evidence()
            adapters = evidence.get("available_adapters", [])

            if not adapters:
                return HealthCheckResult(
                    name=self.name(),
                    status=EHealthStatus.UNHEALTHY,
                    message="No adapters available",
                    duration_ms=self._duration_ms(start),
                )

            return HealthCheckResult(
                name=self.name(),
                status=EHealthStatus.HEALTHY,
                message=f"{len(adapters)} adapters available",
                details={"adapters": adapters},
                duration_ms=self._duration_ms(start),
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name(),
                status=EHealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=self._duration_ms(start),
            )

    def _duration_ms(self, start: datetime) -> float:
        return (datetime.utcnow() - start).total_seconds() * 1000


class ContainerHealthCheck(IHealthCheck):
    def __init__(self, service: LoggingService) -> None:
        self._service = service

    def name(self) -> str:
        return "container"

    def is_critical(self) -> bool:
        return True

    async def check(self) -> HealthCheckResult:
        start = datetime.utcnow()
        try:
            evidence = self._service.collect_operational_evidence()
            queue_depth = evidence.get("queue_depth", 0)
            max_records = evidence.get("max_records", 0)

            # Degraded if queue > 80% capacity
            if max_records > 0 and queue_depth / max_records > 0.8:
                return HealthCheckResult(
                    name=self.name(),
                    status=EHealthStatus.DEGRADED,
                    message=f"Queue at {queue_depth/max_records*100:.1f}% capacity",
                    details={"queue_depth": queue_depth, "max_records": max_records},
                    duration_ms=self._duration_ms(start),
                )

            return HealthCheckResult(
                name=self.name(),
                status=EHealthStatus.HEALTHY,
                message=f"Queue at {queue_depth/max_records*100:.1f}% capacity",
                details={"queue_depth": queue_depth, "max_records": max_records},
                duration_ms=self._duration_ms(start),
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name(),
                status=EHealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=self._duration_ms(start),
            )

    def _duration_ms(self, start: datetime) -> float:
        return (datetime.utcnow() - start).total_seconds() * 1000


class DLQHealthCheck(IHealthCheck):
    def __init__(self, dlq) -> None:
        self._dlq = dlq

    def name(self) -> str:
        return "dead_letter_queue"

    def is_critical(self) -> bool:
        return False

    async def check(self) -> HealthCheckResult:
        start = datetime.utcnow()
        try:
            stats = self._dlq.get_statistics()
            failed_count = stats.failed_count
            pending_count = stats.pending_count

            # Critical if failed > 100
            if failed_count > 100:
                return HealthCheckResult(
                    name=self.name(),
                    status=EHealthStatus.UNHEALTHY,
                    message=f"{failed_count} failed entries need attention",
                    details={"failed": failed_count, "pending": pending_count},
                    duration_ms=self._duration_ms(start),
                )

            # Degraded if pending > 1000
            if pending_count > 1000:
                return HealthCheckResult(
                    name=self.name(),
                    status=EHealthStatus.DEGRADED,
                    message=f"{pending_count} entries awaiting retry",
                    details={"failed": failed_count, "pending": pending_count},
                    duration_ms=self._duration_ms(start),
                )

            return HealthCheckResult(
                name=self.name(),
                status=EHealthStatus.HEALTHY,
                message="DLQ healthy",
                details={"failed": failed_count, "pending": pending_count},
                duration_ms=self._duration_ms(start),
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name(),
                status=EHealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=self._duration_ms(start),
            )

    def _duration_ms(self, start: datetime) -> float:
        return (datetime.utcnow() - start).total_seconds() * 1000
```

#### 1.4.1 Health Endpoint

**File:** `logging_system/observability/health/endpoint.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .interfaces import IHealthCheck
    from .types import EHealthStatus, HealthReport


@dataclass
class HealthEndpointConfig:
    timeout_seconds: float = 5.0
    include_details: bool = True
    cache_ttl_seconds: float = 1.0


class HealthEndpoint:
    def __init__(
        self,
        checks: list[IHealthCheck],
        config: HealthEndpointConfig | None = None,
    ) -> None:
        self._checks = checks
        self._config = config or HealthEndpointConfig()
        self._cached_report: HealthReport | None = None
        self._cache_time: float = 0.0

    async def get_health(self) -> HealthReport:
        results = []
        for check in self._checks:
            result = await check.check()
            results.append(result)

        overall = self._determine_overall_status(results)

        return HealthReport(
            overall_status=overall,
            checks=results,
        )

    async def get_ready(self) -> HealthReport:
        results = []
        for check in self._checks:
            if check.is_critical():
                result = await check.check()
                results.append(result)

        # Readiness = all critical checks healthy
        all_healthy = all(r.is_healthy() for r in results)
        overall = EHealthStatus.HEALTHY if all_healthy else EHealthStatus.UNHEALTHY

        return HealthReport(overall_status=overall, checks=results)

    async def get_live(self) -> HealthReport:
        # Liveness = basic responsiveness
        return HealthReport(
            overall_status=EHealthStatus.HEALTHY,
            checks=[
                HealthCheckResult(
                    name="process",
                    status=EHealthStatus.HEALTHY,
                    message="Process is running",
                )
            ],
        )

    def _determine_overall_status(self, results: list[HealthCheckResult]) -> EHealthStatus:
        if any(r.status == EHealthStatus.UNHEALTHY for r in results):
            # Check if critical
            unhealthy_critical = any(
                r.status == EHealthStatus.UNHEALTHY and self._is_critical_check(r.name)
                for r in results
            )
            return EHealthStatus.UNHEALTHY if unhealthy_critical else EHealthStatus.DEGRADED

        if any(r.status == EHealthStatus.DEGRADED for r in results):
            return EHealthStatus.DEGRADED

        return EHealthStatus.HEALTHY

    def _is_critical_check(self, name: str) -> bool:
        return any(c.name() == name and c.is_critical() for c in self._checks)
```

---

### Phase 2: Metrics System (Depends on Phase 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 2: METRICS                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  2.1 Metrics Types and Registries                                           │
│      ├── EMetricType enum (COUNTER, GAUGE, HISTOGRAM, SUMMARY)           │
│      ├── MetricValue dataclass                                            │
│      └── MetricRegistry                                                    │
│                                                                             │
│  2.2 Metric Instruments                                                     │
│      ├── Counter for cumulative counts                                     │
│      ├── Gauge for point-in-time values                                    │
│      ├── Histogram for distributions                                       │
│      └── Summary for quantiles                                             │
│                                                                             │
│  2.3 Metrics Exporters                                                     │
│      ├── PrometheusExporter                                                │
│      ├── OpenTelemetryExporter                                             │
│      └── InMemoryMetricsStore                                              │
│                                                                             │
│  2.4 Logging Service Metrics Integration                                     │
│      ├── Emit metrics (logs_emitted_total, logs_dispatched_total)         │
│      ├── Queue metrics (queue_depth, max_queue_depth)                     │
│      └── Adapter metrics (adapter_calls_total, adapter_errors_total)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.1.1 Metrics Types

**File:** `logging_system/observability/metrics/types.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import threading


class EMetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass(frozen=True)
class MetricMetadata:
    name: str
    description: str
    unit: str | None = None
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricValue:
    value: float
    timestamp_utc: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class CounterValue:
    value: float = 0.0
    total: float = 0.0


@dataclass
class GaugeValue:
    value: float = 0.0


@dataclass
class HistogramValue:
    count: int = 0
    sum: float = 0.0
    buckets: dict[float, int] = field(default_factory=dict)  # upper_bound -> count


class MetricRegistry:
    def __init__(self) -> None:
        self._counters: dict[str, CounterValue] = {}
        self._gauges: dict[str, GaugeValue] = {}
        self._histograms: dict[str, HistogramValue] = {}
        self._lock = threading.RLock()

    def counter(self, name: str, labels: dict[str, str] | None = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._counters:
                self._counters[key] = CounterValue()
            self._counters[key].total += 1
            self._counters[key].value = self._counters[key].total

    def gauge_set(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._gauges:
                self._gauges[key] = GaugeValue()
            self._gauges[key].value = value

    def gauge_inc(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._gauges:
                self._gauges[key] = GaugeValue()
            self._gauges[key].value += value

    def histogram_observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = HistogramValue(
                    buckets={0.005: 0, 0.01: 0, 0.025: 0, 0.05: 0, 0.1: 0, 0.25: 0, 0.5: 0, 1.0: 0, 2.5: 0, 5.0: 0, 10.0: 0}
                )
            h = self._histograms[key]
            h.count += 1
            h.sum += value
            for bound in h.buckets:
                if value <= bound:
                    h.buckets[bound] += 1

    def _make_key(self, name: str, labels: dict[str, str] | None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def collect(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": {k: {"value": v.value, "total": v.total} for k, v in self._counters.items()},
                "gauges": {k: {"value": v.value} for k, v in self._gauges.items()},
                "histograms": {
                    k: {"count": v.count, "sum": v.sum, "buckets": v.buckets}
                    for k, v in self._histograms.items()
                },
            }
```

#### 2.2.1 Prometheus Exporter

**File:** `logging_system/observability/metrics/exporters/prometheus.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logging_system.observability.metrics.types import MetricRegistry


class PrometheusExporter:
    def __init__(self, registry: MetricRegistry) -> None:
        self._registry = registry

    def export(self) -> str:
        lines = []
        metrics = self._registry.collect()

        # Counters
        for key, data in metrics["counters"].items():
            lines.append(f"# TYPE {key} counter")
            lines.append(f"{key} {data['value']}")

        # Gauges
        for key, data in metrics["gauges"].items():
            lines.append(f"# TYPE {key} gauge")
            lines.append(f"{key} {data['value']}")

        # Histograms
        for key, data in metrics["histograms"].items():
            base_name = key.split("{")[0]
            lines.append(f"# TYPE {base_name} histogram")
            lines.append(f"{base_name}_count{key[len(base_name):] if key != base_name else ''} {data['count']}")
            lines.append(f"{base_name}_sum{key[len(base_name):] if key != base_name else ''} {data['sum']}")
            for bound, count in data["buckets"].items():
                bucket_labels = key.strip("{}") if "{" in key else ""
                suffix = f"{{{bucket_labels},le={bound}}}" if bucket_labels else f"{{le={bound}}}"
                lines.append(f"{base_name}_bucket{suffix} {count}")

        return "\n".join(lines)
```

---

### Phase 3: Distributed Tracing (Depends on Phases 1, 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 3: DISTRIBUTED TRACING                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  3.1 Trace Context Types                                                    │
│      ├── TraceContext dataclass                                            │
│      ├── SpanStatus enum                                                   │
│      └── SpanKind enum                                                     │
│                                                                             │
│  3.2 Trace Integration                                                      │
│      ├── Inject/extract trace context to log records                       │
│      ├── Auto-create spans for dispatch operations                         │
│      └── W3C TraceContext propagation                                     │
│                                                                             │
│  3.3 Trace Attributes                                                      │
│      ├── Resource attributes (service.name, service.version)              │
│      ├── Span attributes (log.level, record_id, adapter_key)            │
│      └── Events for key log lifecycle events                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.1.1 Trace Context Types

**File:** `logging_system/observability/tracing/types.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ESpanKind(str, Enum):
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class ESpanStatus(str, Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass(frozen=True)
class SpanContext:
    trace_id: str
    span_id: str
    trace_flags: str = "01"
    trace_state: str = ""
    remote: bool = False


@dataclass
class Span:
    name: str
    context: SpanContext
    kind: ESpanKind = ESpanKind.INTERNAL
    status: ESpanStatus = ESpanStatus.UNSET
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    links: list[SpanContext] = field(default_factory=list)
    parent_span_id: str | None = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append({
            "name": name,
            "timestamp_utc": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })

    def set_status(self, status: ESpanStatus, description: str | None = None) -> None:
        self.status = status

    def end(self) -> None:
        self.end_time = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "context": {
                "trace_id": self.context.trace_id,
                "span_id": self.context.span_id,
                "trace_flags": self.context.trace_flags,
            },
            "kind": self.kind.value,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "attributes": self.attributes,
            "events": self.events,
            "links": [{"trace_id": lc.trace_id, "span_id": lc.span_id} for lc in self.links],
            "parent_span_id": self.parent_span_id,
        }


@dataclass
class TraceConfig:
    service_name: str = "logging-system"
    service_version: str = "1.0.0"
    enabled: bool = True
    export_batch_size: int = 100
    export_timeout_ms: int = 5000
```

#### 3.2.1 Trace Context Propagation

**File:** `logging_system/observability/tracing/propagation.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
import uuid

from .types import Span, SpanContext, ESpanKind, ESpanStatus

if TYPE_CHECKING:
    from logging_system.models.record import LogRecord


class W3CTraceContextPropagator:
    TRACE_VERSION = "00"
    TRACEPARENT_HEADER = "traceparent"
    TRACESTATE_HEADER = "tracestate"

    @staticmethod
    def inject_context(record: LogRecord, carrier: dict[str, str]) -> dict[str, str]:
        trace_id = record.payload.get("trace_id", W3CTraceContextPropagator._generate_trace_id())
        span_id = W3CTraceContextPropagator._generate_span_id()

        traceparent = f"{W3CTraceContextPropagator.TRACE_VERSION}-{trace_id}-{span_id}-01"
        carrier[W3CTraceContextPropagator.TRACEPARENT_HEADER] = traceparent

        return carrier

    @staticmethod
    def extract_context(carrier: dict[str, str]) -> SpanContext | None:
        traceparent = carrier.get(W3CTraceContextPropagator.TRACEPARENT_HEADER)
        if not traceparent:
            return None

        parts = traceparent.split("-")
        if len(parts) != 4:
            return None

        return SpanContext(
            trace_id=parts[1],
            span_id=parts[2],
            trace_flags=parts[3],
            remote=True,
        )

    @staticmethod
    def _generate_trace_id() -> str:
        return uuid.uuid4().hex[:32]

    @staticmethod
    def _generate_span_id() -> str:
        return uuid.uuid4().hex[:16]


class TracingDecorator:
    def __init__(self, tracer) -> None:
        self._tracer = tracer

    def start_span(
        self,
        name: str,
        kind: ESpanKind = ESpanKind.INTERNAL,
        parent_context: SpanContext | None = None,
        attributes: dict | None = None,
    ) -> Span:
        span_id = W3CTraceContextPropagator._generate_span_id()
        trace_id = parent_context.trace_id if parent_context else W3CTraceContextPropagator._generate_trace_id()

        parent_span_id = parent_context.span_id if parent_context else None

        span = Span(
            name=name,
            context=SpanContext(trace_id=trace_id, span_id=span_id),
            kind=kind,
            parent_span_id=parent_span_id,
        )

        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        return span
```

---

### Phase 4: Health Endpoint Server (Depends on Phase 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   PHASE 4: HEALTH ENDPOINT SERVER                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  4.1 HTTP Server for Health Endpoints                                       │
│      ├── Async HTTP server using aiohttp                                   │
│      ├── GET /health                                                       │
│      ├── GET /health/ready                                                 │
│      └── GET /health/live                                                  │
│                                                                             │
│  4.2 Metrics Endpoint                                                       │
│      ├── GET /metrics (Prometheus format)                                 │
│      └── GET /metrics/json                                                 │
│                                                                             │
│  4.3 Integration with LoggingService                                         │
│      ├── Auto-register health checks                                       │
│      └── Wire up metrics registry                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 4.1.1 Health Server

**File:** `logging_system/observability/server/health_server.py`

```python
from __future__ import annotations
from dataclasses import dataclass
import asyncio
from aiohttp import web
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logging_system.observability.health.endpoint import HealthEndpoint
    from logging_system.observability.metrics.exporters.prometheus import PrometheusExporter


@dataclass
class ObservabilityServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    enable_health: bool = True
    enable_metrics: bool = True


class ObservabilityServer:
    def __init__(
        self,
        health_endpoint: HealthEndpoint,
        prometheus_exporter: PrometheusExporter,
        config: ObservabilityServerConfig | None = None,
    ) -> None:
        self._health = health_endpoint
        self._metrics = prometheus_exporter
        self._config = config or ObservabilityServerConfig()
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        self._app = web.Application()
        self._setup_routes()
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._config.host, self._config.port)
        await site.start()

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()

    def _setup_routes(self) -> None:
        if not self._app:
            return

        if self._config.enable_health:
            self._app.router.add_get("/health", self._handle_health)
            self._app.router.add_get("/health/ready", self._handle_ready)
            self._app.router.add_get("/health/live", self._handle_live)

        if self._config.enable_metrics:
            self._app.router.add_get("/metrics", self._handle_metrics)
            self._app.router.add_get("/metrics/json", self._handle_metrics_json)

    async def _handle_health(self, request: web.Request) -> web.Response:
        report = await self._health.get_health()
        status = 200 if report.overall_status.value == "healthy" else 503
        return web.json_response(report.to_dict(), status=status)

    async def _handle_ready(self, request: web.Request) -> web.Response:
        report = await self._health.get_ready()
        status = 200 if report.overall_status.value == "healthy" else 503
        return web.json_response(report.to_dict(), status=status)

    async def _handle_live(self, request: web.Request) -> web.Response:
        report = await self._health.get_live()
        return web.json_response(report.to_dict())

    async def _handle_metrics(self, request: web.Request) -> web.Response:
        return web.Response(text=self._metrics.export(), content_type="text/plain")

    async def _handle_metrics_json(self, request: web.Request) -> web.Response:
        return web.json_response(self._metrics._registry.collect())
```

---

### Phase 5: Dashboard and Alerting (Depends on Phases 2, 4)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 5: DASHBOARD & ALERTING                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  5.1 Grafana Dashboard Template                                             │
│      ├── Logs Overview Panel                                                │
│      ├── Queue Depth Panel                                                  │
│      ├── Dispatch Latency Panel                                             │
│      ├── Error Rate Panel                                                   │
│      └── DLQ Health Panel                                                  │
│                                                                             │
│  5.2 Alert Rules                                                           │
│      ├── HighQueueDepth alert                                              │
│      ├── HighErrorRate alert                                               │
│      ├── CircuitBreakerOpen alert                                         │
│      └── DLQFailingEntries alert                                          │
│                                                                             │
│  5.3 Integration Tests                                                      │
│      └── End-to-end observability pipeline                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 5.1.1 Grafana Dashboard JSON

**File:** `logging_system/observability/dashboard/grafana_dashboard.json`

```json
{
  "dashboard": {
    "title": "Py_LoggingSystem - Production Dashboard",
    "uid": "py_logging_system",
    "panels": [
      {
        "title": "Logs Emitted / Minute",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(logs_emitted_total[1m])",
            "legendFormat": "Emitted/s"
          }
        ]
      },
      {
        "title": "Logs Dispatched / Minute",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(logs_dispatched_total[1m])",
            "legendFormat": "Dispatched/s"
          }
        ]
      },
      {
        "title": "Queue Depth",
        "type": "gauge",
        "targets": [
          {
            "expr": "queue_depth",
            "legendFormat": "Current"
          }
        ],
        "fieldConfig": {
          "thresholds": {
            "steps": [
              {"value": 0, "color": "green"},
              {"value": 5000, "color": "yellow"},
              {"value": 8000, "color": "red"}
            ]
          }
        }
      },
      {
        "title": "Dispatch Latency (p95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, dispatch_latency_seconds_bucket)",
            "legendFormat": "p95"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(logs_dispatch_errors_total[5m])",
            "legendFormat": "Errors/s"
          }
        ]
      },
      {
        "title": "DLQ Entries",
        "type": "stat",
        "targets": [
          {
            "expr": "dlq_entries_total",
            "legendFormat": "Total"
          }
        ]
      },
      {
        "title": "Circuit Breaker Status",
        "type": "table",
        "targets": [
          {
            "expr": "circuit_breaker_state",
            "format": "table"
          }
        ]
      }
    ],
    "templating": {
      "variables": [
        {
          "name": "instance",
          "type": "query",
          "query": "label_values(queue_depth, instance)"
        }
      ]
    }
  }
}
```

#### 5.2.1 Alert Rules

**File:** `logging_system/observability/alerts/alert_rules.yaml`

```yaml
alerts:
  - name: HighQueueDepth
    expr: "queue_depth > 8000"
    for: "5m"
    severity: warning
    summary: "Queue depth exceeds 8000"
    description: "Queue depth has been above 8000 for 5 minutes. Consider scaling or investigating backpressure."
    annotations:
      runbook_url: "https://wiki.example.com/runbooks/high-queue-depth"

  - name: CriticalQueueDepth
    expr: "queue_depth > 9500"
    for: "1m"
    severity: critical
    summary: "Queue depth critically high"
    description: "Queue depth exceeds 95% of maximum. Immediate action required."
    annotations:
      runbook_url: "https://wiki.example.com/runbooks/critical-queue"

  - name: HighErrorRate
    expr: "rate(logs_dispatch_errors_total[5m]) > 0.1"
    for: "5m"
    severity: warning
    summary: "High dispatch error rate"
    description: "Dispatch error rate exceeds 10% over 5 minutes."
    annotations:
      runbook_url: "https://wiki.example.com/runbooks/high-error-rate"

  - name: CircuitBreakerOpen
    expr: "circuit_breaker_state == 2"  # 2 = OPEN
    for: "1m"
    severity: critical
    summary: "Circuit breaker is open"
    description: "Adapter circuit breaker has opened. Dispatch may be degraded."
    annotations:
      runbook_url: "https://wiki.example.com/runbooks/circuit-breaker-open"

  - name: DLQFailingEntries
    expr: "dlq_entries_failed > 100"
    for: "10m"
    severity: warning
    summary: "DLQ has failing entries"
    description: "Over 100 entries in DLQ are failing after max retries. Manual investigation required."
    annotations:
      runbook_url: "https://wiki.example.com/runbooks/dlq-investigation"

  - name: HighDispatchLatency
    expr: "histogram_quantile(0.95, dispatch_latency_seconds_bucket) > 1"
    for: "5m"
    severity: warning
    summary: "High dispatch latency"
    description: "p95 dispatch latency exceeds 1 second."
    annotations:
      runbook_url: "https://wiki.example.com/runbooks/high-latency"
```

---

## File Structure After Implementation

```
logging_system/
├── observability/
│   ├── __init__.py
│   ├── health/
│   │   ├── __init__.py
│   │   ├── types.py              # Phase 1
│   │   ├── interfaces.py        # Phase 1
│   │   ├── checks.py            # Phase 1
│   │   ├── endpoint.py          # Phase 1
│   │   └── server.py            # Phase 4
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── types.py             # Phase 2
│   │   ├── registry.py          # Phase 2
│   │   └── exporters/
│   │       ├── __init__.py
│   │       ├── prometheus.py    # Phase 2
│   │       └── otel.py          # Phase 2
│   ├── tracing/
│   │   ├── __init__.py
│   │   ├── types.py             # Phase 3
│   │   ├── propagation.py       # Phase 3
│   │   └── context.py           # Phase 3
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── grafana_dashboard.json # Phase 5
│   │   └── prometheus_rules.yaml  # Phase 5
│   └── alerts/
│       ├── __init__.py
│       └── alert_rules.yaml     # Phase 5
```

---

## Contract Additions

| Contract | Name | Purpose |
|----------|------|---------|
| 30 | `30_LoggingSystem_HealthCheck_Contract.template.yaml` | Health check interface contract |
| 31 | `31_LoggingSystem_Metrics_Contract.template.yaml` | Metrics types and registry contract |
| 32 | `32_LoggingSystem_Tracing_Contract.template.yaml` | Distributed tracing contract |

---

## Test Plan

| Phase | Tests | Focus |
|-------|-------|-------|
| 1 | 15 | Health check registration, status determination |
| 2 | 20 | Counter/gauge/histogram operations, export formats |
| 3 | 15 | Context propagation, span lifecycle |
| 4 | 10 | HTTP endpoints, status codes |
| 5 | 10 | Dashboard rendering, alert rule validation |

---

## Metrics to Track

| Metric | Type | Description |
|--------|------|-------------|
| `logs_emitted_total` | Counter | Total logs emitted |
| `logs_dispatched_total` | Counter | Total logs dispatched |
| `logs_dispatch_errors_total` | Counter | Failed dispatches |
| `logs_evicted_total` | Counter | Evicted due to retention |
| `queue_depth` | Gauge | Current pending records |
| `dispatch_latency_seconds` | Histogram | Dispatch timing |
| `dlq_entries_total` | Gauge | DLQ size by status |
| `circuit_breaker_state` | Gauge | Per-adapter CB state |
| `adapter_calls_total` | Counter | Adapter invocations |

---

## Dependencies on Other Roadmaps

| This Phase | Depends On |
|------------|-----------|
| All | Error Handling & Resilience (Phase 1) - DLQ health check |

---

**Estimated Implementation Time:** 3-4 weeks  
**Estimated Effort:** ~2500 lines of new code  
**Risk Level:** Medium (adds new HTTP server component)
