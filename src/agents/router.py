from __future__ import annotations

from typing import Literal, TypedDict


class ToolCall(TypedDict):
    tool: Literal["sql", "rag", "graph"]
    name: str
    params: dict


def classify(query: str) -> ToolCall:
    q = query.lower()
    if any(k in q for k in ("variance", "overbill", "how much", "total", "rate ")):
        if "service" in q or "by service" in q:
            return {"tool": "sql", "name": "variance_by_service", "params": {}}
        if "on-time" in q or "on time" in q or "sla" in q:
            return {"tool": "sql", "name": "on_time_rate", "params": {}}
        return {"tool": "sql", "name": "variance_summary", "params": {}}
    if any(
        k in q for k in ("email from", "calendar on", "file named", "in sharepoint", "from user ")
    ):
        return {"tool": "graph", "name": "lookup", "params": {}}
    return {"tool": "rag", "name": "contract_lookup", "params": {}}
