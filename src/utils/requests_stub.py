"""Very small stub for :mod:`requests` used in test environments.

The real ``requests`` library is not available in the sandbox, but the service
clients import it eagerly.  This module exposes a ``post`` function that raises
an informative error so production code still knows that the dependency is
required, while keeping imports working for unit tests that stub network calls.
"""
from __future__ import annotations

from typing import Any


class _RequestsStub:
    def __getattr__(self, name: str) -> Any:  # pragma: no cover - rarely exercised
        raise RuntimeError(
            "The 'requests' package is required for this operation. Install it via "
            "'pip install requests'."
        )

    def post(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            "HTTP requests are not available in this test environment."
        )


requests = _RequestsStub()
