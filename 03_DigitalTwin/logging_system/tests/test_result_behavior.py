from __future__ import annotations

import unittest

from logging_system.errors.error_hierarchy import ELogErrorCode
from logging_system.errors.result import (
    ErrorResult,
    Result,
    ResultOps,
    Success,
    bind,
    is_error,
    is_success,
    map,
    or_else,
)


class SuccessTests(unittest.TestCase):
    def test_success_creation(self) -> None:
        result = Success(value=42)
        self.assertEqual(result.value, 42)

    def test_success_bool_true(self) -> None:
        result = Success(value="test")
        self.assertTrue(bool(result))

    def test_success_is_instance(self) -> None:
        result = Success(value=[1, 2, 3])
        self.assertIsInstance(result, Success)


class ErrorResultTests(unittest.TestCase):
    def test_error_result_creation(self) -> None:
        result = ErrorResult(
            code=ELogErrorCode.ADAPTER_NOT_FOUND,
            message="Adapter not found",
        )
        self.assertEqual(result.code, ELogErrorCode.ADAPTER_NOT_FOUND)
        self.assertEqual(result.message, "Adapter not found")
        self.assertEqual(result.context, {})

    def test_error_result_with_context(self) -> None:
        result = ErrorResult(
            code="CUSTOM_ERROR",
            message="Custom error occurred",
            context={"field": "email", "reason": "invalid"},
        )
        self.assertEqual(result.context["field"], "email")

    def test_error_result_bool_false(self) -> None:
        result = ErrorResult(code="ERR", message="error")
        self.assertFalse(bool(result))


class ResultTypeTests(unittest.TestCase):
    def test_result_type_union_success(self) -> None:
        result: Result[int] = Success(100)
        self.assertTrue(is_success(result))
        self.assertFalse(is_error(result))

    def test_result_type_union_error(self) -> None:
        result: Result[int] = ErrorResult(code="ERR", message="error")
        self.assertFalse(is_success(result))
        self.assertTrue(is_error(result))


class ResultOpsTests(unittest.TestCase):
    def test_result_ops_ok(self) -> None:
        result = ResultOps.ok(42)
        self.assertIsInstance(result, Success)
        self.assertEqual(result.value, 42)

    def test_result_ops_err_with_enum(self) -> None:
        result = ResultOps.err(ELogErrorCode.ADAPTER_INIT_FAILED, "Failed to init")
        self.assertIsInstance(result, ErrorResult)
        self.assertEqual(result.code, ELogErrorCode.ADAPTER_INIT_FAILED)
        self.assertEqual(result.message, "Failed to init")

    def test_result_ops_err_with_string(self) -> None:
        result = ResultOps.err("CUSTOM_CODE", "Custom message")
        self.assertEqual(result.code, "CUSTOM_CODE")
        self.assertEqual(result.message, "Custom message")

    def test_result_ops_err_with_kwargs(self) -> None:
        result = ResultOps.err(
            ELogErrorCode.SCHEMA_VALIDATION_FAILED,
            "Validation failed",
            field="email",
            value="not-an-email",
        )
        self.assertEqual(result.context["field"], "email")
        self.assertEqual(result.context["value"], "not-an-email")


class BindTests(unittest.TestCase):
    def test_bind_success(self) -> None:
        def transform(x: int) -> Result[str]:
            return Success(str(x * 2))

        result = bind(Success(5), transform)
        self.assertIsInstance(result, Success)
        self.assertEqual(result.value, "10")

    def test_bind_error_preserves_original(self) -> None:
        def transform(x: int) -> Result[str]:
            return Success(str(x))

        error = ErrorResult(code="ERR", message="original error")
        result = bind(error, transform)
        self.assertIsInstance(result, ErrorResult)
        self.assertEqual(result.code, "ERR")
        self.assertEqual(result.message, "original error")


class MapTests(unittest.TestCase):
    def test_map_success(self) -> None:
        def double(x: int) -> int:
            return x * 2

        result = map(Success(5), double)
        self.assertIsInstance(result, Success)
        self.assertEqual(result.value, 10)

    def test_map_error_preserves_original(self) -> None:
        def double(x: int) -> int:
            return x * 2

        error = ErrorResult(code="ERR", message="error")
        result = map(error, double)
        self.assertIsInstance(result, ErrorResult)
        self.assertEqual(result.code, "ERR")

    def test_map_type_change(self) -> None:
        result = map(Success(42), lambda x: f"value:{x}")
        self.assertIsInstance(result, Success)
        self.assertEqual(result.value, "value:42")


class OrElseTests(unittest.TestCase):
    def test_or_else_success_returns_value(self) -> None:
        result: Result[int] = Success(100)
        self.assertEqual(or_else(result, 0), 100)

    def test_or_else_error_returns_fallback(self) -> None:
        error = ErrorResult(code="ERR", message="error")
        self.assertEqual(or_else(error, 42), 42)

    def test_or_else_with_none_fallback(self) -> None:
        error = ErrorResult(code="ERR", message="error")
        result: Result[None] = or_else(error, None)
        self.assertIsNone(result)


class IsSuccessTests(unittest.TestCase):
    def test_is_success_with_success(self) -> None:
        self.assertTrue(is_success(Success("value")))

    def test_is_success_with_error(self) -> None:
        self.assertFalse(is_success(ErrorResult("ERR", "error")))


class IsErrorTests(unittest.TestCase):
    def test_is_error_with_error(self) -> None:
        self.assertTrue(is_error(ErrorResult("ERR", "error")))

    def test_is_error_with_success(self) -> None:
        self.assertFalse(is_error(Success("value")))


if __name__ == "__main__":
    unittest.main()
