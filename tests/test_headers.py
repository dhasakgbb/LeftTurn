import responses

from src.services.fabric_data_agent import FabricDataAgent
from src.services.search_service import SearchService
from src.services.graph_service import GraphService


def test_fabric_headers_include_user_agent_and_correlation(monkeypatch):
    with responses.RequestsMock() as rsps:
        def _cb(request):
            assert request.headers.get("User-Agent", "").startswith("LeftTurn/")
            assert request.headers.get("X-Correlation-ID") == "CID-1"
            return (200, {}, '{"rows": []}')

        rsps.add_callback(
            "POST",
            "https://fabric.test/sql",
            callback=_cb,
            content_type="application/json",
        )
        agent = FabricDataAgent(
            "https://fabric.test", token="T", extra_headers={"X-Correlation-ID": "CID-1"}
        )
        agent.run_sql_params("SELECT 1 WHERE x=@x", {"@x": 1})


def test_search_headers_include_user_agent_and_correlation(monkeypatch):
    with responses.RequestsMock() as rsps:
        def _cb(request):
            assert request.headers.get("User-Agent", "").startswith("LeftTurn/")
            assert request.headers.get("X-Correlation-ID") == "CID-2"
            return (200, {}, '{"value": []}')

        rsps.add_callback(
            "POST",
            "https://search.test/indexes/contracts/docs/search",
            callback=_cb,
            content_type="application/json",
        )
        svc = SearchService(
            "https://search.test", "contracts", api_key="K", extra_headers={"X-Correlation-ID": "CID-2"}
        )
        svc.search("q")


def test_graph_headers_include_user_agent_and_correlation(monkeypatch):
    with responses.RequestsMock() as rsps:
        def _cb(request):
            assert request.headers.get("User-Agent", "").startswith("LeftTurn/")
            assert request.headers.get("X-Correlation-ID") == "CID-3"
            return (200, {}, '{"value": []}')

        rsps.add_callback(
            "POST",
            "https://graph.test/search/query",
            callback=_cb,
            content_type="application/json",
        )
        graph = GraphService(
            token="T", endpoint="https://graph.test", extra_headers={"X-Correlation-ID": "CID-3"}
        )
        graph.get_resource("q")

