"""Agent that handles queries against structured data sources."""
from __future__ import annotations
from typing import Any

from src.services.sql_templates import TEMPLATES


class StructuredDataAgent:
    def __init__(
        self, fabric_agent: Any, templates: dict[str, str] | None = None
    ) -> None:
        self._fabric_agent = fabric_agent
        self._templates = templates or TEMPLATES

    def query(
        self, template: str, parameters: dict[str, Any] | None = None
    ) -> Any:
        """Execute a parameterized SQL statement using an approved template."""
        sql = self._templates.get(template)
        if sql is None:
            raise ValueError(f"Unknown SQL template: {template}")
        return self._fabric_agent.run_sql_params(sql, parameters or {})
