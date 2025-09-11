"""Simple orchestrator that routes queries to specialized agents."""
from __future__ import annotations
from typing import Any


class OrchestratorAgent:
    """Routes user queries to structured or unstructured agents.

    Uses deterministic, keyword‑based intent rules to keep behavior
    predictable and safe. Swap this out for an LLM classifier if desired.
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

    def handle(self, query: Any) -> Any:
        """Return a response by delegating to the appropriate agent."""
        if isinstance(query, tuple):
            template, params = query
            return self._structured_agent.query(template, params)
        if (
            self._graph_service
            and isinstance(query, str)
            and self._needs_graph(query)
        ):
            return self._graph_service.get_resource(query)
        return self._unstructured_agent.search(query)

    def handle_with_citations(self, query: Any) -> dict:
        """Return tool result with lightweight citations and routing metadata.

        Structure:
        {
          "tool": "fabric_sql|ai_search|graph",
          "result": <tool result>,
          "citations": [ { ... } ]
        }
        """
        if isinstance(query, tuple):
            template, params = query
            data = self._structured_agent.query(template, params)
            return {
                "tool": "fabric_sql",
                "result": data,
                "citations": [
                    {
                        "type": "table",
                        "source": "fabric",
                        "template": template,
                        "parameters": params,
                    }
                ],
            }
        if (
            self._graph_service
            and isinstance(query, str)
            and self._needs_graph(query)
        ):
            data = self._graph_service.get_resource(query)
            return {
                "tool": "graph",
                "result": data,
                "citations": [
                    {"type": "graph", "query": query, "count": len(data)}
                ],
            }
        data = self._unstructured_agent.search(query)
        citations = [
            {"type": "passage", "rank": i + 1, "excerpt": p[:200]}
            for i, p in enumerate(data[:5])
        ]
        return {"tool": "ai_search", "result": data, "citations": citations}

    @staticmethod
    def _needs_graph(query: str) -> bool:
        keywords = {"email", "calendar", "file", "meeting"}
        text = query.lower()
        return any(k in text for k in keywords)
