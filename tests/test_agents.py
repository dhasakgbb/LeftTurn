from src.agents import (
    CarrierAgent,
    DomainAgent,
    CustomerOpsAgent,
    OrchestratorAgent,
    StructuredDataAgent,
    UnstructuredDataAgent,
)
import responses

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

        result = orchestrator.handle("invoice variance for carrier X")

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

        assert agent.handle("rate table") == [{"carrier": "Y"}]


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

        assert carrier.handle("sql rate") == [{"carrier": "Z"}]
        assert customer.handle("sql rate") == [{"carrier": "Z"}]
