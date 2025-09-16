"""Lightweight stand-ins for :mod:`azure.functions` when SDK is unavailable.

The local test environment for this repository does not always have the real
Azure Functions package installed.  These helpers provide the tiny subset of
classes/decorators that our code and tests use so that modules can be imported
without errors.  They deliberately keep behaviour simple and deterministic –
enough to let unit tests exercise the higher-level logic without requiring the
actual Azure runtime.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional


class HttpResponse:
    """Minimal HTTP response compatible with the Azure Functions signature."""

    def __init__(
        self,
        body: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.body = body
        self.status_code = status_code
        self.headers = headers or {}


class HttpRequest:
    """Minimal HTTP request wrapper supporting the bits our handlers use."""

    def __init__(
        self,
        method: str = "GET",
        url: str | None = None,
        headers: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        route_params: Optional[Dict[str, Any]] = None,
        body: Any = None,
    ) -> None:
        self.method = method
        self.url = url or ""
        self.headers = headers or {}
        self.params = params or {}
        self.route_params = route_params or {}
        self._body = body

    def get_json(self) -> Any:
        import json

        if self._body is None:
            raise ValueError("No JSON body provided")
        if isinstance(self._body, (bytes, bytearray)):
            return json.loads(self._body.decode("utf-8"))
        if isinstance(self._body, str):
            return json.loads(self._body)
        return self._body


class Blueprint:
    """Stores decorated functions so tests can reference them."""

    def __init__(self) -> None:
        self._functions: List[Callable[..., Any]] = []

    def _register(self, func: Callable[..., Any]) -> Callable[..., Any]:
        if func not in self._functions:
            self._functions.append(func)
        return func

    def function_name(self, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            setattr(func, "_function_name", name)
            return self._register(func)

        return decorator

    def route(
        self,
        route: str,
        methods: Optional[Iterable[str]] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            setattr(func, "_route", route)
            setattr(func, "_methods", list(methods or []))
            return self._register(func)

        return decorator

    @property
    def functions(self) -> List[Callable[..., Any]]:
        return list(self._functions)


class FunctionApp:
    """Very small stand-in for ``azure.functions.FunctionApp``."""

    def __init__(self) -> None:
        self._functions: Dict[str, Callable[..., Any]] = {}

    def register_functions(self, blueprint: Blueprint) -> None:
        for func in blueprint.functions:
            name = getattr(func, "_function_name", func.__name__)
            self._functions[name] = func

    def function_name(self, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            setattr(func, "_function_name", name)
            self._functions[name] = func
            return func

        return decorator

    def route(
        self,
        route: str,
        methods: Optional[Iterable[str]] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            setattr(func, "_route", route)
            setattr(func, "_methods", list(methods or []))
            return func

        return decorator


class _FunctionsModule:
    Blueprint = Blueprint
    FunctionApp = FunctionApp
    HttpRequest = HttpRequest
    HttpResponse = HttpResponse


functions = _FunctionsModule()
