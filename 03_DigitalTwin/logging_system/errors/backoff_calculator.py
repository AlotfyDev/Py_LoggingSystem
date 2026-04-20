from __future__ import annotations

import random

from .retry_policy import EJitterMode, ERetryStrategy


def _fibonacci(n: int) -> int:
    if n <= 1:
        return 1
    a, b = 1, 1
    for _ in range(2, n):
        a, b = b, a + b
    return b


class BackoffCalculator:
    def __init__(
        self,
        initial_delay_seconds: float = 0.1,
        max_delay_seconds: float = 60.0,
        strategy: ERetryStrategy | None = None,
        jitter_mode: EJitterMode | None = None,
    ) -> None:
        self._initial_delay = initial_delay_seconds
        self._max_delay = max_delay_seconds
        self._strategy = strategy
        self._jitter_mode = jitter_mode
        self._last_base_delay = initial_delay_seconds

    def calculate_delay(
        self,
        attempt: int,
        strategy: ERetryStrategy | None = None,
        jitter_mode: EJitterMode | None = None,
    ) -> float:
        strat = strategy or self._strategy or ERetryStrategy.EXPONENTIAL
        jitter = jitter_mode or self._jitter_mode or EJitterMode.FULL

        base_delay = self._calculate_base_delay(attempt, strat)

        with_jitter = self._apply_jitter(base_delay, attempt, jitter)

        capped = min(with_jitter, self._max_delay)
        return max(0.0, capped)

    def _calculate_base_delay(self, attempt: int, strategy: ERetryStrategy) -> float:
        if strategy == ERetryStrategy.IMMEDIATE:
            return 0.0

        if strategy == ERetryStrategy.LINEAR:
            return self._initial_delay * attempt

        if strategy == ERetryStrategy.EXPONENTIAL:
            return self._initial_delay * (2 ** (attempt - 1))

        if strategy == ERetryStrategy.FIBONACCI:
            return self._initial_delay * _fibonacci(attempt)

        return self._initial_delay * (2 ** (attempt - 1))

    def _apply_jitter(self, base_delay: float, attempt: int, jitter_mode: EJitterMode) -> float:
        if jitter_mode == EJitterMode.NONE:
            return base_delay

        if jitter_mode == EJitterMode.FULL:
            return base_delay * (0.5 + random.random() * 0.5)

        if jitter_mode == EJitterMode.DECORRELATED:
            self._last_base_delay = min(
                self._last_base_delay * random.uniform(1.3, 3.0),
                self._max_delay,
            )
            return self._last_base_delay

        return base_delay

    @property
    def initial_delay(self) -> float:
        return self._initial_delay

    @property
    def max_delay(self) -> float:
        return self._max_delay
