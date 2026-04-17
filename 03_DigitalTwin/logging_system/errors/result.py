from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

if TYPE_CHECKING:
    from logging_system.errors.error_hierarchy import ELogErrorCode

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True)
class Success(Generic[T]):
    value: T

    def __bool__(self) -> bool:
        return True


@dataclass(frozen=True)
class ErrorResult:
    code: ELogErrorCode | str
    message: str
    context: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return False


Result = Success[T] | ErrorResult


@dataclass
class ResultOps:
    @staticmethod
    def ok(value: T) -> Success[T]:
        return Success(value)

    @staticmethod
    def err(code: ELogErrorCode | str, message: str, **kwargs: Any) -> ErrorResult:
        return ErrorResult(code=code, message=message, context=kwargs)


def bind(result: Result[T], func: Callable[[T], Result[U]]) -> Result[U]:
    if isinstance(result, Success):
        return func(result.value)
    return ErrorResult(code=result.code, message=result.message, context=result.context)


def map(result: Result[T], func: Callable[[T], U]) -> Result[U]:
    if isinstance(result, Success):
        return Success(func(result.value))
    return ErrorResult(code=result.code, message=result.message, context=result.context)


def or_else(result: Result[T], fallback: T) -> T:
    if isinstance(result, Success):
        return result.value
    return fallback


def is_success(result: Result[T]) -> bool:
    return isinstance(result, Success)


def is_error(result: Result[T]) -> bool:
    return isinstance(result, ErrorResult)
