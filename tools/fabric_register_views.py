#!/usr/bin/env python3
"""
Register curated Fabric SQL views from a .sql file.

Purposefully bypasses the read-only guardrails of FabricDataAgent by using
ODBC directly. Intended for admin/seeding tasks only.

Requirements
- Set FABRIC_ODBC_CONNECTION_STRING to a valid Warehouse SQL endpoint DSN.
- Install pyodbc in the active environment (pip install pyodbc).

Usage
  python tools/fabric_register_views.py fabric/sql/create_views_carrier.sql
"""
from __future__ import annotations

import os
import sys
import re


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: fabric_register_views.py <sql_file>", file=sys.stderr)
        return 2
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"SQL file not found: {path}", file=sys.stderr)
        return 2

    cstr = os.getenv("FABRIC_ODBC_CONNECTION_STRING", "").strip()
    if not cstr:
        print("FABRIC_ODBC_CONNECTION_STRING is required for ODBC execution.", file=sys.stderr)
        return 2

    try:
        import pyodbc  # type: ignore
    except Exception as e:  # pragma: no cover
        print("pyodbc is required. Install with: pip install pyodbc", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 2

    sql_text = _read_file(path)
    statements = _split_sql_statements(sql_text)
    if not statements:
        print("No SQL statements found.", file=sys.stderr)
        return 1

    print(f"Connecting via ODBC to execute {len(statements)} statements…")
    conn = pyodbc.connect(cstr, autocommit=True)
    try:
        cur = conn.cursor()
        for i, stmt in enumerate(statements, start=1):
            s = stmt.strip()
            if not s:
                continue
            print(f"[{i}/{len(statements)}] Executing: {s.splitlines()[0][:80]}…")
            cur.execute(s)
        print("✅ Views registration completed.")
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return 0


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _split_sql_statements(sql: str) -> list[str]:
    """Split SQL text into executable statements.

    Handles basic cases with semicolons and ignores line comments and blank lines.
    """
    # Remove single-line comments
    lines = []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        lines.append(line)
    text = "\n".join(lines)
    # Split on semicolons that end a statement
    parts = re.split(r";\s*(?:\r?\n|$)", text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
