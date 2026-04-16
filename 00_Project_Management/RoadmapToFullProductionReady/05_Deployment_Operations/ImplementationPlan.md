# Deployment & Operations - Implementation Roadmap

**Current Score:** 4/10  
**Target Score:** 9/10  
**Priority:** HIGH

---

## Executive Summary

The logging system lacks production deployment infrastructure including Docker support, health endpoints, graceful shutdown, environment configuration, and operational tooling. These gaps prevent reliable production deployments.

---

## Gap Analysis

| Gap | Severity | Current State | Target State |
|-----|----------|---------------|--------------|
| Docker Support | CRITICAL | None | Multi-stage Dockerfile |
| Health Endpoints | CRITICAL | None | /health, /ready, /live |
| Graceful Shutdown | CRITICAL | None | Drain + shutdown |
| Environment Config | HIGH | Manual | Environment variables |
| Helm Charts | MEDIUM | None | Kubernetes deployment |
| CI/CD Pipeline | HIGH | None | GitHub Actions |
| Container Registry | MEDIUM | None | ghcr.io setup |

---

## Implementation Phases (Dependency-Ordered)

### Phase 1: Docker Support (No Dependencies)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PHASE 1: DOCKER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  1.1 Multi-stage Dockerfile                                                 │
│      ├── Builder stage with all dependencies                                │
│      ├── Minimal runtime stage                                            │
│      └── Non-root user for security                                        │
│                                                                             │
│  1.2 Docker Configuration Files                                             │
│      ├── .dockerignore                                                     │
│      ├── docker-compose.yml for local dev                                  │
│      └── .dockerenv for defaults                                          │
│                                                                             │
│  1.3 Container Security Hardening                                         │
│      ├── Read-only filesystem                                              │
│      ├── No new privileges                                                │
│      └── Resource limits                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 1.1.1 Multi-stage Dockerfile

**File:** `Dockerfile`

```dockerfile
# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency files
COPY requirements.txt requirements.lock* /tmp/

# Install dependencies (layer caching)
RUN if [ -f /tmp/requirements.lock ]; then \
        pip install --no-cache-dir -r /tmp/requirements.lock; \
    else \
        pip install --no-cache-dir -r /tmp/requirements.txt; \
    fi

# Copy source code
COPY . /app
WORKDIR /app

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.11-slim as runtime

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/false --create-home appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy only necessary application files
COPY --from=builder /app/03_DigitalTwin ./03_DigitalTwin
COPY --from=builder /app/README.md ./README.md

# Create state directory with correct permissions
RUN mkdir -p /app/state /app/logs /app/data && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/03_DigitalTwin \
    LOGSYS_STATE_DIR=/app/state \
    LOGSYS_LOG_DIR=/app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/live')"

# Expose ports
EXPOSE 8080

# Default command
CMD ["python", "-m", "logging_system.cli", "run-server"]
```

#### 1.1.2 Docker Compose

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  logging-system:
    build:
      context: .
      dockerfile: Dockerfile
    image: ghcr.io/alotfydev/py-loggingsystem:latest
    container_name: logging-system
    restart: unless-stopped
    
    ports:
      - "8080:8080"
      - "9090:9090"  # Metrics port
    
    environment:
      - LOGSYS_STATE_DIR=/app/state
      - LOGSYS_LOG_DIR=/app/logs
      - LOGSYS_HOST=0.0.0.0
      - LOGSYS_PORT=8080
      - LOGSYS_METRICS_PORT=9090
      - LOGSYS_WORKERS=4
      - LOGSYS_MAX_QUEUE_SIZE=10000
      - LOGSYS_THREAD_SAFETY_MODE=single_writer_per_partition
      - LOGSYS_ENABLE_OTEL=true
      - LOGSYS_OTEL_ENDPOINT=http://otel-collector:4317
    
    volumes:
      - logging-state:/app/state
      - logging-data:/app/data
    
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/live')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 256M
    
    networks:
      - logging-network
    
    depends_on:
      - otel-collector
  
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    container_name: otel-collector
    volumes:
      - ./deploy/otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml
    networks:
      - logging-network

volumes:
  logging-state:
    driver: local
  logging-data:
    driver: local

networks:
  logging-network:
    driver: bridge
```

#### 1.1.3 .dockerignore

**File:** `.dockerignore`

```
# Git
.git
.gitignore
.gitattributes

# Documentation
*.md
docs/
LICENSE

# Development
.vscode/
.idea/
*.pyc
__pycache__/
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/

# Environments
.env
.venv/
env/
venv/
.env.local

# CI/CD
.github/
.gitlab-ci.yml
Jenkinsfile

# Misc
*.log
*.tmp
.DS_Store
Thumbs.db
```

---

### Phase 2: Environment Configuration (Depends on Phase 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   PHASE 2: ENVIRONMENT CONFIGURATION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  2.1 Environment Variable Configuration                                      │
│      ├── EnvironmentConfig dataclass                                        │
│      ├── Environment variable parsing                                       │
│      └── Validation with pydantic                                          │
│                                                                             │
│  2.2 Configuration Profiles                                                  │
│      ├── development                                                        │
│      ├── staging                                                           │
│      ├── production                                                        │
│      └── Environment-specific defaults                                     │
│                                                                             │
│  2.3 Secrets from Environment                                               │
│      ├── SecretRef parsing from env vars                                   │
│      └── Encryption key from environment                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.1.1 Environment Configuration

**File:** `logging_system/config/environment.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import os
from typing import Any


class EEnvironment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class EnvironmentConfig:
    environment: EEnvironment = EEnvironment.DEVELOPMENT
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8080
    metrics_port: int = 9090
    workers: int = 4
    
    # State and storage
    state_dir: str = "/app/state"
    log_dir: str = "/app/logs"
    data_dir: str = "/app/data"
    
    # Threading
    thread_safety_mode: str = "single_writer_per_partition"
    
    # Observability
    enable_otel: bool = False
    otel_endpoint: str | None = None
    otel_service_name: str = "logging-system"
    
    # Error handling
    enable_circuit_breaker: bool = True
    enable_dlq: bool = True
    dlq_path: str | None = None
    
    # Security
    enable_encryption: bool = False
    encryption_key_ref: str | None = None
    enable_rate_limiting: bool = False
    rate_limit_rps: float = 100.0
    
    # Performance
    max_queue_size: int = 10000
    batch_size: int = 100
    dispatch_mode: str = "sync"
    
    # Health check
    health_check_interval_seconds: int = 30
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Feature flags
    feature_async_dispatch: bool = False
    feature_adaptive_batching: bool = False
    feature_connection_pooling: bool = False


def load_from_environment() -> EnvironmentConfig:
    """Load configuration from environment variables."""
    
    def get_env(name: str, default: Any, cast_type: type | None = None) -> Any:
        value = os.environ.get(name, default)
        if value is None:
            return default
        if cast_type == bool:
            return str(value).lower() in ('true', '1', 'yes', 'on')
        if cast_type == int:
            return int(value)
        if cast_type == float:
            return float(value)
        return value
    
    env_name = get_env("LOGSYS_ENVIRONMENT", "development")
    try:
        environment = EEnvironment(env_name.lower())
    except ValueError:
        environment = EEnvironment.DEVELOPMENT
    
    config = EnvironmentConfig(
        environment=environment,
        host=get_env("LOGSYS_HOST", "0.0.0.0"),
        port=get_env("LOGSYS_PORT", 8080, int),
        metrics_port=get_env("LOGSYS_METRICS_PORT", 9090, int),
        workers=get_env("LOGSYS_WORKERS", 4, int),
        state_dir=get_env("LOGSYS_STATE_DIR", "/app/state"),
        log_dir=get_env("LOGSYS_LOG_DIR", "/app/logs"),
        data_dir=get_env("LOGSYS_DATA_DIR", "/app/data"),
        thread_safety_mode=get_env("LOGSYS_THREAD_SAFETY_MODE", "single_writer_per_partition"),
        enable_otel=get_env("LOGSYS_ENABLE_OTEL", False, bool),
        otel_endpoint=get_env("LOGSYS_OTEL_ENDPOINT"),
        otel_service_name=get_env("LOGSYS_OTEL_SERVICE_NAME", "logging-system"),
        enable_circuit_breaker=get_env("LOGSYS_ENABLE_CIRCUIT_BREAKER", True, bool),
        enable_dlq=get_env("LOGSYS_ENABLE_DLQ", True, bool),
        dlq_path=get_env("LOGSYS_DLQ_PATH"),
        enable_encryption=get_env("LOGSYS_ENABLE_ENCRYPTION", False, bool),
        encryption_key_ref=get_env("LOGSYS_ENCRYPTION_KEY_REF"),
        enable_rate_limiting=get_env("LOGSYS_ENABLE_RATE_LIMITING", False, bool),
        rate_limit_rps=get_env("LOGSYS_RATE_LIMIT_RPS", 100.0, float),
        max_queue_size=get_env("LOGSYS_MAX_QUEUE_SIZE", 10000, int),
        batch_size=get_env("LOGSYS_BATCH_SIZE", 100, int),
        dispatch_mode=get_env("LOGSYS_DISPATCH_MODE", "sync"),
        health_check_interval_seconds=get_env("LOGSYS_HEALTH_CHECK_INTERVAL", 30, int),
        log_level=get_env("LOGSYS_LOG_LEVEL", "INFO"),
        log_format=get_env("LOGSYS_LOG_FORMAT", "json"),
        feature_async_dispatch=get_env("LOGSYS_FEATURE_ASYNC_DISPATCH", False, bool),
        feature_adaptive_batching=get_env("LOGSYS_FEATURE_ADAPTIVE_BATCHING", False, bool),
        feature_connection_pooling=get_env("LOGSYS_FEATURE_CONNECTION_POOLING", False, bool),
    )
    
    return config


def validate_config(config: EnvironmentConfig) -> list[str]:
    """Validate configuration and return list of errors."""
    errors = []
    
    if config.port < 1 or config.port > 65535:
        errors.append(f"Invalid port: {config.port}")
    
    if config.workers < 1 or config.workers > 32:
        errors.append(f"Invalid workers: {config.workers}")
    
    if config.max_queue_size < 100:
        errors.append(f"max_queue_size too small: {config.max_queue_size}")
    
    if config.batch_size < 1 or config.batch_size > 10000:
        errors.append(f"Invalid batch_size: {config.batch_size}")
    
    if config.enable_otel and not config.otel_endpoint:
        errors.append("OTel enabled but endpoint not configured")
    
    if config.enable_encryption and not config.encryption_key_ref:
        errors.append("Encryption enabled but key_ref not configured")
    
    valid_modes = {"single_writer_per_partition", "thread_safe_locked", "lock_free_cas"}
    if config.thread_safety_mode not in valid_modes:
        errors.append(f"Invalid thread_safety_mode: {config.thread_safety_mode}")
    
    valid_dispatch = {"sync", "async", "batch_async"}
    if config.dispatch_mode not in valid_dispatch:
        errors.append(f"Invalid dispatch_mode: {config.dispatch_mode}")
    
    return errors
```

---

### Phase 3: Graceful Shutdown (Depends on Phase 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 3: GRACEFUL SHUTDOWN                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  3.1 Shutdown Manager                                                       │
│      ├── GracefulShutdownManager                                           │
│      ├── Signal handling (SIGTERM, SIGINT)                                 │
│      └── Drain timeout configuration                                       │
│                                                                             │
│  3.2 Drain Operations                                                      │
│      ├── Drain pending records                                             │
│      ├── Close connections gracefully                                       │
│      └── Flush buffers                                                    │
│                                                                             │
│  3.3 Shutdown Hooks                                                        │
│      ├── Pre-shutdown hooks                                               │
│      ├── Post-shutdown hooks                                               │
│      └── Health check degradation during drain                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.1.1 Shutdown Manager

**File:** `logging_system/operations/shutdown.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import signal
import threading
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)


class EShutdownState(str, Enum):
    RUNNING = "running"
    DRAINING = "draining"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"


@dataclass
class ShutdownConfig:
    drain_timeout_seconds: float = 30.0
    shutdown_timeout_seconds: float = 10.0
    health_check_fail_on_drain: bool = True
    continue_dispatch_on_drain: bool = False


@dataclass
class ShutdownState:
    state: EShutdownState = EShutdownState.RUNNING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    pending_records: int = 0
    drained_records: int = 0
    errors: list[str] = field(default_factory=list)


class GracefulShutdownManager:
    """Manages graceful shutdown with drain support."""

    def __init__(
        self,
        config: ShutdownConfig | None = None,
        drain_callback: Callable[[], Any] | None = None,
    ) -> None:
        self._config = config or ShutdownConfig()
        self._drain_callback = drain_callback
        self._state = ShutdownState()
        self._lock = threading.RLock()
        self._hooks: list[tuple[int, Callable]] = []  # (priority, hook)
        self._shutdown_event = threading.Event()
        self._original_signal_handlers: dict[int, Any] = {}

    def register_hook(self, priority: int, hook: Callable[[], Any]) -> None:
        """Register a shutdown hook with priority (higher = called later)."""
        with self._lock:
            self._hooks.append((priority, hook))
            self._hooks.sort(key=lambda x: x[0])

    async def initiate_shutdown(self) -> ShutdownState:
        """Initiate graceful shutdown with drain."""
        with self._lock:
            if self._state.state != EShutdownState.RUNNING:
                return self._state

            self._state.state = EShutdownState.DRAINING
            self._state.started_at = datetime.utcnow()

        logger.info("Initiating graceful shutdown with drain...")

        try:
            # Run drain
            if self._drain_callback:
                await asyncio.wait_for(
                    self._execute_drain(),
                    timeout=self._config.drain_timeout_seconds,
                )
            
            # Transition to shutting down
            with self._lock:
                self._state.state = EShutdownState.SHUTTING_DOWN

            # Execute hooks
            await self._execute_hooks()

            # Final cleanup
            with self._lock:
                self._state.state = EShutdownState.TERMINATED
                self._state.completed_at = datetime.utcnow()

            logger.info("Graceful shutdown completed")

        except asyncio.TimeoutError:
            logger.warning("Drain timeout exceeded, forcing shutdown")
            with self._lock:
                self._state.errors.append("Drain timeout exceeded")
                self._state.state = EShutdownState.TERMINATED
                self._state.completed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            with self._lock:
                self._state.errors.append(str(e))
                self._state.state = EShutdownState.TERMINATED
                self._state.completed_at = datetime.utcnow()

        self._shutdown_event.set()
        return self._state

    async def _execute_drain(self) -> None:
        """Execute drain operation."""
        logger.info("Draining pending records...")

        if self._drain_callback:
            try:
                result = await self._drain_callback()
                if isinstance(result, dict):
                    self._state.drained_records = result.get("drained", 0)
                    self._state.pending_records = result.get("pending", 0)
                logger.info(f"Drain completed: {self._state.drained_records} records")
            except Exception as e:
                logger.error(f"Drain error: {e}")
                self._state.errors.append(f"Drain error: {e}")

    async def _execute_hooks(self) -> None:
        """Execute registered shutdown hooks."""
        for priority, hook in self._hooks:
            try:
                logger.debug(f"Executing shutdown hook (priority {priority})")
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
            except Exception as e:
                logger.error(f"Hook error: {e}")
                self._state.errors.append(f"Hook error: {e}")

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def handle_signal(signum, frame):
            sig_name = signal.Signals(signum).name
            logger.info(f"Received {sig_name}, initiating shutdown...")
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self.initiate_shutdown())
            except RuntimeError:
                pass

        for sig in (signal.SIGTERM, signal.SIGINT):
            self._original_signal_handlers[sig] = signal.signal(sig, handle_signal)

    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_signal_handlers.items():
            signal.signal(sig, handler)

    @property
    def state(self) -> ShutdownState:
        with self._lock:
            return ShutdownState(
                state=self._state.state,
                started_at=self._state.started_at,
                completed_at=self._state.completed_at,
                pending_records=self._state.pending_records,
                drained_records=self._state.drained_records,
                errors=list(self._state.errors),
            )

    def wait_for_shutdown(self, timeout: float | None = None) -> bool:
        """Wait for shutdown to complete."""
        return self._shutdown_event.wait(timeout=timeout)

    def is_shutting_down(self) -> bool:
        with self._lock:
            return self._state.state in (
                EShutdownState.DRAINING,
                EShutdownState.SHUTTING_DOWN,
            )
```

---

### Phase 4: Kubernetes Deployment (Depends on Phase 1, 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 4: KUBERNETES                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  4.1 Helm Chart Structure                                                   │
│      ├── Chart.yaml                                                         │
│      ├── values.yaml                                                       │
│      ├── templates/                                                         │
│      └── Chart.lock                                                        │
│                                                                             │
│  4.2 Kubernetes Manifests                                                   │
│      ├── Deployment with readiness/liveness probes                         │
│      ├── Service with port configuration                                   │
│      ├── ConfigMap for environment                                         │
│      └── ServiceMonitor for Prometheus                                     │
│                                                                             │
│  4.3 Helm Helpers                                                           │
│      └── helpers.tpl for common patterns                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 4.1.1 Helm Chart values.yaml

**File:** `deploy/helm/logging-system/values.yaml`

```yaml
# Default values for logging-system.
# This is a YAML-formatted file.
# Declare variables to be passed into your templates.

replicaCount: 2

image:
  repository: ghcr.io/alotfydev/py-loggingsystem
  pullPolicy: IfNotPresent
  tag: "latest"

imagePullSecrets: []
nameOverride: ""
fullnameOverride: ""

serviceAccount:
  create: true
  annotations: {}
  name: ""

podAnnotations: {}

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000

securityContext:
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false

service:
  type: ClusterIP
  port: 8080
  metricsPort: 9090

ingress:
  enabled: false
  className: ""
  annotations: {}
  hosts:
    - host: logging.local
      paths:
        - path: /
          pathType: Prefix
  tls: []

resources:
  limits:
    cpu: 2000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 256Mi

livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 30

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

# Application configuration
config:
  environment: production
  threadSafetyMode: single_writer_per_partition
  maxQueueSize: 10000
  batchSize: 100
  dispatchMode: async
  enableOtel: true
  enableCircuitBreaker: true
  enableDLQ: true
  enableRateLimiting: true
  rateLimitRps: 1000

# ServiceMonitor for Prometheus scraping
serviceMonitor:
  enabled: true
  interval: 30s
  scrapeTimeout: 10s
  namespace: monitoring

# PodDisruptionBudget
podDisruptionBudget:
  enabled: true
  minAvailable: 1
  # maxUnavailable: 1

# HorizontalPodAutoscaler v2
hpa:
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max

# Persistence
persistence:
  enabled: true
  storageClass: "standard"
  size: 10Gi
  accessMode: ReadWriteOnce

# Network policies
networkPolicy:
  enabled: true
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - port: 4317
          protocol: TCP

# Pod topology spread constraints
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app.kubernetes.io/name: logging-system
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app.kubernetes.io/name: logging-system
```

---

### Phase 5: CI/CD Pipeline (Depends on Phase 1, 2, 3, 4)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 5: CI/CD                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  5.1 GitHub Actions Workflows                                               │
│      ├── ci.yml - Build, test, lint                                         │
│      ├── release.yml - Build and push images                               │
│      └── deploy.yml - Deploy to environments                              │
│                                                                             │
│  5.2 Build Pipeline                                                         │
│      ├── Multi-platform builds                                             │
│      ├── SBOM generation                                                   │
│      └── Vulnerability scanning                                            │
│                                                                             │
│  5.3 Deployment Pipeline                                                    │
│      ├── Environment promotion                                               │
│      ├── Rollback strategy                                                  │
│      └── Smoke tests                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 5.1.1 CI Workflow

**File:** `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '20'

jobs:
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install ruff mypy types-python-dateutil

      - name: Run Ruff
        run: ruff check .

      - name: Run type checking
        run: mypy logging_system/

      - name: Check requirements
        run: |
          pip install pip-tools
          pip-compile --dry-run --generate-hashes requirements.in || true

  test:
    name: Test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests
        run: pytest --cov=logging_system --cov-report=xml --cov-report=html

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r logging_system/ -f json -o bandit.json || true

  build:
    name: Build
    runs-on: ubuntu-latest
    needs: [lint, test, security]
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: true
          sbom: true

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image-name: ghcr.io/${{ github.repository }}:${{ github.sha }}
          attach-bom: true
          format: spdx-json
          output-file: sbom.spdx.json
```

#### 5.1.2 Release Workflow

**File:** `.github/workflows/release.yml`

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: read
  packages: write

jobs:
  release:
    name: Create Release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Get version
        id: version
        run: echo "VERSION=${tag#v}" >> $GITHUB_OUTPUT
        env:
          tag: ${{ github.ref_name }}

      - name: Generate changelog
        id: changelog
        uses: anothrNr/github-action-changelog-generator@v2
        with:
          issues: true
          pr: true
          breaking: true
          template: ${{ github.workspace }}/.github/CHANGELOG.tmpl.md

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          body_path: CHANGELOG.md
          draft: false
          prerelease: ${{ contains(steps.version.outputs.VERSION, 'alpha') || contains(steps.version.outputs.VERSION, 'beta') }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Push to Container Registry
        run: |
          docker buildx build \
            --platform linux/amd64,linux/arm64 \
            --push \
            --tag ghcr.io/${{ github.repository }}:${{ steps.version.outputs.VERSION }} \
            --tag ghcr.io/${{ github.repository }}:latest \
            .
```

---

## File Structure After Implementation

```
.
├── Dockerfile                          # Phase 1
├── docker-compose.yml                  # Phase 1
├── .dockerignore                      # Phase 1
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Phase 5
│       └── release.yml                # Phase 5
├── logging_system/
│   ├── config/
│   │   ├── __init__.py
│   │   └── environment.py            # Phase 2
│   └── operations/
│       ├── __init__.py
│       └── shutdown.py              # Phase 3
└── deploy/
    └── helm/
        └── logging-system/
            ├── Chart.yaml            # Phase 4
            ├── values.yaml          # Phase 4
            ├── templates/          # Phase 4
            └── charts/             # Phase 4
```

---

## Contract Additions

| Contract | Name | Purpose |
|----------|------|---------|
| 40 | `40_LoggingSystem_Deployment_Contract.template.yaml` | Deployment configuration |
| 41 | `41_LoggingSystem_Shutdown_Contract.template.yaml` | Graceful shutdown contract |

---

## Deployment Metrics

| Metric | Target |
|--------|--------|
| Deployment time | < 5 minutes |
| Rollback time | < 2 minutes |
| Startup time | < 30 seconds |
| Zero-downtime | 99.9% |

---

**Estimated Implementation Time:** 2-3 weeks  
**Estimated Effort:** ~1500 lines (Docker, YAML, Python)  
**Risk Level:** Medium (infrastructure changes)
