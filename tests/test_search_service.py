import responses
from src.services.search_service import SearchService


def test_search_service_uses_api_version_env(monkeypatch):
    monkeypatch.setenv("SEARCH_API_VERSION", "2023-07-01-Preview")
    with responses.RequestsMock() as rsps:
        def _cb(request):
            assert request.url.endswith("api-version=2023-07-01-Preview")
            return (200, {}, '{"value": [{"content": "x"}]}')

        rsps.add_callback(
            "POST",
            "https://search.test/indexes/contracts/docs/search",
            callback=_cb,
            content_type="application/json",
        )
        svc = SearchService("https://search.test", "contracts", api_key="K")
        out = svc.search("q")
        assert out == ["x"]


def test_search_service_semantic_flag(monkeypatch):
    with responses.RequestsMock() as rsps:
        def _cb(request):
            import json as _json
            body = _json.loads(request.body)
            assert body.get("queryType") == "semantic"
            assert body.get("semanticConfiguration") == "default"
            return (200, {}, '{"value": [{"content": "y"}]}')

        rsps.add_callback(
            "POST",
            "https://search.test/indexes/contracts/docs/search",
            callback=_cb,
            content_type="application/json",
        )
        svc = SearchService("https://search.test", "contracts", api_key="K")
        out = svc.search("q", semantic=True)
        assert out == ["y"]


def test_search_service_hybrid_vector(monkeypatch):
    monkeypatch.setenv("SEARCH_HYBRID", "true")
    monkeypatch.setenv("SEARCH_VECTOR_FIELD", "pageEmbedding")
    monkeypatch.setenv("SEARCH_API_VERSION", "2023-11-01-Preview")
    with responses.RequestsMock() as rsps:
        def _cb(request):
            import json as _json
            body = _json.loads(request.body)
            assert "vector" in body
            assert body["vector"]["fields"] == "pageEmbedding"
            assert isinstance(body["vector"]["value"], list)
            return (200, {}, '{"value": [{"content": "z"}]}')

        rsps.add_callback(
            "POST",
            "https://search.test/indexes/contracts/docs/search",
            callback=_cb,
            content_type="application/json",
        )
        svc = SearchService("https://search.test", "contracts", api_key="K")
        # Monkeypatch embed to avoid network
        svc._embed = lambda _q: [0.1, 0.2, 0.3]  # type: ignore[attr-defined]
        out = svc.search("q", semantic=True)
        assert out == ["z"]
