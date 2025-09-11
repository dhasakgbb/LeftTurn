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
        extra_headers: dict | None = None,
    ) -> None:
        self._token = token or os.getenv("GRAPH_TOKEN", "")
        self._endpoint = endpoint.rstrip("/")
        self._extra_headers = extra_headers or {}

    def get_resource(self, query: str) -> List[str]:
        """Search messages, events, and files matching *query*."""
        try:
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
                "User-Agent": "LeftTurn/1.0",
            }
            headers.update(self._extra_headers)
            response = _post_with_retry(url, payload, headers)
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
        except Exception:
            return []


def _post_with_retry(url: str, payload: dict, headers: dict, timeout: int = 10):
    import random
    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
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
    return requests.post(url, json=payload, headers=headers, timeout=timeout)
