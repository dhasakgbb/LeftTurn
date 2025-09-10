import azure.functions as func
import logging
import json
import base64
from datetime import datetime
from src.services.excel_service import ExcelService
from src.services.validation_service import ValidationService
from src.services.storage_service import StorageService
from src.services.email_service import EmailService
from src.utils.helpers import generate_file_hash, log_function_execution, get_correlation_id

logger = logging.getLogger(__name__)

# Create function blueprint
change_tracker_bp = func.Blueprint()

@change_tracker_bp.function_name(name="verify_changes")
@change_tracker_bp.route(route="verify", methods=["POST"])
async def verify_changes(req: func.HttpRequest) -> func.HttpResponse:
    """
    Verify that changes have been made to a previously failed validation
    
    Expected request body:
    {
        "original_file_id": "file_identifier",
        "updated_file_data": "base64_encoded_updated_file",
        "updated_filename": "updated_file.xlsx"
    }
    """
    start_time = datetime.now()
    correlation_id = get_correlation_id(req)
    
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
        required_fields = ['original_file_id', 'updated_file_data', 'updated_filename']
        missing_fields = [field for field in required_fields if field not in req_body]
        
        if missing_fields:
            return func.HttpResponse(
                json.dumps({"error": f"Missing required fields: {', '.join(missing_fields)}"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        original_file_id = req_body['original_file_id']
        updated_filename = req_body['updated_filename']
        
        # Decode updated file data
        try:
            updated_file_data = base64.b64decode(req_body['updated_file_data'])
        except Exception as e:
            return func.HttpResponse(
                json.dumps({"error": f"Invalid file data encoding: {str(e)}"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Initialize services
        excel_service = ExcelService()
        validation_service = ValidationService()
        storage_service = StorageService()
        email_service = EmailService()
        
        # Get original file metadata
        original_metadata = storage_service.get_file_metadata(original_file_id)
        if not original_metadata:
            return func.HttpResponse(
                json.dumps({"error": "Original file not found"}),
                status_code=404,
                headers={"Content-Type": "application/json"}
            )
        
        logger.info(f"[{correlation_id}] Verifying changes for file: {original_file_id}")
        
        # Parse updated Excel file
        updated_sheets_dict, updated_metadata = excel_service.parse_excel_file(
            updated_file_data, updated_filename
        )
        
        # Generate hash for comparison
        updated_file_hash = generate_file_hash(updated_file_data)
        
        # Store updated file
        storage_service.store_file(updated_file_data, updated_metadata.file_id, updated_filename)
        storage_service.store_file_metadata(updated_metadata)
        
        # Extract data for validation
        updated_validation_data = excel_service.extract_data_for_validation(updated_sheets_dict)
        
        # Re-validate the updated data using the same rules as the original
        # (In a full implementation, you'd retrieve the original validation rules)
        updated_validation_result = validation_service.validate_data(
            updated_validation_data,
            updated_metadata.file_id,
            custom_rules=[]  # Use default rules for now
        )
        
        # Store updated validation result
        storage_service.store_validation_result(updated_validation_result)
        
        # Update change tracking record
        # Find existing tracking record for the original file
        # (This would need to be implemented in storage service)
        
        # Determine if changes were successful
        changes_successful = updated_validation_result.total_errors == 0
        
        # Compare file contents to detect actual changes
        change_description = "File updated and re-validated"
        
        # Prepare response
        response_data = {
            "original_file_id": original_file_id,
            "updated_file_id": updated_metadata.file_id,
            "updated_validation_id": updated_validation_result.validation_id,
            "changes_successful": changes_successful,
            "change_description": change_description,
            "updated_file_hash": updated_file_hash,
            "validation_status": updated_validation_result.status.value,
            "remaining_errors": updated_validation_result.total_errors,
            "remaining_warnings": updated_validation_result.total_warnings,
            "timestamp": datetime.now().isoformat()
        }
        
        # If validation passed, send success notification
        if changes_successful:
            # Extract email addresses from updated data
            recipient_emails = excel_service.extract_email_column(updated_validation_data)
            
            if recipient_emails:
                success_notifications = email_service.send_validation_success_notification(
                    updated_metadata.file_id, recipient_emails
                )
                
                # Store notification records
                for notification in success_notifications:
                    storage_service.store_email_notification(notification)
                
                response_data["success_notifications_sent"] = len(success_notifications)
            
            logger.info(f"Changes verified successfully for file: {original_file_id}")
        
        else:
            # If still has errors, send updated failure notification
            recipient_emails = excel_service.extract_email_column(updated_validation_data)
            
            if recipient_emails:
                failure_notifications = email_service.send_validation_failure_notification(
                    updated_validation_result, recipient_emails
                )
                
                # Store notification records
                for notification in failure_notifications:
                    storage_service.store_email_notification(notification)
                
                response_data["failure_notifications_sent"] = len(failure_notifications)
            
            # Include error details
            response_data["remaining_errors_details"] = [
                {
                    "row": error.row,
                    "column": error.column,
                    "value": str(error.value),
                    "message": error.message,
                    "suggested_correction": error.suggested_correction
                }
                for error in updated_validation_result.errors[:10]
            ]
            
            logger.warning(f"Changes verification found remaining errors for file: {original_file_id}")
        
        end_time = datetime.now()
        log_function_execution(
            "verify_changes",
            start_time,
            end_time,
            True,
            {
                "original_file_id": original_file_id,
                "changes_successful": changes_successful,
                "remaining_errors": updated_validation_result.total_errors,
                "correlation_id": correlation_id
            }
        )
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        end_time = datetime.now()
        log_function_execution("verify_changes", start_time, end_time, False, {"correlation_id": correlation_id})
        
        logger.error(f"Error verifying changes: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": "Failed to verify changes",
                "details": str(e)
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

@change_tracker_bp.function_name(name="get_change_history")
@change_tracker_bp.route(route="history/{file_id}", methods=["GET"])
async def get_change_history(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get change history for a file
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
        records = storage_service.get_change_history(file_id)

        response = {
            "file_id": file_id,
            "changes": [
                {
                    "tracking_id": r.tracking_id,
                    "timestamp": (r.change_timestamp.isoformat() if r.change_timestamp else None),
                    "description": r.change_description,
                    "verified": r.verified,
                    "original_file_hash": r.original_file_hash,
                    "updated_file_hash": r.updated_file_hash,
                    "validation_id": r.validation_id,
                }
                for r in records
            ],
            "total_changes": len(records),
            "last_updated": (records[0].change_timestamp.isoformat() if records and records[0].change_timestamp else None),
        }

        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error getting change history: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": "Failed to get change history"
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

@change_tracker_bp.function_name(name="compare_files")
@change_tracker_bp.route(route="compare", methods=["POST"])
async def compare_files(req: func.HttpRequest) -> func.HttpResponse:
    """
    Compare two Excel files to identify changes
    
    Expected request body:
    {
        "original_file_data": "base64_encoded_original",
        "updated_file_data": "base64_encoded_updated",
        "comparison_type": "content|structure|both"  // Optional, defaults to "both"
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
        if 'original_file_data' not in req_body or 'updated_file_data' not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "original_file_data and updated_file_data are required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        comparison_type = req_body.get('comparison_type', 'both')
        
        # Decode file data
        try:
            original_data = base64.b64decode(req_body['original_file_data'])
            updated_data = base64.b64decode(req_body['updated_file_data'])
        except Exception as e:
            return func.HttpResponse(
                json.dumps({"error": f"Invalid file data encoding: {str(e)}"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Initialize Excel service
        excel_service = ExcelService()
        
        # Parse both files
        original_sheets, _ = excel_service.parse_excel_file(original_data, "original.xlsx")
        updated_sheets, _ = excel_service.parse_excel_file(updated_data, "updated.xlsx")
        
        # Generate hashes for comparison
        original_hash = generate_file_hash(original_data)
        updated_hash = generate_file_hash(updated_data)
        
        # Basic comparison results
        comparison_result = {
            "files_identical": original_hash == updated_hash,
            "original_hash": original_hash,
            "updated_hash": updated_hash,
            "comparison_type": comparison_type,
            "timestamp": datetime.now().isoformat()
        }
        
        if not comparison_result["files_identical"]:
            # Detailed comparison (simplified for this example)
            changes = []
            
            # Compare sheet structure
            if comparison_type in ['structure', 'both']:
                original_sheet_names = set(original_sheets.keys())
                updated_sheet_names = set(updated_sheets.keys())
                
                if original_sheet_names != updated_sheet_names:
                    changes.append({
                        "type": "structure_change",
                        "description": "Sheet names changed",
                        "details": {
                            "added_sheets": list(updated_sheet_names - original_sheet_names),
                            "removed_sheets": list(original_sheet_names - updated_sheet_names)
                        }
                    })
            
            # Compare content (basic comparison)
            if comparison_type in ['content', 'both']:
                for sheet_name in original_sheets.keys():
                    if sheet_name in updated_sheets:
                        original_df = original_sheets[sheet_name]
                        updated_df = updated_sheets[sheet_name]
                        
                        # Compare dimensions
                        if original_df.shape != updated_df.shape:
                            changes.append({
                                "type": "content_change",
                                "sheet": sheet_name,
                                "description": "Sheet dimensions changed",
                                "details": {
                                    "original_shape": original_df.shape,
                                    "updated_shape": updated_df.shape
                                }
                            })
            
            comparison_result["changes"] = changes
            comparison_result["total_changes"] = len(changes)
        
        return func.HttpResponse(
            json.dumps(comparison_result),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error comparing files: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": "Failed to compare files",
                "details": str(e)
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )
