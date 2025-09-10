import azure.functions as func
import logging
import json
from datetime import datetime
from src.services.excel_service import ExcelService
from src.services.validation_service import ValidationService
from src.services.email_service import EmailService
from src.services.storage_service import StorageService
from src.models.validation_models import ProcessingRequest, ValidationRule
from src.utils.helpers import generate_file_hash, log_function_execution

logger = logging.getLogger(__name__)

# Create function blueprint
excel_processor_bp = func.Blueprint()

@excel_processor_bp.function_name(name="process_excel_file")
@excel_processor_bp.route(route="process", methods=["POST"])
async def process_excel_file(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main function to process uploaded Excel files
    
    Expected request body:
    {
        "filename": "data.xlsx",
        "file_data": "base64_encoded_file_data",
        "validation_rules": [...],  // Optional custom rules
        "email_lookup_field": "email",  // Optional, defaults to "email"
        "requester_email": "user@domain.com"  // Optional
    }
    """
    start_time = datetime.now()
    
    try:
        # Parse request
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
        if 'filename' not in req_body or 'file_data' not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "filename and file_data are required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        filename = req_body['filename']
        
        # Decode base64 file data
        import base64
        try:
            file_data = base64.b64decode(req_body['file_data'])
        except Exception as e:
            return func.HttpResponse(
                json.dumps({"error": f"Invalid file data encoding: {str(e)}"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Enforce file size limit if configured
        import os
        try:
            max_mb = float(os.getenv('MAX_FILE_SIZE_MB', '50'))
        except ValueError:
            max_mb = 50.0
        max_bytes = int(max_mb * 1024 * 1024)
        if len(file_data) > max_bytes:
            return func.HttpResponse(
                json.dumps({
                    "error": "File too large",
                    "message": f"Max allowed size is {int(max_mb)} MB"
                }),
                status_code=413,
                headers={"Content-Type": "application/json"}
            )
        
        # Initialize services
        excel_service = ExcelService()
        validation_service = ValidationService()
        email_service = EmailService()
        storage_service = StorageService()
        
        # Validate file format against allowed types
        if not excel_service.validate_file_format(filename):
            return func.HttpResponse(
                json.dumps({"error": "Unsupported file format"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        logger.info(f"Processing Excel file: {filename}")
        
        # Parse Excel file
        sheets_dict, metadata = excel_service.parse_excel_file(file_data, filename)
        
        # Store file and metadata
        storage_service.store_file(file_data, metadata.file_id, filename)
        storage_service.store_file_metadata(metadata)
        
        # Extract data for validation
        validation_data = excel_service.extract_data_for_validation(sheets_dict)
        
        # Parse custom validation rules if provided
        custom_rules = []
        if 'validation_rules' in req_body:
            try:
                custom_rules = [ValidationRule(**rule) for rule in req_body['validation_rules']]
            except Exception as e:
                logger.warning(f"Error parsing custom validation rules: {str(e)}")
        
        # Perform validation
        validation_result = validation_service.validate_data(
            validation_data,
            metadata.file_id,
            custom_rules
        )
        
        # Store validation result
        storage_service.store_validation_result(validation_result)
        
        # Handle email notifications based on validation result
        email_lookup_field = req_body.get('email_lookup_field', 'email')
        requester_email = req_body.get('requester_email')
        
        # Extract email addresses for notifications
        recipient_emails = excel_service.extract_email_column(validation_data, email_lookup_field)
        if requester_email:
            recipient_emails.append(requester_email)
        
        # Remove duplicates
        recipient_emails = list(set(recipient_emails))
        
        # Send appropriate notifications
        email_notifications = []
        if validation_result.status.value == "failed":
            # Send failure notification
            email_notifications = email_service.send_validation_failure_notification(
                validation_result, recipient_emails
            )
            
            # Create change tracking record
            file_hash = generate_file_hash(file_data)
            storage_service.create_change_tracking_record(
                metadata.file_id,
                validation_result.validation_id,
                file_hash
            )
            
        elif validation_result.status.value == "passed":
            # Send success notification
            email_notifications = email_service.send_validation_success_notification(
                metadata.file_id, recipient_emails
            )
        
        # Store email notification records
        for notification in email_notifications:
            storage_service.store_email_notification(notification)
        
        # Update validation result with email info
        validation_result.email_sent = len(email_notifications) > 0
        if recipient_emails:
            validation_result.email_recipient = recipient_emails[0]  # Primary recipient
        
        # Prepare response
        response_data = {
            "file_id": metadata.file_id,
            "validation_id": validation_result.validation_id,
            "status": validation_result.status.value,
            "total_errors": validation_result.total_errors,
            "total_warnings": validation_result.total_warnings,
            "processed_rows": validation_result.processed_rows,
            "email_sent": validation_result.email_sent,
            "notifications_sent": len(email_notifications),
            "timestamp": validation_result.timestamp.isoformat()
        }
        
        # Include error details if validation failed
        if validation_result.status.value == "failed":
            response_data["errors"] = [
                {
                    "row": error.row,
                    "column": error.column,
                    "value": str(error.value),
                    "message": error.message,
                    "suggested_correction": error.suggested_correction
                }
                for error in validation_result.errors[:10]  # Limit to first 10 errors
            ]
        
        end_time = datetime.now()
        log_function_execution(
            "process_excel_file",
            start_time,
            end_time,
            True,
            {
                "file_id": metadata.file_id,
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
        log_function_execution("process_excel_file", start_time, end_time, False)
        
        logger.error(f"Error processing Excel file: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": "Failed to process Excel file",
                "details": str(e)
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

@excel_processor_bp.function_name(name="get_processing_status")
@excel_processor_bp.route(route="status/{file_id}", methods=["GET"])
async def get_processing_status(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get processing status for a file
    """
    try:
        file_id = req.route_params.get('file_id')
        
        if not file_id:
            return func.HttpResponse(
                json.dumps({"error": "file_id is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        storage_service = StorageService()
        
        # Get file metadata
        metadata = storage_service.get_file_metadata(file_id)
        if not metadata:
            return func.HttpResponse(
                json.dumps({"error": "File not found"}),
                status_code=404,
                headers={"Content-Type": "application/json"}
            )
        
        # Get latest validation result
        # This would need to be implemented in storage service
        # For now, return basic file info
        
        response_data = {
            "file_id": file_id,
            "filename": metadata.filename,
            "upload_timestamp": metadata.upload_timestamp.isoformat(),
            "file_size": metadata.file_size,
            "total_rows": metadata.total_rows,
            "total_columns": metadata.total_columns,
            "sheet_names": metadata.sheet_names
        }
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": "Failed to get processing status"
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )
