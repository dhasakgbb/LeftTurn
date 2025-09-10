import azure.functions as func
import logging
import json
from datetime import datetime
from src.services.email_service import EmailService
from src.services.storage_service import StorageService
from src.models.validation_models import ValidationResult, ValidationStatus
from src.utils.helpers import log_function_execution, validate_email_format

logger = logging.getLogger(__name__)

# Create function blueprint
email_sender_bp = func.Blueprint()

@email_sender_bp.function_name(name="send_notification")
@email_sender_bp.route(route="notify", methods=["POST"])
async def send_notification(req: func.HttpRequest) -> func.HttpResponse:
    """
    Send email notification for validation results
    
    Expected request body:
    {
        "validation_id": "validation_identifier",
        "recipient_emails": ["email1@domain.com", "email2@domain.com"],
        "notification_type": "failure|success|reminder"
    }
    """
    start_time = datetime.now()
    
    try:
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Validate required fields
        if 'validation_id' not in req_body or 'recipient_emails' not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "validation_id and recipient_emails are required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        validation_id = req_body['validation_id']
        recipient_emails = req_body['recipient_emails']
        notification_type = req_body.get('notification_type', 'failure')
        
        # Validate email addresses
        valid_emails = []
        for email in recipient_emails:
            if validate_email_format(email):
                valid_emails.append(email)
            else:
                logger.warning(f"Invalid email format: {email}")
        
        if not valid_emails:
            return func.HttpResponse(
                json.dumps({"error": "No valid email addresses provided"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Initialize services
        email_service = EmailService()
        storage_service = StorageService()
        
        notifications_sent = []
        
        if notification_type in ['failure', 'reminder']:
            # Get validation result
            validation_result = storage_service.get_validation_result(validation_id)
            if not validation_result:
                return func.HttpResponse(
                    json.dumps({"error": "Validation result not found"}),
                    status_code=404,
                    headers={"Content-Type": "application/json"}
                )
            
            # Send failure/reminder notifications
            notifications = email_service.send_validation_failure_notification(
                validation_result, valid_emails
            )
            notifications_sent.extend(notifications)
            
        elif notification_type == 'success':
            # Extract file_id from validation_id (assuming format: val_file_id_timestamp)
            file_id = validation_id.split('_')[1] if '_' in validation_id else validation_id
            
            # Send success notifications
            notifications = email_service.send_validation_success_notification(
                file_id, valid_emails
            )
            notifications_sent.extend(notifications)
        
        # Store notification records
        for notification in notifications_sent:
            storage_service.store_email_notification(notification)
        
        response_data = {
            "validation_id": validation_id,
            "notification_type": notification_type,
            "notifications_sent": len(notifications_sent),
            "recipients": valid_emails,
            "timestamp": datetime.now().isoformat(),
            "notification_ids": [n.notification_id for n in notifications_sent]
        }
        
        end_time = datetime.now()
        log_function_execution(
            "send_notification",
            start_time,
            end_time,
            True,
            {
                "validation_id": validation_id,
                "notification_type": notification_type,
                "recipients": len(valid_emails)
            }
        )
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        end_time = datetime.now()
        log_function_execution("send_notification", start_time, end_time, False)
        
        logger.error(f"Error sending notification: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": "Failed to send notification",
                "details": str(e)
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

@email_sender_bp.function_name(name="send_custom_email")
@email_sender_bp.route(route="custom", methods=["POST"])
async def send_custom_email(req: func.HttpRequest) -> func.HttpResponse:
    """
    Send custom email notification
    
    Expected request body:
    {
        "recipient_emails": ["email@domain.com"],
        "subject": "Custom Subject",
        "message": "Custom message content",
        "message_type": "html|text"  // Optional, defaults to text
    }
    """
    try:
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Validate required fields
        required_fields = ['recipient_emails', 'subject', 'message']
        missing_fields = [field for field in required_fields if field not in req_body]
        
        if missing_fields:
            return func.HttpResponse(
                json.dumps({"error": f"Missing required fields: {', '.join(missing_fields)}"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        recipient_emails = req_body['recipient_emails']
        subject = req_body['subject']
        message = req_body['message']
        message_type = req_body.get('message_type', 'text')
        
        # Validate email addresses
        valid_emails = [email for email in recipient_emails if validate_email_format(email)]
        
        if not valid_emails:
            return func.HttpResponse(
                json.dumps({"error": "No valid email addresses provided"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Initialize email service
        email_service = EmailService()
        
        if not email_service.email_client:
            return func.HttpResponse(
                json.dumps({"error": "Email service not configured"}),
                status_code=503,
                headers={"Content-Type": "application/json"}
            )
        
        # Send emails
        sent_count = 0
        failed_emails = []
        
        for email in valid_emails:
            try:
                # Prepare email content
                email_message = {
                    "senderAddress": email_service.sender_email,
                    "recipients": {
                        "to": [{"address": email}]
                    },
                    "content": {
                        "subject": subject
                    }
                }
                
                # Set content based on message type
                if message_type.lower() == 'html':
                    email_message["content"]["html"] = message
                else:
                    email_message["content"]["plainText"] = message
                
                # Send email
                poller = email_service.email_client.begin_send(email_message)
                result = poller.result()
                
                sent_count += 1
                logger.info(f"Custom email sent to {email}: {result.message_id}")
                
            except Exception as e:
                failed_emails.append({"email": email, "error": str(e)})
                logger.error(f"Failed to send custom email to {email}: {str(e)}")
        
        response_data = {
            "emails_sent": sent_count,
            "total_recipients": len(valid_emails),
            "failed_emails": failed_emails,
            "subject": subject,
            "timestamp": datetime.now().isoformat()
        }
        
        status_code = 200 if sent_count > 0 else 500
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=status_code,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error sending custom email: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": "Failed to send custom email"
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

@email_sender_bp.function_name(name="get_notification_status")
@email_sender_bp.route(route="status/{notification_id}", methods=["GET"])
async def get_notification_status(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get the status of a sent notification
    """
    try:
        notification_id = req.route_params.get('notification_id')
        
        if not notification_id:
            return func.HttpResponse(
                json.dumps({"error": "notification_id is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # For now, return basic status
        # In a full implementation, this would query the storage service
        # to get actual notification status
        
        response_data = {
            "notification_id": notification_id,
            "status": "delivered",  # This would be from actual delivery tracking
            "sent_timestamp": datetime.now().isoformat(),
            "delivery_timestamp": datetime.now().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error getting notification status: {str(e)}")
        
        return func.HttpResponse(
            json.dumps({
                "error": "Internal server error",
                "message": "Failed to get notification status"
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

@email_sender_bp.function_name(name="send_reminder")
@email_sender_bp.timer_trigger(schedule="0 0 9 * * *")  # Daily at 9 AM
async def send_reminder_emails(timer: func.TimerRequest) -> None:
    """
    Timer-triggered function to send reminder emails for pending corrections
    """
    try:
        logger.info("Starting reminder email job")
        
        # This would query the storage service to find validation results
        # that failed and haven't been corrected within the deadline
        
        # For now, just log that the reminder job ran
        logger.info("Reminder email job completed")
        
    except Exception as e:
        logger.error(f"Error in reminder email job: {str(e)}")