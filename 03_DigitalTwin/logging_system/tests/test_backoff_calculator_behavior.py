import pytest

from logging_system.errors import (
    BackoffCalculator,
    ERetryStrategy,
    EJitterMode,
)


class TestBackoffImmediate:
    def test_backoff_immediate_attempt_1(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.IMMEDIATE)
        assert calc.calculate_delay(1) == 0.0

    def test_backoff_immediate_attempt_5(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.IMMEDIATE)
        assert calc.calculate_delay(5) == 0.0

    def test_backoff_immediate_any_attempt_returns_zero(self):
        calc = BackoffCalculator(initial_delay_seconds=0.5, strategy=ERetryStrategy.IMMEDIATE)
        for attempt in range(1, 10):
            assert calc.calculate_delay(attempt) == 0.0


class TestBackoffLinear:
    def test_backoff_linear_attempt_1(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.LINEAR, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(1) == pytest.approx(0.1)

    def test_backoff_linear_attempt_2(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.LINEAR, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(2) == pytest.approx(0.2)

    def test_backoff_linear_attempt_5(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.LINEAR, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(5) == pytest.approx(0.5)


class TestBackoffExponential:
    def test_backoff_exponential_attempt_1(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.EXPONENTIAL, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(1) == pytest.approx(0.1)

    def test_backoff_exponential_attempt_2(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.EXPONENTIAL, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(2) == pytest.approx(0.2)

    def test_backoff_exponential_attempt_3(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.EXPONENTIAL, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(3) == pytest.approx(0.4)

    def test_backoff_exponential_attempt_4(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.EXPONENTIAL, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(4) == pytest.approx(0.8)


class TestBackoffFibonacci:
    def test_backoff_fibonacci_attempt_1(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.FIBONACCI, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(1) == pytest.approx(0.1)

    def test_backoff_fibonacci_attempt_2(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.FIBONACCI, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(2) == pytest.approx(0.1)

    def test_backoff_fibonacci_attempt_3(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.FIBONACCI, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(3) == pytest.approx(0.2)

    def test_backoff_fibonacci_attempt_4(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.FIBONACCI, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(4) == pytest.approx(0.3)

    def test_backoff_fibonacci_attempt_5(self):
        calc = BackoffCalculator(initial_delay_seconds=0.1, strategy=ERetryStrategy.FIBONACCI, jitter_mode=EJitterMode.NONE)
        assert calc.calculate_delay(5) == pytest.approx(0.5)


class TestJitterModes:
    def test_jitter_none_returns_same_value(self):
        calc = BackoffCalculator(
            initial_delay_seconds=0.1,
            strategy=ERetryStrategy.EXPONENTIAL,
            jitter_mode=EJitterMode.NONE,
        )
        delay = calc.calculate_delay(3)
        assert delay == pytest.approx(0.4)

    def test_jitter_full_is_within_bounds(self):
        calc = BackoffCalculator(
            initial_delay_seconds=0.1,
            strategy=ERetryStrategy.EXPONENTIAL,
            jitter_mode=EJitterMode.FULL,
        )
        base = 0.4
        min_expected = base * 0.5
        max_expected = base * 1.0
        for _ in range(100):
            delay = calc.calculate_delay(3)
            assert min_expected <= delay <= max_expected

    def test_jitter_decorrelated_stays_within_max(self):
        calc = BackoffCalculator(
            initial_delay_seconds=0.1,
            max_delay_seconds=1.0,
            strategy=ERetryStrategy.EXPONENTIAL,
            jitter_mode=EJitterMode.DECORRELATED,
        )
        for _ in range(100):
            delay = calc.calculate_delay(3)
            assert 0 <= delay <= 1.0


class TestMaxDelayCap:
    def test_max_delay_cap_applied(self):
        calc = BackoffCalculator(
            initial_delay_seconds=1.0,
            max_delay_seconds=2.0,
            strategy=ERetryStrategy.EXPONENTIAL,
            jitter_mode=EJitterMode.NONE,
        )
        assert calc.calculate_delay(10) == 2.0

    def test_max_delay_cap_with_jitter(self):
        calc = BackoffCalculator(
            initial_delay_seconds=1.0,
            max_delay_seconds=5.0,
            strategy=ERetryStrategy.EXPONENTIAL,
            jitter_mode=EJitterMode.FULL,
        )
        for _ in range(100):
            delay = calc.calculate_delay(10)
            assert delay <= 5.0


class TestOverridePerCall:
    def test_override_strategy_per_call(self):
        calc = BackoffCalculator(
            initial_delay_seconds=0.1,
            strategy=ERetryStrategy.LINEAR,
            jitter_mode=EJitterMode.NONE,
        )
        delay = calc.calculate_delay(3, strategy=ERetryStrategy.EXPONENTIAL)
        assert delay == pytest.approx(0.4)

    def test_override_jitter_per_call(self):
        calc = BackoffCalculator(
            initial_delay_seconds=0.1,
            strategy=ERetryStrategy.EXPONENTIAL,
            jitter_mode=EJitterMode.NONE,
        )
        delay_no_jitter = calc.calculate_delay(3, jitter_mode=EJitterMode.NONE)
        assert delay_no_jitter == pytest.approx(0.4)
