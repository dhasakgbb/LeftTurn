from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ValidationStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    CORRECTED = "corrected"

class ValidationRule(BaseModel):
    """Model for validation rules"""
    rule_id: str
    rule_name: str
    description: str
    rule_type: str  # "data_type", "range", "format", "custom"
    parameters: Dict[str, Any]
    severity: str = "error"  # "error", "warning", "info"

class ValidationError(BaseModel):
    """Model for validation errors"""
    row: int
    column: str
    value: Any
    rule_id: str
    message: str
    severity: str
    suggested_correction: Optional[str] = None

class ExcelFileMetadata(BaseModel):
    """Model for Excel file metadata"""
    file_id: str
    filename: str
    upload_timestamp: datetime
    file_size: int
    sheet_names: List[str]
    total_rows: int
    total_columns: int
    uploaded_by: Optional[str] = None

class ValidationResult(BaseModel):
    """Model for validation results"""
    file_id: str
    validation_id: str
    status: ValidationStatus
    timestamp: datetime
    errors: List[ValidationError]
    warnings: List[ValidationError]
    total_errors: int
    total_warnings: int
    processed_rows: int
    email_sent: bool = False
    email_recipient: Optional[str] = None

class EmailNotification(BaseModel):
    """Model for email notifications"""
    notification_id: str
    file_id: str
    validation_id: str
    recipient_email: str
    subject: str
    sent_timestamp: datetime
    delivery_status: str = "pending"
    correction_deadline: Optional[datetime] = None

class ChangeTrackingRecord(BaseModel):
    """Model for tracking changes"""
    tracking_id: str
    file_id: str
    validation_id: str
    original_file_hash: str
    updated_file_hash: Optional[str] = None
    change_timestamp: Optional[datetime] = None
    change_description: Optional[str] = None
    verified: bool = False

class ProcessingRequest(BaseModel):
    """Model for processing requests"""
    request_id: str
    file_data: bytes
    filename: str
    validation_rules: List[ValidationRule]
    email_lookup_field: str = "email"  # Column name for email lookup
    requester_email: Optional[str] = None