from __future__ import annotations

from typing import Literal, TypedDict


class ToolCall(TypedDict):
    tool: Literal["sql", "rag", "graph"]
    name: str
    params: dict


def classify(query: str) -> ToolCall:
    q = query.lower()
    if any(
        k in q for k in ("variance", "overbill", "sum ", "count ", "rate ", "how much", "total")
    ):
        return {"tool": "sql", "name": "variance_summary", "params": {}}
    if any(
        k in q for k in ("email from", "calendar on", "file named", "in sharepoint", "from user ")
    ):
        return {"tool": "graph", "name": "lookup", "params": {}}
    return {"tool": "rag", "name": "contract_lookup", "params": {}}
