from __future__ import annotations

import unittest

from logging_system.errors.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerMetrics,
    CircuitBreakerOpenError,
    ECircuitState,
)


class ECircuitStateTests(unittest.TestCase):
    def test_closed_value(self) -> None:
        self.assertEqual(ECircuitState.CLOSED.value, "closed")

    def test_open_value(self) -> None:
        self.assertEqual(ECircuitState.OPEN.value, "open")

    def test_half_open_value(self) -> None:
        self.assertEqual(ECircuitState.HALF_OPEN.value, "half_open")

    def test_string_coercion(self) -> None:
        self.assertEqual(ECircuitState.CLOSED, "closed")
        self.assertEqual(ECircuitState.OPEN, "open")
        self.assertEqual(ECircuitState.HALF_OPEN, "half_open")


class CircuitBreakerConfigTests(unittest.TestCase):
    def test_default_values(self) -> None:
        config = CircuitBreakerConfig()
        self.assertEqual(config.failure_threshold, 5)
        self.assertEqual(config.success_threshold, 2)
        self.assertEqual(config.open_timeout_seconds, 30.0)
        self.assertEqual(config.half_open_max_calls, 3)
        self.assertEqual(config.sliding_window_size, 10)

    def test_custom_values(self) -> None:
        config = CircuitBreakerConfig(
            failure_threshold=10,
            success_threshold=3,
            open_timeout_seconds=60.0,
            half_open_max_calls=5,
            sliding_window_size=20,
        )
        self.assertEqual(config.failure_threshold, 10)
        self.assertEqual(config.success_threshold, 3)
        self.assertEqual(config.open_timeout_seconds, 60.0)
        self.assertEqual(config.half_open_max_calls, 5)
        self.assertEqual(config.sliding_window_size, 20)

    def test_config_is_frozen(self) -> None:
        config = CircuitBreakerConfig()
        with self.assertRaises(AttributeError):
            config.failure_threshold = 10  # type: ignore[attr-defined]


class CircuitBreakerMetricsTests(unittest.TestCase):
    def test_default_values(self) -> None:
        metrics = CircuitBreakerMetrics()
        self.assertEqual(metrics.total_calls, 0)
        self.assertEqual(metrics.successful_calls, 0)
        self.assertEqual(metrics.failed_calls, 0)
        self.assertEqual(metrics.rejected_calls, 0)
        self.assertEqual(metrics.state_transitions, 0)
        self.assertIsNone(metrics.last_failure_time)
        self.assertIsNone(metrics.last_success_time)
        self.assertEqual(metrics.consecutive_failures, 0)
        self.assertEqual(metrics.consecutive_successes, 0)

    def test_to_dict(self) -> None:
        metrics = CircuitBreakerMetrics(
            total_calls=100,
            successful_calls=90,
            failed_calls=10,
        )
        d = metrics.to_dict()
        self.assertEqual(d["total_calls"], 100)
        self.assertEqual(d["successful_calls"], 90)
        self.assertEqual(d["failed_calls"], 10)
        self.assertEqual(d["rejected_calls"], 0)


class CircuitBreakerOpenErrorTests(unittest.TestCase):
    def test_error_with_name_and_state(self) -> None:
        error = CircuitBreakerOpenError(
            circuit_name="adapter.http",
            state=ECircuitState.OPEN,
        )
        self.assertEqual(error.circuit_name, "adapter.http")
        self.assertEqual(error.state, ECircuitState.OPEN)
        self.assertEqual(str(error), "Circuit breaker 'adapter.http' is open")

    def test_error_with_custom_message(self) -> None:
        error = CircuitBreakerOpenError(
            circuit_name="adapter.http",
            state=ECircuitState.OPEN,
            message="Custom error message",
        )
        self.assertEqual(str(error), "Custom error message")

    def test_error_inheritance(self) -> None:
        error = CircuitBreakerOpenError(
            circuit_name="test",
            state=ECircuitState.OPEN,
        )
        self.assertIsInstance(error, Exception)


if __name__ == "__main__":
    unittest.main()
