from __future__ import annotations

import pytest

from logging_system.errors import (
    EErrorCategory,
    EJitterMode,
    ERetryStrategy,
    RetryAttempt,
    RetryBudget,
    RetryConfig,
)


class TestRetryStrategyEnum:
    def test_retry_strategy_values(self):
        assert ERetryStrategy.IMMEDIATE.value == "IMMEDIATE"
        assert ERetryStrategy.LINEAR.value == "LINEAR"
        assert ERetryStrategy.EXPONENTIAL.value == "EXPONENTIAL"
        assert ERetryStrategy.FIBONACCI.value == "FIBONACCI"

    def test_retry_strategy_count(self):
        assert len(ERetryStrategy) == 4

    def test_retry_strategy_is_string_enum(self):
        assert isinstance(ERetryStrategy.EXPONENTIAL, str)
        assert ERetryStrategy.EXPONENTIAL == "EXPONENTIAL"


class TestEJitterModeEnum:
    def test_jitter_mode_values(self):
        assert EJitterMode.NONE.value == "NONE"
        assert EJitterMode.FULL.value == "FULL"
        assert EJitterMode.DECORRELATED.value == "DECORRELATED"

    def test_jitter_mode_count(self):
        assert len(EJitterMode) == 3

    def test_jitter_mode_is_string_enum(self):
        assert isinstance(EJitterMode.FULL, str)
        assert EJitterMode.FULL == "FULL"


class TestRetryConfigDefaults:
    def test_retry_config_defaults(self):
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.initial_delay_seconds == 0.1
        assert config.max_delay_seconds == 60.0
        assert config.timeout_seconds is None
        assert config.strategy == ERetryStrategy.EXPONENTIAL
        assert config.jitter_mode == EJitterMode.FULL
        assert config.retryable_categories == ()
        assert config.retryable_error_codes == ()

    def test_retry_config_is_frozen(self):
        config = RetryConfig()
        with pytest.raises(Exception):
            config.max_attempts = 5

    def test_retry_config_custom_values(self):
        config = RetryConfig(
            max_attempts=5,
            initial_delay_seconds=0.5,
            max_delay_seconds=120.0,
            timeout_seconds=30.0,
            strategy=ERetryStrategy.LINEAR,
            jitter_mode=EJitterMode.NONE,
        )
        assert config.max_attempts == 5
        assert config.initial_delay_seconds == 0.5
        assert config.max_delay_seconds == 120.0
        assert config.timeout_seconds == 30.0
        assert config.strategy == ERetryStrategy.LINEAR
        assert config.jitter_mode == EJitterMode.NONE


class TestRetryConfigValidation:
    def test_retry_config_max_attempts_less_than_one_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RetryConfig(max_attempts=0)

    def test_retry_config_max_attempts_negative_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            RetryConfig(max_attempts=-1)

    def test_retry_config_initial_delay_negative_raises(self):
        with pytest.raises(ValueError, match="initial_delay"):
            RetryConfig(initial_delay_seconds=-0.1)

    def test_retry_config_max_delay_negative_raises(self):
        with pytest.raises(ValueError, match="max_delay"):
            RetryConfig(max_delay_seconds=-1.0)

    def test_retry_config_timeout_negative_raises(self):
        with pytest.raises(ValueError, match="timeout"):
            RetryConfig(timeout_seconds=-5.0)

    def test_retry_config_valid_values(self):
        config = RetryConfig(
            max_attempts=1,
            initial_delay_seconds=0.0,
            max_delay_seconds=0.0,
            timeout_seconds=0.0,
        )
        assert config.max_attempts == 1
        assert config.initial_delay_seconds == 0.0


class TestRetryConfigRetryability:
    def test_is_error_retryable_by_category(self):
        config = RetryConfig(retryable_categories=(EErrorCategory.TRANSIENT,))
        assert config.is_error_retryable(None, EErrorCategory.TRANSIENT) is True
        assert config.is_error_retryable(None, EErrorCategory.PERMANENT) is False

    def test_is_error_retryable_by_code(self):
        config = RetryConfig(retryable_error_codes=("NETWORK_ERROR",))
        assert config.is_error_retryable("NETWORK_ERROR", None) is True
        assert config.is_error_retryable("OTHER_ERROR", None) is False

    def test_is_error_retryable_both_none(self):
        config = RetryConfig()
        assert config.is_error_retryable(None, None) is False


class TestRetryAttempt:
    def test_retry_attempt_creation(self):
        attempt = RetryAttempt(attempt_number=1, success=True)
        assert attempt.attempt_number == 1
        assert attempt.success is True
        assert attempt.delay_seconds == 0.0
        assert attempt.error_code is None
        assert attempt.error_message is None
        assert attempt.timestamp_utc is not None

    def test_retry_attempt_with_error(self):
        attempt = RetryAttempt(
            attempt_number=2,
            success=False,
            delay_seconds=1.0,
            error_code="TIMEOUT",
            error_message="Connection timed out",
        )
        assert attempt.attempt_number == 2
        assert attempt.success is False
        assert attempt.delay_seconds == 1.0
        assert attempt.error_code == "TIMEOUT"
        assert attempt.error_message == "Connection timed out"

    def test_retry_attempt_is_frozen(self):
        attempt = RetryAttempt(attempt_number=1)
        with pytest.raises(Exception):
            attempt.attempt_number = 5


class TestRetryBudget:
    def test_retry_budget_defaults(self):
        budget = RetryBudget()
        assert budget.total_attempts == 0
        assert budget.successful_attempts == 0
        assert budget.failed_attempts == 0
        assert budget.total_delay_seconds == 0.0
        assert budget.first_attempt_timestamp is None
        assert budget.last_attempt_timestamp is None
        assert budget.attempts == ()

    def test_retry_budget_add_success_attempt(self):
        budget = RetryBudget()
        attempt = RetryAttempt(attempt_number=1, success=True, delay_seconds=0.1)
        new_budget = budget.add_attempt(attempt)
        assert new_budget.total_attempts == 1
        assert new_budget.successful_attempts == 1
        assert new_budget.failed_attempts == 0
        assert new_budget.total_delay_seconds == 0.1
        assert new_budget.first_attempt_timestamp is not None
        assert new_budget.last_attempt_timestamp is not None
        assert len(new_budget.attempts) == 1

    def test_retry_budget_add_failed_attempt(self):
        budget = RetryBudget()
        attempt = RetryAttempt(
            attempt_number=1,
            success=False,
            delay_seconds=0.5,
            error_code="TIMEOUT",
        )
        new_budget = budget.add_attempt(attempt)
        assert new_budget.total_attempts == 1
        assert new_budget.successful_attempts == 0
        assert new_budget.failed_attempts == 1
        assert new_budget.total_delay_seconds == 0.5

    def test_retry_budget_add_multiple_attempts(self):
        budget = RetryBudget()
        attempt1 = RetryAttempt(attempt_number=1, success=False, delay_seconds=0.1)
        attempt2 = RetryAttempt(attempt_number=2, success=False, delay_seconds=0.2)
        attempt3 = RetryAttempt(attempt_number=3, success=True, delay_seconds=0.3)
        budget = budget.add_attempt(attempt1)
        budget = budget.add_attempt(attempt2)
        budget = budget.add_attempt(attempt3)
        assert budget.total_attempts == 3
        assert budget.successful_attempts == 1
        assert budget.failed_attempts == 2
        assert budget.total_delay_seconds == pytest.approx(0.6)
        assert len(budget.attempts) == 3

    def test_retry_budget_is_frozen(self):
        budget = RetryBudget()
        with pytest.raises(Exception):
            budget.total_attempts = 5

    def test_retry_budget_to_dict(self):
        budget = RetryBudget()
        attempt = RetryAttempt(
            attempt_number=1,
            success=True,
            delay_seconds=0.1,
        )
        budget = budget.add_attempt(attempt)
        result = budget.to_dict()
        assert result["total_attempts"] == 1
        assert result["successful_attempts"] == 1
        assert result["failed_attempts"] == 0
        assert result["total_delay_seconds"] == 0.1
        assert len(result["attempts"]) == 1
        assert result["attempts"][0]["attempt_number"] == 1
        assert result["attempts"][0]["success"] is True
