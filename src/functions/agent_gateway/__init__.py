import azure.functions as func
import json
import os
import logging
from datetime import datetime

from src.agents import (
    OrchestratorAgent,
    StructuredDataAgent,
    UnstructuredDataAgent,
    DomainAgent,
    CarrierAgent,
    CustomerOpsAgent,
)
from src.services.fabric_data_agent import FabricDataAgent
from src.services.search_service import SearchService
from src.services.graph_service import GraphService
from src.utils.helpers import get_correlation_id, log_function_execution

logger = logging.getLogger(__name__)

agent_gateway_bp = func.Blueprint()


def _build_orchestrator() -> OrchestratorAgent:
    """Create an orchestrator wired to Fabric, Search, and Graph services.

    Configuration is taken from environment variables so this function stays
    testable and production-ready without code changes across environments.
    """
    # Structured: Fabric
    fabric_endpoint = os.getenv("FABRIC_ENDPOINT", "").strip()
    fabric_token = os.getenv("FABRIC_TOKEN", "").strip()
    fabric = FabricDataAgent(fabric_endpoint, token=fabric_token) if fabric_endpoint else None

    # Unstructured: Azure AI Search
    search_endpoint = os.getenv("SEARCH_ENDPOINT", "").strip()
    search_index = os.getenv("SEARCH_INDEX", "").strip()
    search_key = os.getenv("SEARCH_API_KEY", "").strip()
    search = (
        SearchService(search_endpoint, search_index, api_key=search_key)
        if search_endpoint and search_index
        else None
    )

    # Microsoft Graph
    graph_token = os.getenv("GRAPH_TOKEN", "").strip()
    graph_endpoint = os.getenv("GRAPH_ENDPOINT", "https://graph.microsoft.com/v1.0")
    graph = GraphService(token=graph_token, endpoint=graph_endpoint) if graph_token else None

    structured = StructuredDataAgent(fabric) if fabric else None
    unstructured = UnstructuredDataAgent(search) if search else None

    if not structured and not unstructured:
        raise RuntimeError("No data services configured: set FABRIC_*/SEARCH_* env vars")

    # Fallbacks: If either side is missing, provide a shallow stub that raises clear error
    class _Missing:
        def __init__(self, name: str):
            self._name = name

        def query(self, *_args, **_kwargs):  # for StructuredDataAgent
            raise RuntimeError(f"{self._name} is not configured")

        def search(self, *_args, **_kwargs):  # for UnstructuredDataAgent
            raise RuntimeError(f"{self._name} is not configured")

    structured = structured or StructuredDataAgent(_Missing("Fabric Data Agent"))
    unstructured = unstructured or UnstructuredDataAgent(_Missing("Search Service"))

    return OrchestratorAgent(structured, unstructured, graph)


def _resolve_chat_agent(name: str, orchestrator: OrchestratorAgent):
    name = (name or "domain").lower()
    if name in ("carrier", "carriers"):
        return CarrierAgent(orchestrator)
    if name in ("customer", "custops", "ops"):
        return CustomerOpsAgent(orchestrator)
    return DomainAgent(orchestrator)


@agent_gateway_bp.function_name(name="agent_ask")
@agent_gateway_bp.route(route="agents/{agent}/ask", methods=["POST"])
async def agent_ask(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP gateway for LeftTurn chat agents.

    Body: {"query": "text"}
    Path: /api/agents/{agent}/ask where agent is one of: domain|carrier|customer
    """
    started = datetime.now()
    cid = get_correlation_id(req)
    try:
        try:
            body = req.get_json()
        except Exception:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON in request body"}),
                status_code=400,
                headers={"Content-Type": "application/json"},
            )
        query = (body or {}).get("query")
        if not query or not isinstance(query, str):
            return func.HttpResponse(
                json.dumps({"error": "'query' is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"},
            )

        orchestrator = _build_orchestrator()
        agent = _resolve_chat_agent(req.route_params.get("agent", "domain"), orchestrator)

        logger.info(f"[{cid}] Agent ask to {agent.__class__.__name__}")
        # Prefer enriched result with evidence when available
        result_payload = orchestrator.handle_with_citations(query)

        finished = datetime.now()
        log_function_execution(
            "agent_ask",
            started,
            finished,
            True,
            {"agent": agent.__class__.__name__, "correlation_id": cid},
        )

        return func.HttpResponse(
            json.dumps({"agent": agent.__class__.__name__, **result_payload}),
            status_code=200,
            headers={"Content-Type": "application/json"},
        )
    except Exception as e:
        finished = datetime.now()
        log_function_execution("agent_ask", started, finished, False, {"correlation_id": cid})
        logger.error(f"[{cid}] agent_ask error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "message": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"},
        )
