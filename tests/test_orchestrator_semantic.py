import responses

from src.agents import OrchestratorAgent, StructuredDataAgent, UnstructuredDataAgent
from src.services.fabric_data_agent import FabricDataAgent
from src.services.search_service import SearchService


def test_orchestrator_unstructured_uses_semantic_when_configured(monkeypatch):
    monkeypatch.setenv("SEARCH_USE_SEMANTIC", "true")
    with responses.RequestsMock() as rsps:
        def _cb(request):
            import json as _json
            body = _json.loads(request.body)
            assert body.get("queryType") == "semantic"
            return (200, {}, '{"value": [{"content": "Clause text"}]}')

        rsps.add_callback(
            "POST",
            "https://search.test/indexes/contracts/docs/search",
            callback=_cb,
            content_type="application/json",
        )
        structured = StructuredDataAgent(FabricDataAgent("https://fabric.test", token="T"))
        unstructured = UnstructuredDataAgent(SearchService("https://search.test", "contracts", api_key="K"))
        orch = OrchestratorAgent(structured, unstructured)
        out = orch.handle("what does clause 7.4 say?")
        assert out == ["Clause text"]

