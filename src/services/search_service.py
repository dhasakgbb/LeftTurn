"""Client for Azure Cognitive Search used by the unstructured data agent."""
from __future__ import annotations

import os
from typing import List

import requests


class SearchService:
    """Query an Azure Cognitive Search index."""

    def __init__(
        self, endpoint: str, index: str, api_key: str | None = None
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._index = index
        self._api_key = api_key or os.getenv("SEARCH_API_KEY", "")

    def search(self, query: str) -> List[str]:
        url = (
            f"{self._endpoint}/indexes/{self._index}/docs/search"
            "?api-version=2021-04-30-Preview"
        )
        headers = {
            "api-key": self._api_key,
            "Content-Type": "application/json",
        }
        response = requests.post(
            url,
            headers=headers,
            json={"search": query},
            timeout=10,
        )
        response.raise_for_status()
        docs = response.json().get("value", [])
        return [d.get("content") or d.get("text", "") for d in docs]
