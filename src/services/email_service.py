import logging
import os
from typing import List, Optional
from datetime import datetime, timedelta, timezone
try:
    from azure.communication.email import EmailClient
except Exception:  # pragma: no cover - allow running without Azure SDKs installed
    EmailClient = None  # type: ignore
from src.models.validation_models import ValidationResult, EmailNotification

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending email notifications using Azure Communication Services"""
    
    def __init__(self):
        self.email_client = self._initialize_email_client()
        self.sender_email = os.getenv("DEFAULT_SENDER_EMAIL", "noreply@yourdomain.com")
    
    def _initialize_email_client(self) -> Optional[EmailClient]:
        """Initialize Azure Communication Services Email client"""
        try:
            connection_string = os.getenv("AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING")
            if not connection_string:
                logger.warning("Azure Communication Services connection string not configured")
                return None
            
            return EmailClient.from_connection_string(connection_string)
        except Exception as e:
            logger.error(f"Failed to initialize email client: {str(e)}")
            return None
    
    def send_validation_failure_notification(self, validation_result: ValidationResult, 
                                           recipient_emails: List[str]) -> List[EmailNotification]:
        """
        Send email notification for validation failures
        
        Args:
            validation_result: ValidationResult object with errors
            recipient_emails: List of email addresses to notify
            
        Returns:
            List of EmailNotification objects
        """
        notifications = []
        
        if not self.email_client:
            logger.error("Email client not initialized")
            return notifications
        
        # Generate email content
        subject = f"Data Validation Failed - {validation_result.file_id}"
        html_content = self._generate_validation_email_html(validation_result)
        text_content = self._generate_validation_email_text(validation_result)
        
        # Send to each recipient
        for recipient in recipient_emails:
            try:
                notification = self._send_email(
                    recipient,
                    subject,
                    html_content,
                    text_content,
                    validation_result
                )
                notifications.append(notification)
                
            except Exception as e:
                logger.error(f"Failed to send email to {recipient}: {str(e)}")
                # Create failed notification record
                notification = EmailNotification(
                    notification_id=f"email_{int(datetime.now(timezone.utc).timestamp())}",
                    file_id=validation_result.file_id,
                    validation_id=validation_result.validation_id,
                    recipient_email=recipient,
                    subject=subject,
                    sent_timestamp=datetime.now(timezone.utc),
                    delivery_status="failed"
                )
                notifications.append(notification)
        
        return notifications
    
    def _send_email(self, recipient: str, subject: str, html_content: str, 
                   text_content: str, validation_result: ValidationResult) -> EmailNotification:
        """Send individual email"""
        
        # Create email message
        message = {
            "senderAddress": self.sender_email,
            "recipients": {
                "to": [{"address": recipient}]
            },
            "content": {
                "subject": subject,
                "html": html_content,
                "plainText": text_content
            }
        }
        
        # Send email
        poller = self.email_client.begin_send(message)
        result = poller.result()
        
        # Create notification record
        notification = EmailNotification(
            notification_id=f"email_{int(datetime.now(timezone.utc).timestamp())}_{recipient.replace('@', '_')}",
            file_id=validation_result.file_id,
            validation_id=validation_result.validation_id,
            recipient_email=recipient,
            subject=subject,
            sent_timestamp=datetime.now(timezone.utc),
            delivery_status="sent",
            correction_deadline=datetime.now(timezone.utc) + timedelta(days=3)  # 3 days to correct
        )
        
        logger.info(f"Email sent successfully to {recipient}: {result.message_id}")
        return notification
    
    def _generate_validation_email_html(self, validation_result: ValidationResult) -> str:
        """Generate HTML email content for validation failures"""
        
        errors_html = ""
        for error in validation_result.errors[:10]:  # Limit to first 10 errors
            suggestion = f"<br><strong>Suggestion:</strong> {error.suggested_correction}" if error.suggested_correction else ""
            errors_html += f"""
            <tr>
                <td>{error.row}</td>
                <td>{error.column}</td>
                <td>{error.value}</td>
                <td>{error.message}{suggestion}</td>
            </tr>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ color: #d73027; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="header">Data Validation Failed</h1>
                
                <p>Your submitted Excel file has failed data validation. Please review and correct the following issues:</p>
                
                <h3>Validation Summary</h3>
                <ul>
                    <li><strong>File ID:</strong> {validation_result.file_id}</li>
                    <li><strong>Total Errors:</strong> {validation_result.total_errors}</li>
                    <li><strong>Total Warnings:</strong> {validation_result.total_warnings}</li>
                    <li><strong>Rows Processed:</strong> {validation_result.processed_rows}</li>
                    <li><strong>Validation Date (UTC):</strong> {validation_result.timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}</li>
                </ul>
                
                <h3>Errors Found</h3>
                <table>
                    <tr>
                        <th>Row</th>
                        <th>Column</th>
                        <th>Current Value</th>
                        <th>Issue & Suggested Correction</th>
                    </tr>
                    {errors_html}
                </table>
                
                {"<p><em>Note: Only the first 10 errors are shown. Please correct all issues and resubmit.</em></p>" if len(validation_result.errors) > 10 else ""}
                
                <p><strong>Next Steps:</strong></p>
                <ol>
                    <li>Download and correct your Excel file</li>
                    <li>Address all validation errors listed above</li>
                    <li>Resubmit the corrected file</li>
                </ol>
                
                <p>Please correct these issues and resubmit your file within 3 business days.</p>
                
                <div class="footer">
                    <p>This is an automated message from the Azure Excel Data Validation Agent.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def _generate_validation_email_text(self, validation_result: ValidationResult) -> str:
        """Generate plain text email content for validation failures"""
        
        errors_text = ""
        for error in validation_result.errors[:10]:
            suggestion = f" | Suggestion: {error.suggested_correction}" if error.suggested_correction else ""
            errors_text += f"Row {error.row}, Column {error.column}: {error.message} (Value: {error.value}){suggestion}\n"
        
        text_content = f"""
Data Validation Failed

Your submitted Excel file has failed data validation. Please review and correct the following issues:

Validation Summary (UTC):
- File ID: {validation_result.file_id}
- Total Errors: {validation_result.total_errors}
- Total Warnings: {validation_result.total_warnings}
- Rows Processed: {validation_result.processed_rows}
- Validation Date (UTC): {validation_result.timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}

Errors Found:
{errors_text}

{"Note: Only the first 10 errors are shown. Please correct all issues and resubmit." if len(validation_result.errors) > 10 else ""}

Next Steps:
1. Download and correct your Excel file
2. Address all validation errors listed above
3. Resubmit the corrected file

Please correct these issues and resubmit your file within 3 business days.

This is an automated message from the Azure Excel Data Validation Agent.
        """
        
        return text_content
    
    def send_validation_success_notification(self, file_id: str, recipient_emails: List[str]) -> List[EmailNotification]:
        """
        Send email notification for successful validation
        
        Args:
            file_id: File identifier
            recipient_emails: List of email addresses to notify
            
        Returns:
            List of EmailNotification objects
        """
        notifications = []
        
        if not self.email_client:
            logger.error("Email client not initialized")
            return notifications
        
        subject = f"Data Validation Successful - {file_id}"
        html_content = self._generate_success_email_html(file_id)
        text_content = self._generate_success_email_text(file_id)
        
        for recipient in recipient_emails:
            try:
                message = {
                    "senderAddress": self.sender_email,
                    "recipients": {
                        "to": [{"address": recipient}]
                    },
                    "content": {
                        "subject": subject,
                        "html": html_content,
                        "plainText": text_content
                    }
                }
                
                poller = self.email_client.begin_send(message)
                result = poller.result()
                
                notification = EmailNotification(
                    notification_id=f"success_{int(datetime.now(timezone.utc).timestamp())}_{recipient.replace('@', '_')}",
                    file_id=file_id,
                    validation_id="success",
                    recipient_email=recipient,
                    subject=subject,
                    sent_timestamp=datetime.now(timezone.utc),
                    delivery_status="sent"
                )
                notifications.append(notification)
                
                logger.info(f"Success notification sent to {recipient}: {result.message_id}")
                
            except Exception as e:
                logger.error(f"Failed to send success notification to {recipient}: {str(e)}")
        
        return notifications
    
    def _generate_success_email_html(self, file_id: str) -> str:
        """Generate HTML content for success notification"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ color: #2e7d32; }}
                .success {{ background-color: #e8f5e8; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="header">Data Validation Successful</h1>
                <div class="success">
                    <p>✅ Your Excel file has passed all validation checks!</p>
                    <p><strong>File ID:</strong> {file_id}</p>
                    <p><strong>Validation Date (UTC):</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}</p>
                </div>
                <p>Your data has been successfully processed and is ready for use.</p>
            </div>
        </body>
        </html>
        """
    
    def _generate_success_email_text(self, file_id: str) -> str:
        """Generate text content for success notification"""
        return f"""
Data Validation Successful

✅ Your Excel file has passed all validation checks!

File ID: {file_id}
Validation Date (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}

Your data has been successfully processed and is ready for use.
        """
