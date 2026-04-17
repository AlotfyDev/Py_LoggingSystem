from __future__ import annotations

import unittest

from logging_system.errors.error_hierarchy import (
    EErrorCategory,
    ELogErrorCode,
    ERetryableError,
    ErrorContext,
)


class EErrorCategoryTests(unittest.TestCase):
    def test_transient_value(self) -> None:
        self.assertEqual(EErrorCategory.TRANSIENT.value, "TRANSIENT")

    def test_permanent_value(self) -> None:
        self.assertEqual(EErrorCategory.PERMANENT.value, "PERMANENT")

    def test_partial_value(self) -> None:
        self.assertEqual(EErrorCategory.PARTIAL.value, "PARTIAL")

    def test_string_coercion(self) -> None:
        self.assertEqual(EErrorCategory.TRANSIENT, "TRANSIENT")


class ERetryableErrorTests(unittest.TestCase):
    def test_network_unreachable_value(self) -> None:
        self.assertEqual(ERetryableError.NETWORK_UNREACHABLE.value, "NETWORK_UNREACHABLE")

    def test_connection_timeout_value(self) -> None:
        self.assertEqual(ERetryableError.CONNECTION_TIMEOUT.value, "CONNECTION_TIMEOUT")

    def test_read_timeout_value(self) -> None:
        self.assertEqual(ERetryableError.READ_TIMEOUT.value, "READ_TIMEOUT")

    def test_service_unavailable_value(self) -> None:
        self.assertEqual(ERetryableError.SERVICE_UNAVAILABLE.value, "SERVICE_UNAVAILABLE")

    def test_rate_limited_value(self) -> None:
        self.assertEqual(ERetryableError.RATE_LIMITED.value, "RATE_LIMITED")

    def test_backpressure_value(self) -> None:
        self.assertEqual(ERetryableError.BACKPRESSURE.value, "BACKPRESSURE")

    def test_transient_binding_error_value(self) -> None:
        self.assertEqual(ERetryableError.TRANSIENT_BINDING_ERROR.value, "TRANSIENT_BINDING_ERROR")

    def test_string_coercion(self) -> None:
        self.assertEqual(ERetryableError.SERVICE_UNAVAILABLE, "SERVICE_UNAVAILABLE")


class ELogErrorCodeTests(unittest.TestCase):
    def test_adapter_not_found_value(self) -> None:
        self.assertEqual(ELogErrorCode.ADAPTER_NOT_FOUND.value, "ADAPTER_NOT_FOUND")

    def test_adapter_init_failed_value(self) -> None:
        self.assertEqual(ELogErrorCode.ADAPTER_INIT_FAILED.value, "ADAPTER_INIT_FAILED")

    def test_adapter_dispatch_failed_value(self) -> None:
        self.assertEqual(ELogErrorCode.ADAPTER_DISPATCH_FAILED.value, "ADAPTER_DISPATCH_FAILED")

    def test_adapter_timeout_value(self) -> None:
        self.assertEqual(ELogErrorCode.ADAPTER_TIMEOUT.value, "ADAPTER_TIMEOUT")

    def test_schema_validation_failed_value(self) -> None:
        self.assertEqual(ELogErrorCode.SCHEMA_VALIDATION_FAILED.value, "SCHEMA_VALIDATION_FAILED")

    def test_schema_missing_required_field_value(self) -> None:
        self.assertEqual(ELogErrorCode.SCHEMA_MISSING_REQUIRED_FIELD.value, "SCHEMA_MISSING_REQUIRED_FIELD")

    def test_schema_invalid_field_type_value(self) -> None:
        self.assertEqual(ELogErrorCode.SCHEMA_INVALID_FIELD_TYPE.value, "SCHEMA_INVALID_FIELD_TYPE")

    def test_binding_failed_value(self) -> None:
        self.assertEqual(ELogErrorCode.BINDING_FAILED.value, "BINDING_FAILED")

    def test_binding_missing_adapter_key_value(self) -> None:
        self.assertEqual(ELogErrorCode.BINDING_MISSING_ADAPTER_KEY.value, "BINDING_MISSING_ADAPTER_KEY")

    def test_binding_invalid_payload_value(self) -> None:
        self.assertEqual(ELogErrorCode.BINDING_INVALID_PAYLOAD.value, "BINDING_INVALID_PAYLOAD")

    def test_queue_full_value(self) -> None:
        self.assertEqual(ELogErrorCode.QUEUE_FULL.value, "QUEUE_FULL")

    def test_queue_put_failed_value(self) -> None:
        self.assertEqual(ELogErrorCode.QUEUE_PUT_FAILED.value, "QUEUE_PUT_FAILED")

    def test_queue_get_failed_value(self) -> None:
        self.assertEqual(ELogErrorCode.QUEUE_GET_FAILED.value, "QUEUE_GET_FAILED")

    def test_envelope_malformed_value(self) -> None:
        self.assertEqual(ELogErrorCode.ENVELOPE_MALFORMED.value, "ENVELOPE_MALFORMED")

    def test_envelope_missing_content_value(self) -> None:
        self.assertEqual(ELogErrorCode.ENVELOPE_MISSING_CONTENT.value, "ENVELOPE_MISSING_CONTENT")

    def test_envelope_serialization_failed_value(self) -> None:
        self.assertEqual(ELogErrorCode.ENVELOPE_SERIALIZATION_FAILED.value, "ENVELOPE_SERIALIZATION_FAILED")

    def test_config_invalid_value(self) -> None:
        self.assertEqual(ELogErrorCode.CONFIG_INVALID.value, "CONFIG_INVALID")

    def test_config_missing_required_value(self) -> None:
        self.assertEqual(ELogErrorCode.CONFIG_MISSING_REQUIRED.value, "CONFIG_MISSING_REQUIRED")

    def test_profile_not_found_value(self) -> None:
        self.assertEqual(ELogErrorCode.PROFILE_NOT_FOUND.value, "PROFILE_NOT_FOUND")

    def test_profile_activation_failed_value(self) -> None:
        self.assertEqual(ELogErrorCode.PROFILE_ACTIVATION_FAILED.value, "PROFILE_ACTIVATION_FAILED")

    def test_catalog_error_value(self) -> None:
        self.assertEqual(ELogErrorCode.CATALOG_ERROR.value, "CATALOG_ERROR")

    def test_container_error_value(self) -> None:
        self.assertEqual(ELogErrorCode.CONTAINER_ERROR.value, "CONTAINER_ERROR")

    def test_resource_exhausted_value(self) -> None:
        self.assertEqual(ELogErrorCode.RESOURCE_EXHAUSTED.value, "RESOURCE_EXHAUSTED")

    def test_unknown_error_value(self) -> None:
        self.assertEqual(ELogErrorCode.UNKNOWN_ERROR.value, "UNKNOWN_ERROR")


class EnumSerializationTests(unittest.TestCase):
    def test_error_category_json_serializable(self) -> None:
        import json
        result = json.dumps(EErrorCategory.TRANSIENT.value)
        self.assertEqual(result, '"TRANSIENT"')

    def test_retryable_error_json_serializable(self) -> None:
        import json
        result = json.dumps(ERetryableError.SERVICE_UNAVAILABLE.value)
        self.assertEqual(result, '"SERVICE_UNAVAILABLE"')

    def test_log_error_code_json_serializable(self) -> None:
        import json
        result = json.dumps(ELogErrorCode.UNKNOWN_ERROR.value)
        self.assertEqual(result, '"UNKNOWN_ERROR"')


class ErrorContextTests(unittest.TestCase):
    def test_error_context_creation_with_required_fields(self) -> None:
        ctx = ErrorContext(
            error_code=ELogErrorCode.ADAPTER_DISPATCH_FAILED,
            category=EErrorCategory.TRANSIENT,
        )
        self.assertEqual(ctx.error_code, ELogErrorCode.ADAPTER_DISPATCH_FAILED)
        self.assertEqual(ctx.category, EErrorCategory.TRANSIENT)
        self.assertIsNotNone(ctx.timestamp_utc)
        self.assertEqual(ctx.metadata, {})

    def test_error_context_with_metadata(self) -> None:
        ctx = ErrorContext(
            error_code=ELogErrorCode.SCHEMA_VALIDATION_FAILED,
            category=EErrorCategory.PERMANENT,
            metadata={"field": "email", "reason": "invalid_format"},
        )
        self.assertEqual(ctx.metadata["field"], "email")
        self.assertEqual(ctx.metadata["reason"], "invalid_format")

    def test_error_context_with_original_error(self) -> None:
        original = ValueError("test error")
        ctx = ErrorContext(
            error_code=ELogErrorCode.BINDING_FAILED,
            category=EErrorCategory.PERMANENT,
            original_error=original,
        )
        self.assertIs(ctx.original_error, original)
        self.assertEqual(str(ctx.original_error), "test error")

    def test_error_context_with_stack_trace(self) -> None:
        ctx = ErrorContext(
            error_code=ELogErrorCode.UNKNOWN_ERROR,
            category=EErrorCategory.TRANSIENT,
            stack_trace="Traceback (most recent call last):\n  File ...",
        )
        self.assertIsNotNone(ctx.stack_trace)

    def test_error_context_is_frozen(self) -> None:
        ctx = ErrorContext(
            error_code=ELogErrorCode.ADAPTER_NOT_FOUND,
            category=EErrorCategory.PERMANENT,
        )
        with self.assertRaises(AttributeError):
            ctx.error_code = ELogErrorCode.ADAPTER_INIT_FAILED  # type: ignore[attr-defined]

    def test_is_retryable_transient(self) -> None:
        ctx = ErrorContext(
            error_code=ELogErrorCode.ADAPTER_TIMEOUT,
            category=EErrorCategory.TRANSIENT,
        )
        self.assertTrue(ctx.is_retryable())

    def test_is_retryable_partial(self) -> None:
        ctx = ErrorContext(
            error_code=ELogErrorCode.QUEUE_FULL,
            category=EErrorCategory.PARTIAL,
        )
        self.assertTrue(ctx.is_retryable())

    def test_is_retryable_permanent(self) -> None:
        ctx = ErrorContext(
            error_code=ELogErrorCode.ADAPTER_NOT_FOUND,
            category=EErrorCategory.PERMANENT,
        )
        self.assertFalse(ctx.is_retryable())

    def test_to_dict(self) -> None:
        ctx = ErrorContext(
            error_code=ELogErrorCode.ADAPTER_DISPATCH_FAILED,
            category=EErrorCategory.TRANSIENT,
            metadata={"adapter_key": "telemetry"},
        )
        d = ctx.to_dict()
        self.assertEqual(d["error_code"], "ADAPTER_DISPATCH_FAILED")
        self.assertEqual(d["category"], "TRANSIENT")
        self.assertIn("timestamp_utc", d)
        self.assertEqual(d["metadata"]["adapter_key"], "telemetry")
        self.assertIsNone(d["original_error"])
        self.assertIsNone(d["stack_trace"])

    def test_to_dict_with_original_error(self) -> None:
        original = RuntimeError("connection refused")
        ctx = ErrorContext(
            error_code=ELogErrorCode.ADAPTER_TIMEOUT,
            category=EErrorCategory.TRANSIENT,
            original_error=original,
        )
        d = ctx.to_dict()
        self.assertEqual(d["original_error"], "connection refused")


if __name__ == "__main__":
    unittest.main()
