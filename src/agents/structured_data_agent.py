"""Agent that handles queries against structured data sources."""
from __future__ import annotations
from typing import Any


class StructuredDataAgent:
    def __init__(self, fabric_agent: Any) -> None:
        self._fabric_agent = fabric_agent

    def query(self, sql: str) -> Any:
        """Execute a SQL statement via the Fabric data agent."""
        return self._fabric_agent.run_sql(sql)
