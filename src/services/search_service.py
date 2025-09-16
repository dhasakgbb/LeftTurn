"""Client for Azure Cognitive Search used by the unstructured data agent."""
from __future__ import annotations

import os
from typing import List, Any

try:  # pragma: no cover
    import requests
except ModuleNotFoundError:  # pragma: no cover
    from src.utils.requests_stub import requests
from src.utils.constants import USER_AGENT


class SearchService:
    """Query an Azure Cognitive Search index."""

    def __init__(
        self,
        endpoint: str,
        index: str,
        api_key: str | None = None,
        api_version: str | None = None,
        extra_headers: dict | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._index = index
        self._api_key = api_key or os.getenv("SEARCH_API_KEY", "")
        self._api_version = api_version or os.getenv("SEARCH_API_VERSION", "2021-04-30-Preview")
        self._hybrid = os.getenv("SEARCH_HYBRID", "false").lower() in {"1", "true", "yes"}
        self._vector_field = os.getenv("SEARCH_VECTOR_FIELD", "pageEmbedding")
        self._extra_headers = extra_headers or {}

    def search(
        self, query: str, top: int = 5, semantic: bool = False, return_fields: bool = False
    ) -> List[Any]:
        url = (
            f"{self._endpoint}/indexes/{self._index}/docs/search?api-version={self._api_version}"
        )
        headers = {
            "api-key": self._api_key,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        headers.update(self._extra_headers)
        try:
            timeout = int(os.getenv("SEARCH_TIMEOUT", "10"))
        except Exception:
            timeout = 10
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
                body["vector"] = {
                    "value": embedding,
                    "fields": self._vector_field,
                    "k": top,
                }

        response = _post_with_retry(url, body, headers, timeout=timeout)
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
            headers = {"api-key": key, "Content-Type": "application/json", "User-Agent": USER_AGENT}
            payload = {"input": text}
            r = _rq.post(url, headers=headers, json=payload, timeout=10)
            r.raise_for_status()
            data = r.json()
            return data["data"][0]["embedding"]
        except Exception:
            return None


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
