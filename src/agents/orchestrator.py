"""Simple orchestrator that routes queries to specialized agents."""
from __future__ import annotations
from typing import Any


class OrchestratorAgent:
    """Routes user queries to structured or unstructured agents.

    The routing heuristics are intentionally lightweight; in a production
    system this would rely on an LLM or intent classifier.
    """

    def __init__(
        self,
        structured_agent: Any,
        unstructured_agent: Any,
        graph_service: Any | None = None,
    ) -> None:
        self._structured_agent = structured_agent
        self._unstructured_agent = unstructured_agent
        self._graph_service = graph_service

    def handle(self, query: str) -> Any:
        """Return a response by delegating to the appropriate agent."""
        if self._graph_service and self._needs_graph(query):
            return self._graph_service.get_resource(query)
        if self._is_structured_query(query):
            return self._structured_agent.query(query)
        return self._unstructured_agent.search(query)

    @staticmethod
    def _is_structured_query(query: str) -> bool:
        keywords = {"invoice", "table", "rate", "sql"}
        text = query.lower()
        return any(k in text for k in keywords)

    @staticmethod
    def _needs_graph(query: str) -> bool:
        keywords = {"email", "calendar", "file", "meeting"}
        text = query.lower()
        return any(k in text for k in keywords)
