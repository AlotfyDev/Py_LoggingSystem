import time

import pytest

from logging_system.errors import (
    CancellationEvent,
    ERetryStrategy,
    EErrorCategory,
    ErrorResult,
    RetryConfig,
    RetryExecutor,
    Success,
)


class TestRetrySuccess:
    def test_retry_success_first_attempt(self):
        executor = RetryExecutor(RetryConfig(max_attempts=3))

        def operation():
            return "success"

        result = executor.execute(operation)
        assert isinstance(result, Success)
        assert result.value == "success"

    def test_retry_success_after_retries(self):
        config = RetryConfig(max_attempts=3, initial_delay_seconds=0.01)
        executor = RetryExecutor(config)
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ConnectionError("Temporary failure")
            return "success after retries"

        result = executor.execute(operation)
        assert isinstance(result, Success)
        assert result.value == "success after retries"
        assert attempts["count"] == 3


class TestRetryFailures:
    def test_retry_max_attempts_exceeded(self):
        config = RetryConfig(max_attempts=3, initial_delay_seconds=0.01)
        executor = RetryExecutor(config)

        def operation():
            raise ConnectionError("Always fails")

        result = executor.execute(operation)
        assert isinstance(result, ErrorResult)
        assert "Max retry attempts" in result.message
        assert result.context["budget"]["total_attempts"] == 3

    def test_retry_non_retryable_error(self):
        config = RetryConfig(
            max_attempts=3,
            initial_delay_seconds=0.01,
            retryable_error_codes=("RetryableError",),
        )
        executor = RetryExecutor(config)

        def operation():
            raise ValueError("Non-retryable")

        result = executor.execute(operation)
        assert isinstance(result, ErrorResult)
        assert "Non-retryable error" in result.message
        assert result.context["budget"]["total_attempts"] == 1


class TestRetryBudget:
    def test_retry_budget_tracking(self):
        config = RetryConfig(max_attempts=3, initial_delay_seconds=0.01)
        executor = RetryExecutor(config)
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise ConnectionError("Temporary")
            return "success"

        result = executor.execute(operation)
        assert isinstance(result, Success)
        assert result.value == "success"
        assert attempts["count"] == 2


class TestRetryTimeout:
    def test_retry_timeout(self):
        config = RetryConfig(max_attempts=10, initial_delay_seconds=0.5)
        executor = RetryExecutor(config)

        def operation():
            raise ConnectionError("Always fails")

        result = executor.execute(operation, timeout_seconds=0.1)
        assert isinstance(result, ErrorResult)
        assert "timeout" in result.message.lower()


class TestRetryWithCircuitBreaker:
    def test_retry_with_circuit_breaker(self):
        from logging_system.errors import CircuitBreaker, CircuitBreakerConfig

        cb_config = CircuitBreakerConfig(failure_threshold=2)
        circuit_breaker = CircuitBreaker("test", cb_config)
        retry_config = RetryConfig(max_attempts=3, initial_delay_seconds=0.01)
        executor = RetryExecutor(retry_config, circuit_breaker)

        def operation():
            raise ConnectionError("Fails")

        result = executor.execute(operation)
        assert isinstance(result, ErrorResult)


class TestRetryStrategies:
    def test_retry_immediate_strategy(self):
        config = RetryConfig(
            max_attempts=3,
            strategy=ERetryStrategy.IMMEDIATE,
            initial_delay_seconds=0.1,
        )
        executor = RetryExecutor(config)
        start = time.monotonic()
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ConnectionError("Temporary")
            return "success"

        result = executor.execute(operation)
        elapsed = time.monotonic() - start
        assert isinstance(result, Success)
        assert elapsed < 0.2

    def test_retry_exponential_strategy(self):
        config = RetryConfig(
            max_attempts=3,
            strategy=ERetryStrategy.EXPONENTIAL,
            initial_delay_seconds=0.05,
        )
        executor = RetryExecutor(config)
        start = time.monotonic()
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise ConnectionError("Temporary")
            return "success"

        result = executor.execute(operation)
        elapsed = time.monotonic() - start
        assert isinstance(result, Success)
        assert elapsed >= 0.05


class TestRetryRetryableCategories:
    def test_retry_with_transient_category(self):
        config = RetryConfig(
            max_attempts=3,
            retryable_categories=(EErrorCategory.TRANSIENT,),
        )
        executor = RetryExecutor(config)
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise ConnectionError("Transient")
            return "success"

        result = executor.execute(operation)
        assert isinstance(result, Success)
        assert result.value == "success"


class TestRetryCancellation:
    def test_retry_cancellation_mid_retry(self):
        import threading

        config = RetryConfig(max_attempts=10, initial_delay_seconds=0.1)
        executor = RetryExecutor(config)
        cancellation_event = CancellationEvent()
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            if attempts["count"] < 5:
                raise ConnectionError("Temporary")
            return "success"

        def cancel_after_delay():
            time.sleep(0.35)
            cancellation_event.cancel()

        cancel_thread = threading.Thread(target=cancel_after_delay)
        cancel_thread.start()

        result = executor.execute(operation, cancellation_event=cancellation_event)
        cancel_thread.join()

        assert isinstance(result, ErrorResult)
        assert "cancelled" in result.message.lower()
        assert attempts["count"] < 5

    def test_retry_no_cancellation(self):
        config = RetryConfig(max_attempts=3, initial_delay_seconds=0.01)
        executor = RetryExecutor(config)
        cancellation_event = CancellationEvent()
        attempts = {"count": 0}

        def operation():
            attempts["count"] += 1
            if attempts["count"] < 2:
                raise ConnectionError("Temporary")
            return "success"

        result = executor.execute(operation, cancellation_event=cancellation_event)
        assert isinstance(result, Success)
        assert result.value == "success"
        assert cancellation_event.is_set() is False
