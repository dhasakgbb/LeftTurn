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
        _ensure_view_only(sql)
        return self._fabric_agent.run_sql_params(sql, parameters or {})


def _ensure_view_only(sql: str) -> None:
    """Block direct table access; allow curated views.

    Anti-goal is bypassing curated views. We block obvious table/schema
    references (dbo., sys., information_schema) but allow view names such as
    vw_* regardless of schema qualification choice in environments.
    """
    import re
    names: list[str] = []
    for m in re.finditer(r"\bFROM\s+([\w\.]+)", sql, re.IGNORECASE):
        names.append(m.group(1))
    for m in re.finditer(r"\bJOIN\s+([\w\.]+)", sql, re.IGNORECASE):
        names.append(m.group(1))
    for n in names:
        nl = n.lower()
        if nl.startswith("vw_") or ".vw_" in nl:
            continue
        if nl.startswith("dbo.") or nl.startswith("sys.") or nl.startswith("information_schema."):
            raise PermissionError("Queries must reference curated views; direct tables are blocked")
