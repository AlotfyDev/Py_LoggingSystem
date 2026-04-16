from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Callable, Mapping
from uuid import uuid4

from ...models.utc_now_iso import utc_now_iso


@dataclass
class ThreadPoolResourceManagementClient:
    _container_leases_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    _execution_leases_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    _execution_profiles_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    _executors_by_profile_id: dict[str, ThreadPoolExecutor] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)
    _default_container_lease_ttl_seconds: int = 3600
    _default_execution_lease_ttl_seconds: int = 300

    def __post_init__(self) -> None:
        if len(self._execution_profiles_by_id) > 0:
            return
        self._execution_profiles_by_id = {
            "exec.logging.local.default": {
                "execution_profile_id": "exec.logging.local.default",
                "scope_support": ["in_process"],
                "queue_model": "bounded_fifo",
                "queue_bounds": {"max_items": 5000},
                "scheduling_policy": {
                    "kind": "fixed_priority",
                    "priority_bands": ["error_fatal", "warn", "info_debug_trace"],
                },
                "thread_safety_mode": "single_writer_per_partition",
                "backpressure_policy": {
                    "action": "drop_oldest",
                    "severity_overrides": {"fatal": "block", "error": "retry_with_jitter"},
                },
                "lease_policy": {"required": True, "ttl_seconds": 300, "renewable": True},
                "worker_pool": {"max_workers": 4},
            },
            "exec.logging.distributed.redis": {
                "execution_profile_id": "exec.logging.distributed.redis",
                "scope_support": ["inter_process", "distributed"],
                "queue_model": "bounded_priority",
                "queue_bounds": {"max_items": 20000},
                "scheduling_policy": {
                    "kind": "weighted_fair",
                    "queue_weights": {"high": 6, "medium": 3, "low": 1},
                },
                "thread_safety_mode": "thread_safe_locked",
                "backpressure_policy": {
                    "action": "retry_with_jitter",
                    "severity_overrides": {"fatal": "block"},
                },
                "lease_policy": {"required": True, "ttl_seconds": 120, "renewable": True},
                "worker_pool": {"max_workers": 8},
            },
        }

    def close(self) -> None:
        with self._lock:
            executors = list(self._executors_by_profile_id.values())
            self._executors_by_profile_id.clear()
        for executor in executors:
            executor.shutdown(wait=True, cancel_futures=False)

    def request_container_lease(
        self,
        *,
        logger_instance_id: str,
        container_binding_id: str,
        container_backend_profile_id: str,
    ) -> Mapping[str, Any]:
        logger_id = str(logger_instance_id).strip()
        binding_id = str(container_binding_id).strip()
        backend_profile_id = str(container_backend_profile_id).strip()
        if logger_id == "":
            raise ValueError("logger_instance_id is required")
        if binding_id == "":
            raise ValueError("container_binding_id is required")
        if backend_profile_id == "":
            raise ValueError("container_backend_profile_id is required")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._default_container_lease_ttl_seconds)
        lease_id = f"lease-{uuid4()}"
        lease = {
            "container_lease_id": lease_id,
            "logger_instance_id": logger_id,
            "container_binding_id": binding_id,
            "container_backend_profile_id": backend_profile_id,
            "issued_at_utc": utc_now_iso(),
            "expires_at_utc": expires_at.isoformat().replace("+00:00", "Z"),
            "state": "active",
        }
        with self._lock:
            self._container_leases_by_id[lease_id] = dict(lease)
        return dict(lease)

    def validate_container_lease(self, container_lease_id: str) -> bool:
        lease_id = str(container_lease_id).strip()
        if lease_id == "":
            return False
        with self._lock:
            lease = self._container_leases_by_id.get(lease_id)
        if lease is None:
            return False
        if lease.get("state") != "active":
            return False
        expires_at_utc = lease.get("expires_at_utc")
        if not isinstance(expires_at_utc, str):
            return False
        expires_at = datetime.fromisoformat(expires_at_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
        return expires_at > datetime.now(timezone.utc)

    def get_container_lease(self, container_lease_id: str) -> Mapping[str, Any]:
        lease_id = str(container_lease_id).strip()
        if lease_id == "":
            raise ValueError("container_lease_id is required")
        with self._lock:
            lease = self._container_leases_by_id.get(lease_id)
        if lease is None:
            raise KeyError(f"container_lease_id is not registered: {lease_id}")
        return dict(lease)

    def release_container_lease(self, container_lease_id: str) -> None:
        lease_id = str(container_lease_id).strip()
        if lease_id == "":
            raise ValueError("container_lease_id is required")
        with self._lock:
            lease = self._container_leases_by_id.get(lease_id)
            if lease is None:
                raise KeyError(f"container_lease_id is not registered: {lease_id}")
            lease["state"] = "released"
            self._container_leases_by_id[lease_id] = lease

    def request_execution_lease(
        self,
        *,
        logger_instance_id: str,
        execution_binding_id: str,
        required_execution_profile_id: str,
    ) -> Mapping[str, Any]:
        logger_id = str(logger_instance_id).strip()
        binding_id = str(execution_binding_id).strip()
        profile_id = str(required_execution_profile_id).strip()
        if logger_id == "":
            raise ValueError("logger_instance_id is required")
        if binding_id == "":
            raise ValueError("execution_binding_id is required")
        if profile_id == "":
            raise ValueError("required_execution_profile_id is required")
        if profile_id not in self._execution_profiles_by_id:
            raise KeyError(f"execution_profile_id is not registered: {profile_id}")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._default_execution_lease_ttl_seconds)
        lease_id = f"exec-lease-{uuid4()}"
        lease = {
            "execution_lease_id": lease_id,
            "logger_instance_id": logger_id,
            "execution_binding_id": binding_id,
            "required_execution_profile_id": profile_id,
            "issued_at_utc": utc_now_iso(),
            "expires_at_utc": expires_at.isoformat().replace("+00:00", "Z"),
            "state": "active",
        }
        with self._lock:
            self._execution_leases_by_id[lease_id] = dict(lease)
        return dict(lease)

    def validate_execution_lease(self, execution_lease_id: str) -> bool:
        lease_id = str(execution_lease_id).strip()
        if lease_id == "":
            return False
        with self._lock:
            lease = self._execution_leases_by_id.get(lease_id)
        if lease is None:
            return False
        if lease.get("state") != "active":
            return False
        expires_at_utc = lease.get("expires_at_utc")
        if not isinstance(expires_at_utc, str):
            return False
        expires_at = datetime.fromisoformat(expires_at_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
        return expires_at > datetime.now(timezone.utc)

    def get_execution_lease(self, execution_lease_id: str) -> Mapping[str, Any]:
        lease_id = str(execution_lease_id).strip()
        if lease_id == "":
            raise ValueError("execution_lease_id is required")
        with self._lock:
            lease = self._execution_leases_by_id.get(lease_id)
        if lease is None:
            raise KeyError(f"execution_lease_id is not registered: {lease_id}")
        return dict(lease)

    def release_execution_lease(self, execution_lease_id: str) -> None:
        lease_id = str(execution_lease_id).strip()
        if lease_id == "":
            raise ValueError("execution_lease_id is required")
        with self._lock:
            lease = self._execution_leases_by_id.get(lease_id)
            if lease is None:
                raise KeyError(f"execution_lease_id is not registered: {lease_id}")
            lease["state"] = "released"
            self._execution_leases_by_id[lease_id] = lease

    def get_execution_profile(self, execution_profile_id: str) -> Mapping[str, Any]:
        profile_id = str(execution_profile_id).strip()
        if profile_id == "":
            raise ValueError("execution_profile_id is required")
        with self._lock:
            profile = self._execution_profiles_by_id.get(profile_id)
        if profile is None:
            raise KeyError(f"execution_profile_id is not registered: {profile_id}")
        return dict(profile)

    def execute_dispatch_tasks(
        self,
        *,
        execution_lease_id: str,
        required_execution_profile_id: str,
        tasks: list[Callable[[], Any]],
    ) -> list[Any]:
        lease_id = str(execution_lease_id).strip()
        if lease_id == "":
            raise ValueError("execution_lease_id is required")
        profile_id = str(required_execution_profile_id).strip()
        if profile_id == "":
            raise ValueError("required_execution_profile_id is required")
        if not self.validate_execution_lease(lease_id):
            raise RuntimeError(f"invalid or expired execution lease: {lease_id}")
        if len(tasks) == 0:
            return []

        profile = self.get_execution_profile(profile_id)
        queue_bounds = profile.get("queue_bounds")
        max_items = queue_bounds.get("max_items") if isinstance(queue_bounds, Mapping) else None
        if isinstance(max_items, int) and max_items > 0 and len(tasks) > max_items:
            raise RuntimeError("task batch exceeds execution profile queue_bounds.max_items")

        executor = self._get_or_create_executor(profile_id=profile_id, profile=profile)
        futures: list[Future[Any]] = [executor.submit(task) for task in tasks]

        results: list[Any] = []
        for idx, future in enumerate(futures):
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001
                for pending in futures[idx + 1 :]:
                    pending.cancel()
                raise RuntimeError("thread pool dispatch task failed") from exc
        return results

    def _get_or_create_executor(self, *, profile_id: str, profile: Mapping[str, Any]) -> ThreadPoolExecutor:
        with self._lock:
            existing = self._executors_by_profile_id.get(profile_id)
            if existing is not None:
                return existing

            worker_pool = profile.get("worker_pool")
            max_workers = worker_pool.get("max_workers") if isinstance(worker_pool, Mapping) else None
            if not isinstance(max_workers, int) or max_workers <= 0:
                max_workers = 4
            executor = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix=f"logsys-{profile_id.replace('.', '-')}",
            )
            self._executors_by_profile_id[profile_id] = executor
            return executor
