"""Microsoft Graph client for accessing M365 resources."""
from __future__ import annotations

import os
from typing import List

import requests


class GraphService:
    """Minimal Microsoft Graph search client."""

    def __init__(
        self,
        token: str | None = None,
        endpoint: str = "https://graph.microsoft.com/v1.0",
    ) -> None:
        self._token = token or os.getenv("GRAPH_TOKEN", "")
        self._endpoint = endpoint.rstrip("/")

    def get_resource(self, query: str) -> List[str]:
        """Search messages, events, and files matching *query*."""
        url = f"{self._endpoint}/search/query"
        payload = {
            "requests": [
                {
                    "entityTypes": ["message", "event", "driveItem"],
                    "query": {"queryString": query},
                    "from": 0,
                    "size": 5,
                }
            ]
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        results: List[str] = []
        for req in response.json().get("value", []):
            for container in req.get("hitsContainers", []):
                for hit in container.get("hits", []):
                    source = hit.get("_source", {})
                    name = (
                        source.get("subject")
                        or source.get("name")
                        or source.get("displayName")
                    )
                    if name:
                        results.append(name)
        return results
