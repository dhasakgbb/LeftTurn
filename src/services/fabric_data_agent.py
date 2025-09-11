"""HTTP client for executing SQL against a Microsoft Fabric endpoint."""
from __future__ import annotations

import os
from typing import List

import requests


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

    def __init__(self, endpoint: str, token: str | None = None) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._token = token or os.getenv("FABRIC_TOKEN", "")

    def run_sql(self, sql: str) -> List[dict]:
        """Run *sql* against the Fabric endpoint and return rows."""
        url = f"{self._endpoint}/sql"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            url,
            json={"query": sql},
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("rows", [])
