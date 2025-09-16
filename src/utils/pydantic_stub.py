"""Simplified stand-ins for the bits of Pydantic used in tests.

The real :mod:`pydantic` package is fairly heavy and is not available inside
the execution sandbox the tests run in.  To keep the production code testable
without pulling the dependency, this module implements a tiny subset of the
Pydantic ``BaseModel`` API:

* attribute declaration via type hints
* simple coercion for nested ``BaseModel`` instances, ``Enum`` values and
  ``List``/``Optional`` containers
* ``model_dump``/``dict`` helpers used by the storage layer

The intent is not to replace Pydantic in production (the real dependency is
still required when running the application) but to give unit tests a light
weight fallback so imports succeed.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, TypeVar, Union, get_args, get_origin


T = TypeVar("T", bound="BaseModel")


def _is_none_type(annotation: Any) -> bool:
    return annotation is type(None)  # noqa: E721 - intentional identity check


class BaseModel:
    """Very small subset of ``pydantic.BaseModel`` used in our code paths."""

    def __init__(self, **data: Any) -> None:
        annotations = getattr(self.__class__, "__annotations__", {})
        for name, annotation in annotations.items():
            if name in data:
                value = data.pop(name)
            elif hasattr(self.__class__, name):
                value = getattr(self.__class__, name)
            else:
                value = None
            value = self._coerce(value, annotation)
            setattr(self, name, value)
        # preserve any additional keys for compatibility
        for key, value in data.items():
            setattr(self, key, value)

    # ``pydantic`` exposes ``model_dump`` (v2) and ``dict`` (v1).  We mimic both.
    def model_dump(self) -> Dict[str, Any]:
        annotations = getattr(self.__class__, "__annotations__", {})
        return {name: self._dump(getattr(self, name)) for name in annotations}

    def dict(self) -> Dict[str, Any]:  # pragma: no cover - alias for compatibility
        return self.model_dump()

    # -------- helpers --------
    @classmethod
    def _coerce(cls, value: Any, annotation: Any) -> Any:
        if value is None:
            return None
        origin = get_origin(annotation)
        args = get_args(annotation)
        if origin in (list, List):
            inner = args[0] if args else Any
            return [cls._coerce(item, inner) for item in (value or [])]
        if origin is Union:
            for arg in args:
                if _is_none_type(arg):
                    continue
                return cls._coerce(value, arg)
            return value
        if isinstance(annotation, type):
            if issubclass(annotation, BaseModel) and isinstance(value, dict):
                return annotation(**value)
            if issubclass(annotation, Enum) and not isinstance(value, Enum):
                return annotation(value)
        return value

    @staticmethod
    def _dump(value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump()
        if isinstance(value, list):
            return [BaseModel._dump(v) for v in value]
        if isinstance(value, Enum):
            return value.value
        return value
