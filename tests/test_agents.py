from src.agents import (
    CarrierAgent,
    DomainAgent,
    CustomerOpsAgent,
    OrchestratorAgent,
    StructuredDataAgent,
    UnstructuredDataAgent,
)
import responses
import pytest

from src.services.fabric_data_agent import FabricDataAgent
from src.services.search_service import SearchService
from src.services.graph_service import GraphService


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


def test_domain_agent_delegates_to_orchestrator() -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            "https://fabric.test/sql",
            json={"rows": [{"carrier": "Y"}]},
        )
        structured = StructuredDataAgent(
            FabricDataAgent("https://fabric.test", token="T")
        )
        unstructured = UnstructuredDataAgent(
            SearchService("https://search.test", "contracts", api_key="K")
        )
        orchestrator = OrchestratorAgent(structured, unstructured)
        agent = DomainAgent(orchestrator)



def test_carrier_and_customer_agents_delegate() -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            "https://fabric.test/sql",
            json={"rows": [{"carrier": "Z"}]},
        )
        structured = StructuredDataAgent(
            FabricDataAgent("https://fabric.test", token="T")
        )
        unstructured = UnstructuredDataAgent(
            SearchService("https://search.test", "contracts", api_key="K")
        )
        orchestrator = OrchestratorAgent(structured, unstructured)
        carrier = CarrierAgent(orchestrator)
        customer = CustomerOpsAgent(orchestrator)



def test_orchestrator_citations_structured() -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            "https://fabric.test/sql",
            json={"rows": [{"carrier": "X", "overbilled": True}]},
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
