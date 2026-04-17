from __future__ import annotations

import unittest

from logging_system.errors.circuit_breaker_registry import (
    CircuitBreakerRegistry,
    get_registry,
    set_registry,
)
from logging_system.errors.circuit_breaker import (
    CircuitBreakerConfig,
    ECircuitState,
)


class CircuitBreakerRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = CircuitBreakerRegistry()

    def test_creates_on_demand(self) -> None:
        breaker = self.registry.get_or_create("adapter.http")
        self.assertIsNotNone(breaker)
        self.assertEqual(breaker.name, "adapter.http")
        self.assertEqual(breaker.state, ECircuitState.CLOSED)

    def test_returns_existing_breaker(self) -> None:
        breaker1 = self.registry.get_or_create("adapter.http")
        breaker2 = self.registry.get_or_create("adapter.http")
        self.assertIs(breaker1, breaker2)

    def test_get_existing_breaker(self) -> None:
        self.registry.get_or_create("adapter.http")
        breaker = self.registry.get("adapter.http")
        self.assertIsNotNone(breaker)
        self.assertEqual(breaker.name, "adapter.http")

    def test_get_nonexistent_breaker(self) -> None:
        breaker = self.registry.get("nonexistent")
        self.assertIsNone(breaker)

    def test_is_available_closed(self) -> None:
        self.registry.get_or_create("adapter.http")
        self.assertTrue(self.registry.is_available("adapter.http"))

    def test_is_available_open(self) -> None:
        breaker = self.registry.get_or_create(
            "adapter.http",
            CircuitBreakerConfig(failure_threshold=1),
        )

        try:
            breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass

        self.assertFalse(self.registry.is_available("adapter.http"))

    def test_is_available_nonexistent(self) -> None:
        self.assertTrue(self.registry.is_available("nonexistent"))

    def test_get_state(self) -> None:
        self.registry.get_or_create("adapter.http")
        state = self.registry.get_state("adapter.http")
        self.assertEqual(state, ECircuitState.CLOSED)

    def test_get_state_nonexistent(self) -> None:
        state = self.registry.get_state("nonexistent")
        self.assertIsNone(state)

    def test_list_all_states(self) -> None:
        self.registry.get_or_create("adapter.http")
        self.registry.get_or_create("adapter.db")

        states = self.registry.list_all_states()
        self.assertEqual(len(states), 2)
        self.assertEqual(states["adapter.http"], ECircuitState.CLOSED)
        self.assertEqual(states["adapter.db"], ECircuitState.CLOSED)

    def test_list_all_breakers(self) -> None:
        self.registry.get_or_create("adapter.http")
        self.registry.get_or_create("adapter.db")

        breakers = self.registry.list_all_breakers()
        self.assertEqual(len(breakers), 2)

    def test_get_all_metrics(self) -> None:
        self.registry.get_or_create("adapter.http")
        metrics = self.registry.get_all_metrics()
        self.assertIn("adapter.http", metrics)
        self.assertIn("total_calls", metrics["adapter.http"])

    def test_reset_single_breaker(self) -> None:
        breaker = self.registry.get_or_create(
            "adapter.http",
            CircuitBreakerConfig(failure_threshold=1),
        )

        try:
            breaker.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass

        self.assertEqual(breaker.state, ECircuitState.OPEN)

        result = self.registry.reset("adapter.http")
        self.assertTrue(result)
        self.assertEqual(breaker.state, ECircuitState.CLOSED)

    def test_reset_nonexistent(self) -> None:
        result = self.registry.reset("nonexistent")
        self.assertFalse(result)

    def test_reset_all(self) -> None:
        breaker1 = self.registry.get_or_create(
            "adapter.http",
            CircuitBreakerConfig(failure_threshold=1),
        )
        breaker2 = self.registry.get_or_create("adapter.db")

        try:
            breaker1.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass

        self.registry.reset_all()
        self.assertEqual(breaker1.state, ECircuitState.CLOSED)
        self.assertEqual(breaker2.state, ECircuitState.CLOSED)

    def test_remove_existing(self) -> None:
        self.registry.get_or_create("adapter.http")
        result = self.registry.remove("adapter.http")
        self.assertTrue(result)
        self.assertIsNone(self.registry.get("adapter.http"))

    def test_remove_nonexistent(self) -> None:
        result = self.registry.remove("nonexistent")
        self.assertFalse(result)

    def test_clear(self) -> None:
        self.registry.get_or_create("adapter.http")
        self.registry.get_or_create("adapter.db")

        self.registry.clear()
        self.assertEqual(len(self.registry), 0)

    def test_len(self) -> None:
        self.assertEqual(len(self.registry), 0)
        self.registry.get_or_create("adapter.http")
        self.assertEqual(len(self.registry), 1)
        self.registry.get_or_create("adapter.db")
        self.assertEqual(len(self.registry), 2)

    def test_contains(self) -> None:
        self.registry.get_or_create("adapter.http")
        self.assertIn("adapter.http", self.registry)
        self.assertNotIn("adapter.db", self.registry)

    def test_default_config(self) -> None:
        self.assertIsNotNone(self.registry.default_config)

        new_config = CircuitBreakerConfig(failure_threshold=10)
        self.registry.set_default_config(new_config)
        self.assertEqual(self.registry.default_config.failure_threshold, 10)

    def test_creates_with_custom_config(self) -> None:
        custom_config = CircuitBreakerConfig(failure_threshold=20)
        breaker = self.registry.get_or_create("adapter.http", custom_config)
        self.assertEqual(breaker.config.failure_threshold, 20)


class GlobalRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_registry = get_registry()

    def tearDown(self) -> None:
        set_registry(self._original_registry)

    def test_get_registry(self) -> None:
        registry = get_registry()
        self.assertIsNotNone(registry)
        self.assertIsInstance(registry, CircuitBreakerRegistry)

    def test_get_registry_same_instance(self) -> None:
        registry1 = get_registry()
        registry2 = get_registry()
        self.assertIs(registry1, registry2)

    def test_set_registry(self) -> None:
        new_registry = CircuitBreakerRegistry()
        set_registry(new_registry)
        retrieved = get_registry()
        self.assertIs(retrieved, new_registry)


if __name__ == "__main__":
    unittest.main()
