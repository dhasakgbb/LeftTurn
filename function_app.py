import azure.functions as func
import logging
from src.functions.excel_processor import excel_processor_bp
from src.functions.data_validator import data_validator_bp
from src.functions.email_sender import email_sender_bp
from src.functions.change_tracker import change_tracker_bp

# Initialize the Function App
app = func.FunctionApp()

# Register blueprints
app.register_functions(excel_processor_bp)
app.register_functions(data_validator_bp)
app.register_functions(email_sender_bp)
app.register_functions(change_tracker_bp)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.function_name(name="health")
@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint"""
    logger.info("Health check requested")
    return func.HttpResponse(
        body='{"status": "healthy", "service": "Azure Excel Data Validation Agent"}',
        status_code=200,
        headers={"Content-Type": "application/json"}
    )