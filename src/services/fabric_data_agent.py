"""Client for executing SQL against Microsoft Fabric.

Supports two modes:
- HTTP (default): posts to an API facade at ``{endpoint}/sql``. This keeps
  tests simple and lets you proxy Fabric in your environment.
- ODBC (optional): if ``FABRIC_ODBC_CONNECTION_STRING`` is set and ``pyodbc``
  is available, queries are executed directly against the Fabric Warehouse SQL
  endpoint using parameter binding.
"""
from __future__ import annotations

import os
from typing import List, Any

import requests
from contextlib import contextmanager

try:  # optional
    import pyodbc  # type: ignore
except Exception:  # pragma: no cover - not required in tests/CI
    pyodbc = None  # type: ignore


class FabricDataAgent:
    """Execute SQL queries through the Fabric Data endpoint.

    Parameters
    ----------
    endpoint: str
        Base URL of the Fabric SQL endpoint.
    token: str | None
        Bearer token for authentication. If ``None`` the ``FABRIC_TOKEN``
        environment variable is used.
    """

    def __init__(self, endpoint: str, token: str | None = None, extra_headers: dict | None = None) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._token = token or os.getenv("FABRIC_TOKEN", "")
        self._odbc_cstr = os.getenv("FABRIC_ODBC_CONNECTION_STRING", "")
        self._mode = (os.getenv("FABRIC_SQL_MODE", "http").lower() or "http")
        self._extra_headers = extra_headers or {}

    def run_sql(self, sql: str) -> List[dict]:
        """Run raw SQL and return rows as a list of dicts."""
        _ensure_read_only(sql)
        if self._mode == "odbc" and self._odbc_cstr and pyodbc is not None:
            with self._conn() as conn:
                cur = conn.cursor()
                cur.execute(sql)
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        # HTTP facade fallback
        url = f"{self._endpoint}/sql"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "User-Agent": "LeftTurn/1.0",
        }
        headers.update(self._extra_headers)
        response = _post_with_retry(url, {"query": sql}, headers)
        return response.json().get("rows", [])

    def run_sql_params(self, sql: str, parameters: dict) -> List[dict]:
        """Execute a parameterized SQL query.

        Parameters should be provided as a dict; they are sent to the Fabric
        service using a standard `parameters` payload to avoid string
        interpolation. Example: `{"@carrier": "X"}` used with
        `WHERE carrier = @carrier`.
        """
        _ensure_read_only(sql)
        if self._mode == "odbc" and self._odbc_cstr and pyodbc is not None:
            with self._conn() as conn:
                cur = conn.cursor()
                # Convert dict {"@p": v} to ordered tuples in query order
                ordered: list[Any] = []
                for name in _iter_param_names(sql):
                    if name in parameters:
                        ordered.append(parameters[name])
                cur.execute(_strip_param_names(sql), ordered)
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        # HTTP facade fallback
        url = f"{self._endpoint}/sql"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "User-Agent": "LeftTurn/1.0",
        }
        headers.update(self._extra_headers)
        payload = {"query": sql, "parameters": [{"name": k, "value": v} for k, v in parameters.items()]}
        response = _post_with_retry(url, payload, headers)
        return response.json().get("rows", [])

    @contextmanager
    def _conn(self):  # pragma: no cover - optional path
        if not self._odbc_cstr or pyodbc is None:
            raise RuntimeError("ODBC mode is not available")
        conn = pyodbc.connect(self._odbc_cstr, autocommit=True)
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass


def _iter_param_names(sql: str) -> List[str]:  # pragma: no cover - parsing helper
    import re
    return re.findall(r"@\w+", sql)


def _strip_param_names(sql: str) -> str:  # pragma: no cover
    # Replace @param with ? for ODBC parameter binding
    import re
    return re.sub(r"@\w+", "?", sql)


def _post_with_retry(url: str, payload: dict, headers: dict, timeout: int = 10):
    """POST with small retry on transient errors (429/5xx/connection).

    Keeps behavior simple and bounded for stability.
    """
    import random
    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            # Retry on throttling or server errors
            if resp.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                delay = 0.2 * (2 ** attempt) + random.random() * 0.05
                try:
                    import time as _t
                    _t.sleep(delay)
                except Exception:
                    pass
                continue
            resp.raise_for_status()
            return resp
        except Exception:
            if attempt == 2:
                raise
            try:
                import time as _t
                _t.sleep(0.2 * (2 ** attempt))
            except Exception:
                pass
    # Should not reach
    return requests.post(url, json=payload, headers=headers, timeout=timeout)


def _ensure_read_only(sql: str) -> None:
    """Guardrail: allow only SELECT/CTE queries in production paths.

    This prevents accidental writes when running against production Fabric.
    """
    import re
    s = sql.lstrip()
    # strip leading comments
    while True:
        s = s.lstrip()
        if s.startswith("/*"):
            end = s.find("*/")
            s = s[end + 2:] if end != -1 else ""
            continue
        if s.startswith("--"):
            nl = s.find("\n")
            s = s[nl + 1:] if nl != -1 else ""
            continue
        break
    m = re.match(r"([a-zA-Z]+)", s or "")
    kw = (m.group(1).lower() if m else "")
    if kw not in {"select", "with"}:
        raise PermissionError("Only read-only SELECT queries are permitted")
