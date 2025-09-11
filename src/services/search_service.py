"""Client for Azure Cognitive Search used by the unstructured data agent."""
from __future__ import annotations

import os
from typing import List, Any

import requests


class SearchService:
    """Query an Azure Cognitive Search index."""

    def __init__(
        self, endpoint: str, index: str, api_key: str | None = None
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._index = index
        self._api_key = api_key or os.getenv("SEARCH_API_KEY", "")

    def search(
        self, query: str, top: int = 5, semantic: bool = False, return_fields: bool = False
    ) -> List[Any]:
        url = (
            f"{self._endpoint}/indexes/{self._index}/docs/search"
            "?api-version=2021-04-30-Preview"
        )
        headers = {
            "api-key": self._api_key,
            "Content-Type": "application/json",
        }
        body = {"search": query, "top": top}
        if semantic:
            # Basic semantic settings; requires a semantic configuration on the index
            body.update({
                "queryType": "semantic",
                "queryLanguage": "en-us",
                "semanticConfiguration": "default",
            })

        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=10,
        )
        response.raise_for_status()
        docs = response.json().get("value", [])
        if return_fields:
            # include basic metadata if present
            out: List[dict] = []
            for d in docs:
                out.append(
                    {
                        "text": d.get("content") or d.get("text", ""),
                        "file": d.get("file"),
                        "page": d.get("page"),
                        "clauseId": d.get("clauseId"),
                    }
                )
            return out
        return [d.get("content") or d.get("text", "") for d in docs]
