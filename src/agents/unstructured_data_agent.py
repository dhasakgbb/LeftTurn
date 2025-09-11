"""Agent for searching unstructured documents."""
from __future__ import annotations
from typing import Any


class UnstructuredDataAgent:
    def __init__(self, search_service: Any) -> None:
        self._search_service = search_service

    def search(self, query: str) -> Any:
        """Search unstructured content via the configured service."""
        return self._search_service.search(query)
