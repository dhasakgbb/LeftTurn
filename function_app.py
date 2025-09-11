import azure.functions as func
import logging
from src.functions.excel_processor import excel_processor_bp
from src.functions.data_validator import data_validator_bp
from src.functions.email_sender import email_sender_bp
from src.functions.change_tracker import change_tracker_bp
from src.functions.agent_gateway import agent_gateway_bp
from src.utils.helpers import validate_stack_readiness
from src.functions.teams_relay import teams_relay_bp

# Initialize the Function App
app = func.FunctionApp()

# Register blueprints
app.register_functions(excel_processor_bp)
app.register_functions(data_validator_bp)
app.register_functions(email_sender_bp)
app.register_functions(change_tracker_bp)
app.register_functions(agent_gateway_bp)
app.register_functions(teams_relay_bp)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.function_name(name="health")
@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint"""
    logger.info("Health check requested")
    detailed = False
    try:
        # type: ignore[attr-defined]
        detailed = (req.params.get("detail") or "").lower() in {"1", "true", "yes"}
    except Exception:
        pass
    payload = {"status": "healthy", "service": "LeftTurn Agents"}
    if detailed:
        payload["config"] = validate_stack_readiness()
    import json as _json
    return func.HttpResponse(
        body=_json.dumps(payload),
        status_code=200,
        headers={"Content-Type": "application/json"}
    )
