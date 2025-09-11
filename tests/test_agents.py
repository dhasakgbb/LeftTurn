from src.agents import (
    CarrierAgent,
    DomainAgent,
    CustomerOpsAgent,
    ClaimsAgent,
    OrchestratorAgent,
    StructuredDataAgent,
    UnstructuredDataAgent,
)
import responses
import pytest

from src.services.fabric_data_agent import FabricDataAgent
from src.services.search_service import SearchService
from src.services.graph_service import GraphService
from src.services.sql_templates import TEMPLATES


def test_orchestrator_routes_structured_queries() -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            "https://fabric.test/sql",
            json={"rows": [{"carrier": "X", "overbilled": True}]},
        )
        fabric = FabricDataAgent("https://fabric.test", token="T")
        structured = StructuredDataAgent(fabric)
        unstructured = UnstructuredDataAgent(
            SearchService("https://search.test", "contracts", api_key="K")
        )
        orchestrator = OrchestratorAgent(structured, unstructured)

        params = {"@from": "2024-01-01", "@to": "2024-01-31"}
        result = orchestrator.handle(("variance_summary", params))

        assert result == [{"carrier": "X", "overbilled": True}]


def test_orchestrator_routes_unstructured_queries() -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            (
                "https://search.test/indexes/contracts/docs/search"
                "?api-version=2021-04-30-Preview"
            ),
            json={
                "value": [{"content": "Clause 7.4: minimum charge applies."}]
            },
        )
        structured = StructuredDataAgent(
            FabricDataAgent("https://fabric.test", token="T")
        )
        unstructured = UnstructuredDataAgent(
            SearchService("https://search.test", "contracts", api_key="K")
        )
        orchestrator = OrchestratorAgent(structured, unstructured)

        result = orchestrator.handle("what does clause 7.4 say?")

        assert result == ["Clause 7.4: minimum charge applies."]


def test_orchestrator_routes_graph_queries() -> None:
    with responses.RequestsMock() as rsps:
        payload = {
            "value": [
                {
                    "hitsContainers": [
                        {
                            "hits": [
                                {"_source": {"subject": "mail about invoice"}}
                            ]
                        }
                    ]
                }
            ]
        }
        rsps.add(
            "POST",
            "https://graph.test/search/query",
            json=payload,
        )
        graph = GraphService(token="T", endpoint="https://graph.test")
        structured = StructuredDataAgent(
            FabricDataAgent("https://fabric.test", token="T")
        )
        unstructured = UnstructuredDataAgent(
            SearchService("https://search.test", "contracts", api_key="K")
        )
        orchestrator = OrchestratorAgent(structured, unstructured, graph)

        result = orchestrator.handle("show recent email")

        assert result == ["mail about invoice"]


@pytest.mark.parametrize(
    "agent_cls",
    [DomainAgent, CarrierAgent, CustomerOpsAgent, ClaimsAgent],
)
def test_agents_delegate_and_expose_prompt(agent_cls) -> None:
    class DummyOrchestrator:
        def __init__(self) -> None:
            self.received = None

        def handle(self, query):
            self.received = query
            return "ok"

    orch = DummyOrchestrator()
    agent = agent_cls(orch)

    assert agent.handle("ping") == "ok"
    assert orch.received == "ping"
    assert isinstance(agent.default_prompt, str) and agent.default_prompt


def test_orchestrator_citations_structured() -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            "https://fabric.test/sql",
            json={"rows": [
                {"carrier": "X", "overbilled": True},
                {"carrier": "Y", "overbilled": False},
            ]},
        )
        structured = StructuredDataAgent(
            FabricDataAgent("https://fabric.test", token="T")
        )
        unstructured = UnstructuredDataAgent(
            SearchService("https://search.test", "contracts", api_key="K")
        )
        orch = OrchestratorAgent(structured, unstructured)

        params = {"@from": "2024-01-01", "@to": "2024-01-31"}
        payload = orch.handle_with_citations(("variance_summary", params))

        assert payload["tool"] == "fabric_sql"
        assert isinstance(payload.get("citations"), list)
        assert payload["citations"][0]["template"] == "variance_summary"
        # sampleRows should include up to first 3 rows
        assert isinstance(payload.get("sampleRows"), list) and len(payload["sampleRows"]) >= 1


def test_orchestrator_citations_views_extracted() -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            "https://fabric.test/sql",
            json={"rows": []},
        )
        structured = StructuredDataAgent(
            FabricDataAgent("https://fabric.test", token="T")
        )
        unstructured = UnstructuredDataAgent(
            SearchService("https://search.test", "contracts", api_key="K")
        )
        orch = OrchestratorAgent(structured, unstructured)

        params = {"@from": "2024-01-01", "@to": "2024-01-31", "@carrier": "X"}
        payload = orch.handle_with_citations(("variance_by_service", params))

        c0 = payload["citations"][0]
        assert "views" in c0 and any("vw_" in v for v in c0["views"]) 


def test_orchestrator_citations_unstructured() -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            (
                "https://search.test/indexes/contracts/docs/search"
                "?api-version=2021-04-30-Preview"
            ),
            json={"value": [{"content": "C7.4 minimum charge applies."}]},
        )
        structured = StructuredDataAgent(
            FabricDataAgent("https://fabric.test", token="T")
        )
        unstructured = UnstructuredDataAgent(
            SearchService("https://search.test", "contracts", api_key="K")
        )
        orch = OrchestratorAgent(structured, unstructured)

        payload = orch.handle_with_citations("what does clause 7.4 say?")

        assert payload["tool"] == "ai_search"
        assert len(payload["citations"]) >= 1
        assert "excerpt" in payload["citations"][0]


def test_orchestrator_citations_unstructured_with_metadata() -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            (
                "https://search.test/indexes/contracts/docs/search"
                "?api-version=2021-04-30-Preview"
            ),
            json={
                "value": [
                    {
                        "file": "carrierX.pdf",
                        "page": 7,
                        "clauseId": "C7.4",
                        "content": "Clause 7.4: minimum charge applies.",
                    }
                ]
            },
        )
        structured = StructuredDataAgent(
            FabricDataAgent("https://fabric.test", token="T")
        )
        # Search service returns fields; orchestrator should surface them in citations
        unstructured = UnstructuredDataAgent(
            SearchService("https://search.test", "contracts", api_key="K")
        )
        orch = OrchestratorAgent(structured, unstructured)

        payload = orch.handle_with_citations("what does clause 7.4 say?")

        c0 = payload["citations"][0]
        assert c0.get("file") == "carrierX.pdf"
        assert c0.get("page") == 7
        assert c0.get("clauseId") == "C7.4"


def test_structured_agent_rejects_unknown_template() -> None:
    agent = StructuredDataAgent(
        FabricDataAgent("https://fabric.test", token="T")
    )
    with pytest.raises(ValueError):
        agent.query("missing", {})


def test_fabric_run_sql_params_sends_parameters() -> None:
    with responses.RequestsMock() as rsps:
        def _cb(request):
            body = request.body
            import json as _json
            data = _json.loads(body)
            assert "parameters" in data
            assert {"name": "@carrier", "value": "X"} in data["parameters"]
            return (200, {}, _json.dumps({"rows": []}))

        rsps.add_callback(
            "POST",
            "https://fabric.test/sql",
            callback=_cb,
            content_type="application/json",
        )
        agent = FabricDataAgent("https://fabric.test", token="T")
        agent.run_sql_params(
            "SELECT 1 WHERE carrier = @carrier", {"@carrier": "X"}
        )


def test_sql_templates_registered() -> None:
    # Ensure expected templates are present
    for key in [
        "variance_summary",
        "variance_by_service",
        "on_time_rate",
        "fuel_surcharge_series",
    ]:
        assert key in TEMPLATES and isinstance(TEMPLATES[key], str)


def test_structured_agent_runs_all_templates() -> None:
    import re

    with responses.RequestsMock() as rsps:
        def _cb(request):
            body = request.body
            import json as _json
            data = _json.loads(body)
            sent_params = {p["name"] for p in data.get("parameters", [])}
            sql = data.get("query", "")
            expected = set(re.findall(r"@[A-Za-z_]+", sql))
            # Only require that params referenced in SQL are provided
            assert expected.issubset(sent_params)
            return (200, {}, _json.dumps({"rows": []}))

        rsps.add_callback(
            "POST",
            "https://fabric.test/sql",
            callback=_cb,
            content_type="application/json",
        )

        fabric = FabricDataAgent("https://fabric.test", token="T")
        structured = StructuredDataAgent(fabric)

        params = {"@from": "2024-01-01", "@to": "2024-01-31", "@carrier": "X"}
        for name in [
            "variance_summary",
            "variance_by_service",
            "on_time_rate",
            "fuel_surcharge_series",
        ]:
            structured.query(name, params)
