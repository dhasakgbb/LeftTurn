try:  # pragma: no cover
    import azure.functions as func
except ModuleNotFoundError:  # pragma: no cover
    from src.utils.azure_functions_stub import functions as func
import logging
import json
from datetime import datetime
from src.services.validation_service import ValidationService
from src.models.validation_models import ValidationRule
from src.utils.helpers import log_function_execution

logger = logging.getLogger(__name__)

# Create function blueprint
data_validator_bp = func.Blueprint()

@data_validator_bp.function_name(name="validate_data")
@data_validator_bp.route(route="validate", methods=["POST"])
async def validate_data(req: func.HttpRequest) -> func.HttpResponse:
    """
    Standalone data validation function
    
    Expected request body:
    {
        "data": [
            {"column1": "value1", "column2": "value2"},
            ...
        ],
        "validation_rules": [...],  // Custom validation rules
        "data_id": "optional_identifier"
    }
    """
    start_time = datetime.now()
    
    try:
        try:
            req_body = req.get_json()
        except Exception:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON in request body"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        if 'data' not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "data field is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Convert data to DataFrame
        import pandas as pd
        data = pd.DataFrame(req_body['data'])
        
        # Parse validation rules
        custom_rules = []
        if 'validation_rules' in req_body:
            try:
                custom_rules = [ValidationRule(**rule) for rule in req_body['validation_rules']]
            except Exception as e:
                logger.warning(f"Error parsing validation rules: {str(e)}")
        
        # Generate data ID if not provided
        data_id = req_body.get('data_id', f"data_{int(datetime.now().timestamp())}")
        
        # Initialize validation service
        validation_service = ValidationService()
        
        # Perform validation
        validation_result = validation_service.validate_data(data, data_id, custom_rules)
        
        # Prepare response
        response_data = {
            "data_id": data_id,
            "validation_id": validation_result.validation_id,
            "status": validation_result.status.value,
            "total_errors": validation_result.total_errors,
            "total_warnings": validation_result.total_warnings,
            "processed_rows": validation_result.processed_rows,
            "timestamp": validation_result.timestamp.isoformat(),
            "errors": [
                {
                    "row": error.row,
                    "column": error.column,
                    "value": str(error.value),
                    "message": error.message,
                    "severity": error.severity,
                    "suggested_correction": error.suggested_correction
                }
                for error in validation_result.errors
            ],
            "warnings": [
                {
                    "row": warning.row,
                    "column": warning.column,
                    "value": str(warning.value),
                    "message": warning.message,
                    "severity": warning.severity,
                    "suggested_correction": warning.suggested_correction
                }
                for warning in validation_result.warnings
            ]
        }
        
        end_time = datetime.now()
        log_function_execution(
            "validate_data",
            start_time,
            end_time,
            True,
            {
                "data_id": data_id,
                "validation_status": validation_result.status.value,
                "errors": validation_result.total_errors
            }
        )
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        end_time = datetime.now()
        log_function_execution("validate_data", start_time, end_time, False)
        
        logger.error(f"Error validating data: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": "Failed to validate data",
                "details": str(e)
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

@data_validator_bp.function_name(name="create_validation_rules")
@data_validator_bp.route(route="rules", methods=["POST"])
async def create_validation_rules(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create and test validation rules
    
    Expected request body:
    {
        "rule_name": "Custom Rule",
        "rule_type": "format|range|data_type|custom",
        "description": "Rule description",
        "parameters": {...},
        "severity": "error|warning|info",
        "test_data": [{"col": "value"}, ...]  // Optional test data
    }
    """
    try:
        try:
            req_body = req.get_json()
        except Exception:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON in request body"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Validate required fields
        required_fields = ['rule_name', 'rule_type', 'description', 'parameters']
        missing_fields = [field for field in required_fields if field not in req_body]
        
        if missing_fields:
            return func.HttpResponse(
                json.dumps({"error": f"Missing required fields: {', '.join(missing_fields)}"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Create validation rule
        rule_id = f"custom_{int(datetime.now().timestamp())}"
        
        try:
            validation_rule = ValidationRule(
                rule_id=rule_id,
                rule_name=req_body['rule_name'],
                description=req_body['description'],
                rule_type=req_body['rule_type'],
                parameters=req_body['parameters'],
                severity=req_body.get('severity', 'error')
            )
        except Exception as e:
            return func.HttpResponse(
                json.dumps({"error": f"Invalid validation rule: {str(e)}"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        response_data = {
            "rule_id": rule_id,
            "rule": validation_rule.dict(),
            "status": "created"
        }
        
        # Test the rule if test data is provided
        if 'test_data' in req_body and req_body['test_data']:
            try:
                import pandas as pd
                test_df = pd.DataFrame(req_body['test_data'])
                
                validation_service = ValidationService()
                test_result = validation_service.validate_data(test_df, "test", [validation_rule])
                
                response_data["test_result"] = {
                    "status": test_result.status.value,
                    "errors": len(test_result.errors),
                    "warnings": len(test_result.warnings),
                    "sample_errors": [
                        {
                            "row": error.row,
                            "column": error.column,
                            "message": error.message
                        }
                        for error in test_result.errors[:3]  # First 3 errors
                    ]
                }
                
            except Exception as e:
                response_data["test_result"] = {
                    "status": "test_failed",
                    "error": str(e)
                }
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=201,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error creating validation rule: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": "Failed to create validation rule"
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

@data_validator_bp.function_name(name="get_validation_templates")
@data_validator_bp.route(route="templates", methods=["GET"])
async def get_validation_templates(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get predefined validation rule templates
    """
    try:
        templates = {
            "email_validation": {
                "rule_name": "Email Format Validation",
                "rule_type": "format",
                "description": "Validate email addresses",
                "parameters": {
                    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                    "columns": ["email"]
                },
                "severity": "error"
            },
            "phone_validation": {
                "rule_name": "Phone Number Validation",
                "rule_type": "format",
                "description": "Validate phone number format",
                "parameters": {
                    "pattern": r"^\+?1?-?(\d{3})-?(\d{3})-?(\d{4})$",
                    "columns": ["phone"]
                },
                "severity": "error"
            },
            "numeric_range": {
                "rule_name": "Numeric Range Validation",
                "rule_type": "range",
                "description": "Validate numeric values within range",
                "parameters": {
                    "min": 0,
                    "max": 100,
                    "columns": ["score", "percentage"]
                },
                "severity": "error"
            },
            "required_fields": {
                "rule_name": "Required Fields",
                "rule_type": "custom",
                "description": "Ensure required fields are not empty",
                "parameters": {
                    "required_columns": ["name", "email", "id"]
                },
                "severity": "error"
            },
            "date_format": {
                "rule_name": "Date Format Validation",
                "rule_type": "format",
                "description": "Validate date format (YYYY-MM-DD)",
                "parameters": {
                    "pattern": r"^\d{4}-\d{2}-\d{2}$",
                    "columns": ["date", "created_date"]
                },
                "severity": "warning"
            }
        }
        
        return func.HttpResponse(
            json.dumps({
                "templates": templates,
                "total_templates": len(templates)
            }),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error getting validation templates: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": "Failed to get validation templates"
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )
