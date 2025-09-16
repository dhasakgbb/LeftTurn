import pytest
from src.agents import OrchestratorAgent, StructuredDataAgent, UnstructuredDataAgent
from src.services.fabric_data_agent import FabricDataAgent
from src.services.graph_service import GraphService
from src.services.search_service import SearchService

responses = pytest.importorskip("responses")


def test_graph_graceful_error_returns_empty():
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST", "https://graph.test/search/query", status=500
        )
        graph = GraphService(token="T", endpoint="https://graph.test")
        structured = StructuredDataAgent(FabricDataAgent("https://fabric.test", token="T"))
        unstructured = UnstructuredDataAgent(SearchService("https://search.test", "contracts", api_key="K"))
        orch = OrchestratorAgent(structured, unstructured, graph)
        out = orch.handle("show recent email")
        assert out == []
