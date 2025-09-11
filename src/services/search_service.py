"""Client for Azure Cognitive Search used by the unstructured data agent."""
from __future__ import annotations

import os
from typing import List, Any

import requests


class SearchService:
    """Query an Azure Cognitive Search index."""

    def __init__(
        self, endpoint: str, index: str, api_key: str | None = None, api_version: str | None = None
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._index = index
        self._api_key = api_key or os.getenv("SEARCH_API_KEY", "")
        self._api_version = api_version or os.getenv("SEARCH_API_VERSION", "2021-04-30-Preview")
        self._hybrid = os.getenv("SEARCH_HYBRID", "false").lower() in {"1", "true", "yes"}
        self._vector_field = os.getenv("SEARCH_VECTOR_FIELD", "pageEmbedding")

    def search(
        self, query: str, top: int = 5, semantic: bool = False, return_fields: bool = False
    ) -> List[Any]:
        url = (
            f"{self._endpoint}/indexes/{self._index}/docs/search?api-version={self._api_version}"
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
        # Hybrid vector + keyword (if configured and embedding available)
        if self._hybrid:
            embedding = self._embed(query)
            if embedding:
                body["vector"] = {"value": embedding, "fields": self._vector_field, "k": top}

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

    def _embed(self, text: str) -> List[float] | None:  # pragma: no cover - network
        """Optionally get an embedding vector via Azure OpenAI if configured."""
        try:
            import requests as _rq
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            key = os.getenv("AZURE_OPENAI_API_KEY")
            dep = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")
            if not (endpoint and key and dep):
                return None
            url = f"{endpoint}/openai/deployments/{dep}/embeddings?api-version=2023-05-15"
            headers = {"api-key": key, "Content-Type": "application/json"}
            payload = {"input": text}
            r = _rq.post(url, headers=headers, json=payload, timeout=10)
            r.raise_for_status()
            data = r.json()
            return data["data"][0]["embedding"]
        except Exception:
            return None
