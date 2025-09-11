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
