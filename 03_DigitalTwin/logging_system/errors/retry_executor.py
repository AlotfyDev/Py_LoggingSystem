from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable, TypeVar

from .backoff_calculator import BackoffCalculator
from .error_hierarchy import ELogErrorCode
from .result import ErrorResult, Result, Success
from .retry_policy import RetryAttempt, RetryBudget, RetryConfig

if TYPE_CHECKING:
    from .circuit_breaker import CircuitBreaker

T = TypeVar("T")


class RetryTimeoutError(Exception):
    pass


class RetryExhaustedError(Exception):
    pass


class RetryExecutor:
    def __init__(
        self,
        config: RetryConfig | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._config = config or RetryConfig()
        self._circuit_breaker = circuit_breaker
        self._backoff = BackoffCalculator(
            initial_delay_seconds=self._config.initial_delay_seconds,
            max_delay_seconds=self._config.max_delay_seconds,
            strategy=self._config.strategy,
            jitter_mode=self._config.jitter_mode,
        )

    def execute(
        self,
        operation: Callable[[], T],
        timeout_seconds: float | None = None,
        cancellation_event: "CancellationEvent | None" = None,
    ) -> Result[T]:
        budget = RetryBudget()
        timeout = timeout_seconds or self._config.timeout_seconds
        deadline = time.monotonic() + timeout if timeout is not None else None

        for attempt_number in range(1, self._config.max_attempts + 1):
            if cancellation_event is not None and cancellation_event.is_set():
                return ErrorResult(
                    code=ELogErrorCode.UNKNOWN_ERROR,
                    message="Operation cancelled",
                    context={"budget": budget.to_dict()},
                )

            if deadline is not None and time.monotonic() >= deadline:
                return ErrorResult(
                    code=ELogErrorCode.UNKNOWN_ERROR,
                    message=f"Retry timeout exceeded after {budget.total_attempts} attempts",
                    context={"budget": budget.to_dict()},
                )

            delay = self._backoff.calculate_delay(attempt_number)
            if attempt_number > 1 and delay > 0:
                remaining = deadline - time.monotonic() if deadline else None
                if remaining is not None and delay > remaining:
                    return ErrorResult(
                        code=ELogErrorCode.UNKNOWN_ERROR,
                        message=f"Retry timeout exceeded during backoff",
                        context={"budget": budget.to_dict()},
                    )
                time.sleep(delay)

            try:
                if self._circuit_breaker is not None:
                    result = self._circuit_breaker.call(operation)
                else:
                    result = operation()

                attempt = RetryAttempt(
                    attempt_number=attempt_number,
                    delay_seconds=delay,
                    success=True,
                )
                budget = budget.add_attempt(attempt)

                return Success(result)

            except Exception as e:
                attempt = RetryAttempt(
                    attempt_number=attempt_number,
                    delay_seconds=delay,
                    success=False,
                    error_code=type(e).__name__,
                    error_message=str(e),
                )
                budget = budget.add_attempt(attempt)

                if attempt_number >= self._config.max_attempts:
                    return ErrorResult(
                        code=ELogErrorCode.UNKNOWN_ERROR,
                        message=f"Max retry attempts ({self._config.max_attempts}) exceeded",
                        context={"budget": budget.to_dict()},
                    )

                if not self._should_retry(e):
                    return ErrorResult(
                        code=ELogErrorCode.UNKNOWN_ERROR,
                        message=f"Non-retryable error: {e}",
                        context={"budget": budget.to_dict()},
                    )

        return ErrorResult(
            code=ELogErrorCode.UNKNOWN_ERROR,
            message=f"Max retry attempts ({self._config.max_attempts}) exceeded",
            context={"budget": budget.to_dict()},
        )

    def _should_retry(self, error: Exception) -> bool:
        error_code = type(error).__name__

        if self._config.retryable_error_codes:
            if error_code not in self._config.retryable_error_codes:
                return False

        return True

    @property
    def config(self) -> RetryConfig:
        return self._config
