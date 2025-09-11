import azure.functions as func
import json
import logging
from datetime import datetime

from src.functions.agent_gateway import _build_orchestrator, _resolve_chat_agent
from src.utils.helpers import get_correlation_id, log_function_execution
from src.utils.cards import build_answer_card

logger = logging.getLogger(__name__)

teams_relay_bp = func.Blueprint()


@teams_relay_bp.function_name(name="teams_ask")
@teams_relay_bp.route(route="teams/ask", methods=["POST"])
async def teams_ask(req: func.HttpRequest) -> func.HttpResponse:
    """Teams relay endpoint that returns an Adaptive Card.

    Body: { "query": "...", "agent": "carrier|claims|customer|domain" }
    """
    started = datetime.now()
    cid = get_correlation_id(req)
    try:
        body = req.get_json()
    except Exception:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON"}),
            status_code=400,
            headers={"Content-Type": "application/json"},
        )

    query = (body or {}).get("query")
    agent_name = (body or {}).get("agent", "domain")
    if not query:
        return func.HttpResponse(
            json.dumps({"error": "'query' is required"}),
            status_code=400,
            headers={"Content-Type": "application/json"},
        )

    orch = _build_orchestrator()
    agent = _resolve_chat_agent(agent_name, orch)
    result_payload = orch.handle_with_citations(query)

    card = build_answer_card(result_payload)

    finished = datetime.now()
    log_function_execution(
        "teams_ask",
        started,
        finished,
        True,
        {"agent": agent.__class__.__name__, "correlation_id": cid},
    )
    return func.HttpResponse(
        json.dumps(card),
        status_code=200,
        headers={"Content-Type": "application/json"},
    )

