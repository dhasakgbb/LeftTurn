import responses

from src.services.fabric_data_agent import FabricDataAgent
from src.services.search_service import SearchService
from src.services.graph_service import GraphService


def test_fabric_retries_then_succeeds():
    calls = {"n": 0}
    with responses.RequestsMock() as rsps:
        def _cb(request):
            calls["n"] += 1
            if calls["n"] == 1:
                return (500, {}, "server error")
            return (200, {}, '{"rows": [{"k": 1}]}')

        rsps.add_callback(
            "POST",
            "https://fabric.test/sql",
            callback=_cb,
            content_type="application/json",
        )
        agent = FabricDataAgent("https://fabric.test", token="T")
        out = agent.run_sql_params("SELECT 1 WHERE x=@x", {"@x": 1})
        assert out == [{"k": 1}]


def test_search_retries_then_succeeds():
    calls = {"n": 0}
    with responses.RequestsMock() as rsps:
        def _cb(request):
            calls["n"] += 1
            if calls["n"] == 1:
                return (503, {}, "unavailable")
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


def test_graph_retries_then_succeeds():
    calls = {"n": 0}
    with responses.RequestsMock() as rsps:
        def _cb(request):
            calls["n"] += 1
            if calls["n"] == 1:
                return (502, {}, "bad gateway")
            return (200, {}, '{"value": []}')

        rsps.add_callback(
            "POST",
            "https://graph.test/search/query",
            callback=_cb,
            content_type="application/json",
        )
        graph = GraphService(token="T", endpoint="https://graph.test")
        out = graph.get_resource("q")
        assert out == []

