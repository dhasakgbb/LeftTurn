"""Agent for searching unstructured documents."""
from __future__ import annotations
from typing import Any
import os


class UnstructuredDataAgent:
    def __init__(self, search_service: Any) -> None:
        self._search_service = search_service
        self._use_semantic = (
            os.getenv("SEARCH_USE_SEMANTIC", "false").lower() in {"1", "true", "yes"}
        )

    def search(self, query: str) -> Any:
        """Search unstructured content via the configured service."""
        return self._search_service.search(query, semantic=self._use_semantic)

    def search_with_meta(self, query: str) -> Any:
        """Search and return passages with optional metadata if available."""
        # If the underlying service supports returning fields, use it
        try:
            return self._search_service.search(
                query, return_fields=True, semantic=self._use_semantic
            )
        except TypeError:
            # Older service signatures may not support return_fields
            return [
                {"text": t, "file": None, "page": None, "clauseId": None}
                for t in self._search_service.search(query)
            ]
