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
    ClaimsAgent,
)
from src.services.fabric_data_agent import FabricDataAgent
from src.services.search_service import SearchService
from src.services.graph_service import GraphService
from src.utils.helpers import get_correlation_id, log_function_execution
from src.services.obo import exchange_obo_for_graph
from src.utils.pbi import build_pbi_deeplink
from src.utils.cards import build_answer_card

logger = logging.getLogger(__name__)

agent_gateway_bp = func.Blueprint()


def _build_orchestrator(user_graph_token: str | None = None) -> OrchestratorAgent:
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
    # Prefer a per-request delegated token from EasyAuth when available
    # Optionally perform OBO to get a Graph token for the user
    graph_token = user_graph_token or os.getenv("GRAPH_TOKEN", "").strip()
    try:
        obo_pref = os.getenv("OBO_ENABLED", "false").lower() in {"1", "true", "yes"}
        if obo_pref and user_graph_token:
            obo_token = exchange_obo_for_graph(user_graph_token)
            if obo_token:
                graph_token = obo_token
    except Exception:
        pass
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
    if name in ("claim", "claims", "dispute"):
        return ClaimsAgent(orchestrator)
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
        fmt = (body or {}).get("format") or req.params.get("format")
        if not query or not isinstance(query, str):
            return func.HttpResponse(
                json.dumps({"error": "'query' is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"},
            )

        payload, agent_name = handle_agent_query(
            query,
            req.route_params.get("agent", "domain"),
            fmt,
            dict(req.headers) if hasattr(req, "headers") else {},
            dict(req.params) if hasattr(req, "params") else {},
        )

        finished = datetime.now()
        log_function_execution(
            "agent_ask",
            started,
            finished,
            True,
            {"agent": agent_name, "correlation_id": cid},
        )

        # If Teams requests a card, return an Adaptive Card payload
        if fmt and fmt.lower() == "card":
            card = build_answer_card(payload)
            return func.HttpResponse(
                json.dumps(card),
                status_code=200,
                headers={"Content-Type": "application/json"},
            )

        return func.HttpResponse(
            json.dumps({"agent": agent_name, **payload}),
            status_code=200,
            headers={"Content-Type": "application/json"},
        )
    except Exception as e:
        finished = datetime.now()
        log_function_execution(
            "agent_ask", started, finished, False, {"correlation_id": cid}
        )
        logger.error(f"[{cid}] agent_ask error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "message": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"},
        )


def _extract_value(text: str, key: str) -> str | None:
    try:
        import re
        # Match key: value where value can be quoted or unquoted token(s)
        # Examples: carrier: Acme, service level="2 Day", sku 812
        pattern = rf"{key}[:=\s]+(?:(['\"])(.*?)\1|([\w\-.]+))"
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            return None
        return (m.group(2) or m.group(3))
    except Exception:
        # Avoid raising from helper; simply return None on parse failure
        return None


def handle_agent_query(
    query: str,
    agent: str = "domain",
    fmt: str | None = None,
    headers: dict | None = None,
    params: dict | None = None,
) -> tuple[dict, str]:
    """Core handler for agent queries used by HTTP function and tests.

    Returns (payload, agent_name).
    """
    headers = headers or {}
    params = params or {}

    # Surface user Graph token from EasyAuth (if enabled)
    graph_token = headers.get("x-ms-token-aad-access-token")
    orchestrator = _build_orchestrator(graph_token)
    agent_obj = _resolve_chat_agent(agent, orchestrator)
    agent_name = agent_obj.__class__.__name__

    # Prefer enriched result with evidence when available
    result_payload = orchestrator.handle_with_citations(query)

    # If structured SQL was used, try to provide a Power BI link
    if result_payload.get("tool") == "fabric_sql":
        # naive filter inference from query keywords
        ql = query.lower()
        filters = {}
        if "carrier" in ql:
            filters["vw_Variance/Carrier"] = _extract_value(query, "carrier") or ""
        if "sku" in ql:
            filters["vw_Variance/SKU"] = _extract_value(query, "sku") or ""
        if "service level" in ql or "service" in ql:
            val = _extract_value(query, "service level") or _extract_value(query, "service")
            if val:
                filters["vw_Variance/ServiceLevel"] = val
        # Include date range expressions from SQL parameters when available
        exprs = []
        try:
            import os as _os
            date_col = _os.getenv("PBI_DATE_COLUMN", "vw_Variance/ShipDate")
            params_dict = (result_payload.get("citations") or [{}])[0].get("parameters") or {}
            dfrom = params_dict.get("@from")
            dto = params_dict.get("@to")
            if dfrom and dto:
                exprs.append(f"{date_col} ge '{dfrom}'")
                exprs.append(f"{date_col} le '{dto}'")
        except Exception:
            pass
        pbi = build_pbi_deeplink({k: v for k, v in filters.items() if v}, expressions=exprs or None)
        if pbi:
            result_payload["powerBiLink"] = pbi

    return result_payload, agent_name
