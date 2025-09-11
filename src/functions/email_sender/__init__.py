import azure.functions as func
import logging
import json
from datetime import datetime
from src.services.email_service import EmailService
from src.services.storage_service import StorageService
from src.models.validation_models import ValidationResult, ValidationStatus
from src.utils.helpers import log_function_execution, validate_email_format, get_correlation_id

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
                logger.warning(f"[{correlation_id}] Invalid email format: {email}")
        
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
            # Prefer retrieving the validation to get the true file_id
            file_id = None
            validation_result = storage_service.get_validation_result(validation_id)
            if validation_result:
                file_id = validation_result.file_id
            else:
                # Fallback: use provided validation_id as-is
                file_id = validation_id
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
                "recipients": len(valid_emails),
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
        log_function_execution("send_notification", start_time, end_time, False, {"correlation_id": correlation_id})
        
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
        
        # Query storage for the email notification record
        storage_service = StorageService()
        record = storage_service.get_email_notification(notification_id)
        if not record:
            return func.HttpResponse(
                json.dumps({"error": "Notification not found"}),
                status_code=404,
                headers={"Content-Type": "application/json"}
            )

        response_data = {
            "notification_id": record.notification_id,
            "file_id": record.file_id,
            "validation_id": record.validation_id,
            "recipient_email": record.recipient_email,
            "status": record.delivery_status,
            "sent_timestamp": record.sent_timestamp.isoformat(),
            "correction_deadline": record.correction_deadline.isoformat() if record.correction_deadline else None,
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

@email_sender_bp.function_name(name="send_reminders")
@email_sender_bp.timer_trigger(schedule="0 0 9 * * *")  # Daily at 9 AM UTC
async def send_reminder_emails(timer: func.TimerRequest) -> None:
    """Send reminder emails for failed validations older than N days.

    Controls:
    - REMINDER_DAYS_OLD: integer days threshold (default 3)
    - REMINDER_MAX_ITEMS: safety cap (default 100)
    """
    try:
        import os
        days = int(os.getenv("REMINDER_DAYS_OLD", "3"))
        cap = int(os.getenv("REMINDER_MAX_ITEMS", "100"))

        storage_service = StorageService()
        email_service = EmailService()

        candidates = storage_service.list_failed_validations(days_older_than=days, limit=cap)
        total_notifications = 0
        for vr in candidates:
            recipients = storage_service.list_email_recipients_for_validation(vr.validation_id)
            if not recipients:
                continue
            notes = email_service.send_validation_failure_notification(vr, recipients)
            for n in notes:
                storage_service.store_email_notification(n)
            total_notifications += len(notes)

        logger.info(f"Reminder job processed {len(candidates)} validations; sent {total_notifications} notifications")
    except Exception as e:
        logger.error(f"Error in reminder email job: {str(e)}")
