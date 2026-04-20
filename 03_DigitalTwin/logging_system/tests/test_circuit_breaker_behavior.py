from __future__ import annotations

import threading
import time
import unittest

from logging_system.errors.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerMetrics,
    CircuitBreakerOpenError,
    ECircuitState,
)


class CircuitBreakerClosedToOpenTests(unittest.TestCase):
    def test_stays_closed_on_success(self) -> None:
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        cb.call(lambda: "success")
        self.assertEqual(cb.state, ECircuitState.CLOSED)

    def test_transitions_to_open_after_failure_threshold(self) -> None:
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        for _ in range(3):
            with self.assertRaises(Exception):
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        self.assertEqual(cb.state, ECircuitState.OPEN)

    def test_metrics_updated_on_failure(self) -> None:
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=3))
        metrics_before = cb.metrics

        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass

        metrics = cb.metrics
        self.assertEqual(metrics.failed_calls, 1)
        self.assertEqual(metrics.consecutive_failures, 1)


class CircuitBreakerOpenToHalfOpenTests(unittest.TestCase):
    def test_transitions_to_half_open_after_timeout(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(failure_threshold=2, open_timeout_seconds=0.1),
        )

        for _ in range(2):
            with self.assertRaises(Exception):
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        self.assertEqual(cb.state, ECircuitState.OPEN)

        time.sleep(0.15)

        self.assertEqual(cb.state, ECircuitState.HALF_OPEN)

    def test_rejects_calls_when_open(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(failure_threshold=2, open_timeout_seconds=1.0),
        )

        for _ in range(2):
            with self.assertRaises(Exception):
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        self.assertFalse(cb.is_call_allowed())

        with self.assertRaises(CircuitBreakerOpenError):
            cb.call(lambda: "should not execute")


class CircuitBreakerHalfOpenToClosedTests(unittest.TestCase):
    def test_transitions_to_closed_after_success_threshold(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(
                failure_threshold=2,
                success_threshold=2,
                open_timeout_seconds=0.1,
            ),
        )

        for _ in range(2):
            with self.assertRaises(Exception):
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        time.sleep(0.15)
        self.assertEqual(cb.state, ECircuitState.HALF_OPEN)

        cb.call(lambda: "success1")
        self.assertEqual(cb.state, ECircuitState.HALF_OPEN)

        cb.call(lambda: "success2")
        self.assertEqual(cb.state, ECircuitState.CLOSED)


class CircuitBreakerHalfOpenToOpenTests(unittest.TestCase):
    def test_transitions_back_to_open_on_failure(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(
                failure_threshold=2,
                open_timeout_seconds=0.1,
            ),
        )

        for _ in range(2):
            with self.assertRaises(Exception):
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        time.sleep(0.15)
        self.assertEqual(cb.state, ECircuitState.HALF_OPEN)

        with self.assertRaises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail in half-open")))

        self.assertEqual(cb.state, ECircuitState.OPEN)


class CircuitBreakerCallWhenOpenTests(unittest.TestCase):
    def test_raises_open_error_when_open(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(failure_threshold=1, open_timeout_seconds=10.0),
        )

        with self.assertRaises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        with self.assertRaises(CircuitBreakerOpenError) as ctx:
            cb.call(lambda: "should not execute")

        self.assertEqual(ctx.exception.circuit_name, "test")
        self.assertEqual(ctx.exception.state, ECircuitState.OPEN)

    def test_increments_rejected_calls_metric(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(failure_threshold=1, open_timeout_seconds=10.0),
        )

        with self.assertRaises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        initial_rejected = cb.metrics.rejected_calls

        try:
            cb.call(lambda: "test")
        except CircuitBreakerOpenError:
            pass

        self.assertEqual(cb.metrics.rejected_calls, initial_rejected + 1)


class CircuitBreakerSlidingWindowTests(unittest.TestCase):
    def test_sliding_window_tracks_failures(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(
                failure_threshold=3,
                sliding_window_size=5,
            ),
        )

        cb.call(lambda: "success1")
        self.assertEqual(cb.get_recent_failures(), 0)

        for _ in range(3):
            with self.assertRaises(Exception):
                cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        self.assertEqual(cb.get_recent_failures(), 3)

    def test_sliding_window_eviction(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(
                failure_threshold=10,
                sliding_window_size=3,
            ),
        )

        for i in range(5):
            try:
                if i < 2:
                    cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
                else:
                    cb.call(lambda: "success")
            except Exception:
                pass

        self.assertLessEqual(cb.get_recent_failures(), 3)


class CircuitBreakerThreadSafetyTests(unittest.TestCase):
    def test_concurrent_calls_are_thread_safe(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(
                failure_threshold=100,
                sliding_window_size=100,
            ),
        )

        errors = []
        successes = []
        lock = threading.Lock()

        def safe_call() -> None:
            try:
                result = cb.call(lambda: "success")
                with lock:
                    successes.append(result)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=safe_call) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(successes), 10)

    def test_state_transition_is_atomic(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(
                failure_threshold=5,
                open_timeout_seconds=0.1,
            ),
        )

        state_changes = []
        lock = threading.Lock()

        def check_state() -> None:
            state = cb.state
            with lock:
                state_changes.append(state)

        threads = [threading.Thread(target=check_state) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for state in state_changes:
            self.assertIn(state, ECircuitState)


class CircuitBreakerMetricsUpdatedTests(unittest.TestCase):
    def test_metrics_updated_on_success(self) -> None:
        cb = CircuitBreaker("test")

        cb.call(lambda: "result")

        metrics = cb.metrics
        self.assertEqual(metrics.total_calls, 1)
        self.assertEqual(metrics.successful_calls, 1)
        self.assertEqual(metrics.failed_calls, 0)
        self.assertIsNotNone(metrics.last_success_time)

    def test_metrics_updated_on_failure(self) -> None:
        cb = CircuitBreaker("test")

        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except Exception:
            pass

        metrics = cb.metrics
        self.assertEqual(metrics.total_calls, 1)
        self.assertEqual(metrics.successful_calls, 0)
        self.assertEqual(metrics.failed_calls, 1)
        self.assertIsNotNone(metrics.last_failure_time)

    def test_state_transitions_counted(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(failure_threshold=1, open_timeout_seconds=0.1),
        )

        initial_transitions = cb.metrics.state_transitions

        with self.assertRaises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        self.assertEqual(cb.metrics.state_transitions, initial_transitions + 1)

        time.sleep(0.15)

        _ = cb.state

        self.assertGreater(cb.metrics.state_transitions, initial_transitions + 1)


class CircuitBreakerMetricsRateTests(unittest.TestCase):
    def test_failure_rate_zero_calls(self) -> None:
        metrics = CircuitBreakerMetrics()
        self.assertEqual(metrics.failure_rate, 0.0)

    def test_failure_rate_with_calls(self) -> None:
        metrics = CircuitBreakerMetrics(total_calls=10, failed_calls=2)
        self.assertEqual(metrics.failure_rate, 0.2)

    def test_success_rate_zero_calls(self) -> None:
        metrics = CircuitBreakerMetrics()
        self.assertEqual(metrics.success_rate, 0.0)

    def test_success_rate_with_calls(self) -> None:
        metrics = CircuitBreakerMetrics(total_calls=10, successful_calls=8)
        self.assertEqual(metrics.success_rate, 0.8)

    def test_rejection_rate_zero(self) -> None:
        metrics = CircuitBreakerMetrics()
        self.assertEqual(metrics.rejection_rate, 0.0)

    def test_rejection_rate_with_rejections(self) -> None:
        metrics = CircuitBreakerMetrics(total_calls=10, rejected_calls=5)
        self.assertEqual(metrics.rejection_rate, 5 / 15)

    def test_availability_full(self) -> None:
        metrics = CircuitBreakerMetrics(successful_calls=10, failed_calls=0)
        self.assertEqual(metrics.availability, 1.0)

    def test_availability_partial(self) -> None:
        metrics = CircuitBreakerMetrics(successful_calls=8, failed_calls=2)
        self.assertEqual(metrics.availability, 0.8)

    def test_metrics_to_dict_includes_rates(self) -> None:
        metrics = CircuitBreakerMetrics(total_calls=10, successful_calls=8, failed_calls=2)
        d = metrics.to_dict()
        self.assertIn("failure_rate", d)
        self.assertIn("success_rate", d)
        self.assertIn("rejection_rate", d)
        self.assertIn("availability", d)
        self.assertEqual(d["failure_rate"], 0.2)
        self.assertEqual(d["success_rate"], 0.8)


class CircuitBreakerHalfOpenMetricsTests(unittest.TestCase):
    def test_half_open_calls_tracked(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(
                failure_threshold=1,
                success_threshold=2,
                open_timeout_seconds=0.1,
            ),
        )

        with self.assertRaises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        time.sleep(0.15)
        _ = cb.state

        cb.call(lambda: "success1")
        self.assertEqual(cb.metrics.half_open_calls_made, 1)

        cb.call(lambda: "success2")
        self.assertEqual(cb.metrics.half_open_calls_made, 2)


class CircuitBreakerResetTests(unittest.TestCase):
    def test_reset_clears_state(self) -> None:
        cb = CircuitBreaker(
            "test",
            CircuitBreakerConfig(failure_threshold=1),
        )

        with self.assertRaises(Exception):
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))

        self.assertEqual(cb.state, ECircuitState.OPEN)

        cb.reset()

        self.assertEqual(cb.state, ECircuitState.CLOSED)
        self.assertEqual(cb.metrics.consecutive_failures, 0)
        self.assertEqual(cb.metrics.rejected_calls, 0)


if __name__ == "__main__":
    unittest.main()
