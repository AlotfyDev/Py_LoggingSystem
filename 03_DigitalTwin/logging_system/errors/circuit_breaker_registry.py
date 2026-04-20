from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    ECircuitState,
)


@dataclass
class CircuitBreakerRegistry:
    _breakers: dict[str, CircuitBreaker] = field(default_factory=dict)
    _default_config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _lock: RLock = field(default_factory=RLock)

    def get_or_create(self, name: str, config: CircuitBreakerConfig | None = None) -> CircuitBreaker:
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    config=config or self._default_config,
                )
            return self._breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        with self._lock:
            return self._breakers.get(name)

    def is_available(self, name: str) -> bool:
        with self._lock:
            breaker = self._breakers.get(name)
            if breaker is None:
                return True
            return breaker.state != ECircuitState.OPEN

    def get_state(self, name: str) -> ECircuitState | None:
        with self._lock:
            breaker = self._breakers.get(name)
            if breaker is None:
                return None
            return breaker.state

    def list_all_states(self) -> dict[str, ECircuitState]:
        with self._lock:
            return {name: cb.state for name, cb in self._breakers.items()}

    def list_all_breakers(self) -> dict[str, CircuitBreaker]:
        with self._lock:
            return dict(self._breakers)

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {name: cb.metrics.to_dict() for name, cb in self._breakers.items()}

    def reset(self, name: str) -> bool:
        with self._lock:
            breaker = self._breakers.get(name)
            if breaker is None:
                return False
            breaker.reset()
            return True

    def reset_all(self) -> None:
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()

    def remove(self, name: str) -> bool:
        with self._lock:
            if name in self._breakers:
                del self._breakers[name]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._breakers.clear()

    @property
    def default_config(self) -> CircuitBreakerConfig:
        return self._default_config

    def set_default_config(self, config: CircuitBreakerConfig) -> None:
        self._default_config = config

    def __len__(self) -> int:
        with self._lock:
            return len(self._breakers)

    def __contains__(self, name: str) -> bool:
        with self._lock:
            return name in self._breakers


_global_registry: CircuitBreakerRegistry | None = None


def get_registry() -> CircuitBreakerRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = CircuitBreakerRegistry()
    return _global_registry


def set_registry(registry: CircuitBreakerRegistry) -> None:
    global _global_registry
    _global_registry = registry
