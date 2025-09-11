# API Usage Examples

This document provides examples of how to use the Azure Excel Data Validation Agent API endpoints.

## Base URL

```
https://your-function-app.azurewebsites.net/api
```

## Authentication

The Function App can be configured with authentication keys. Include the function key in requests:

```
?code=your_function_key
```

## 1. Process Excel File

**Endpoint:** `POST /process`

**Description:** Upload and validate an Excel file with automatic email notifications.

**Request Body:**
```json
{
    "filename": "employee_data.xlsx",
    "file_data": "base64_encoded_file_content",
    "validation_rules": [
        {
            "rule_id": "email_check",
            "rule_name": "Email Validation",
            "description": "Validate email format",
            "rule_type": "format",
            "parameters": {
                "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                "columns": ["email"]
            },
            "severity": "error"
        }
    ],
    "email_lookup_field": "email",
    "requester_email": "admin@company.com"
}
```

**Response:**
```json
{
    "file_id": "excel_abc123_1638360000",
    "validation_id": "val_excel_abc123_1638360000_1638360001",
    "status": "failed",
    "total_errors": 3,
    "total_warnings": 1,
    "processed_rows": 100,
    "email_sent": true,
    "notifications_sent": 2,
    "timestamp": "2023-12-01T10:00:00.000Z",
    "errors": [
        {
            "row": 5,
            "column": "email",
            "value": "invalid-email",
            "message": "Value does not match expected format: Email Validation",
            "suggested_correction": "Use format: user@domain.com"
        }
    ]
}
```

## 2. Standalone Data Validation

**Endpoint:** `POST /validate`

**Description:** Validate JSON data without file upload.

**Request Body:**
```json
{
    "data": [
        {"name": "John Doe", "email": "john@company.com", "age": 30},
        {"name": "Jane Smith", "email": "invalid-email", "age": 25}
    ],
    "validation_rules": [
        {
            "rule_id": "required_fields",
            "rule_name": "Required Fields",
            "description": "Check required fields",
            "rule_type": "custom",
            "parameters": {
                "required_columns": ["name", "email"]
            },
            "severity": "error"
        }
    ],
    "data_id": "dataset_001"
}
```

**Response:**
```json
{
    "data_id": "dataset_001",
    "validation_id": "val_dataset_001_1638360002",
    "status": "failed",
    "total_errors": 1,
    "total_warnings": 0,
    "processed_rows": 2,
    "timestamp": "2023-12-01T10:05:00.000Z",
    "errors": [
        {
            "row": 2,
            "column": "email",
            "value": "invalid-email",
            "message": "Value does not match expected format: Email Format Validation",
            "severity": "error",
            "suggested_correction": "Use a valid email format like user@domain.com"
        }
    ]
}
```

## 3. Send Email Notification

**Endpoint:** `POST /notify`

**Description:** Send email notifications for validation results.

**Request Body:**
```json
{
    "validation_id": "val_excel_abc123_1638360000_1638360001",
    "recipient_emails": ["user@company.com", "admin@company.com"],
    "notification_type": "failure"
}
```

**Response:**
```json
{
    "validation_id": "val_excel_abc123_1638360000_1638360001",
    "notification_type": "failure",
    "notifications_sent": 2,
    "recipients": ["user@company.com", "admin@company.com"],
    "timestamp": "2023-12-01T10:10:00.000Z",
    "notification_ids": ["email_1638360600_user_company_com", "email_1638360600_admin_company_com"]
}
```

## 4. Verify File Changes

**Endpoint:** `POST /verify`

**Description:** Check if corrections have been made to a previously failed file.

**Request Body:**
```json
{
    "original_file_id": "excel_abc123_1638360000",
    "updated_file_data": "base64_encoded_updated_file_content",
    "updated_filename": "employee_data_corrected.xlsx"
}
```

**Response:**
```json
{
    "original_file_id": "excel_abc123_1638360000",
    "updated_file_id": "excel_def456_1638360600",
    "updated_validation_id": "val_excel_def456_1638360600_1638360601",
    "changes_successful": true,
    "change_description": "File updated and re-validated",
    "updated_file_hash": "def456...",
    "validation_status": "passed",
    "remaining_errors": 0,
    "remaining_warnings": 0,
    "timestamp": "2023-12-01T10:15:00.000Z",
    "success_notifications_sent": 2
}
```

## 5. Health Check

**Endpoint:** `GET /health`

**Description:** Check if the service is running.

**Response:**
```json
{
    "status": "healthy",
    "service": "Azure Excel Data Validation Agent"
}
```

## Error Responses

All endpoints return error responses in this format:

```json
{
    "error": "Error type",
    "message": "Human readable error message",
    "details": "Technical details (optional)"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid input)
- `404`: Not Found (resource not found)
- `500`: Internal Server Error

## Validation Rule Types

### Format Validation
```json
{
    "rule_type": "format",
    "parameters": {
        "pattern": "regex_pattern",
        "columns": ["column1", "column2"]
    }
}
```

### Range Validation
```json
{
    "rule_type": "range",
    "parameters": {
        "min": 0,
        "max": 100,
        "columns": ["score", "percentage"]
    }
}
```

### Data Type Validation
```json
{
    "rule_type": "data_type",
    "parameters": {
        "expected_type": "int",
        "columns": ["age", "count"]
    }
}
```

### Custom Validation
```json
{
    "rule_type": "custom",
    "parameters": {
        "required_columns": ["name", "email", "id"]
    }
}
```

## File Encoding

Excel files must be base64 encoded for API requests:

```python
import base64

with open('file.xlsx', 'rb') as file:
    file_data = base64.b64encode(file.read()).decode('utf-8')
```

```javascript
// In browser
const fileInput = document.getElementById('file-input');
const file = fileInput.files[0];
const reader = new FileReader();
reader.readAsDataURL(file);
reader.onload = function() {
    const base64Data = reader.result.split(',')[1];
    // Use base64Data in API request
};
```
## 0. Ask an Agent

Endpoint: `POST /agents/{agent}/ask`

Description: Send a query to a chat agent. `{agent}` is one of `domain`, `carrier`, or `customer`.

Request Body:
```json
{
  "query": "Are we overbilled by Carrier X for SKU 812 this quarter?"
}
```

Response:
```json
{
  "agent": "CarrierAgent",
  "result": [
    { "carrier": "X", "overbilled": true, "variance": 1243.55 }
  ]
}
```

### Get Notification Status

Endpoint: `GET /notify/status/{notification_id}`

Description: Retrieve delivery/status of a previously sent notification. The status is read from Cosmos DB records.

Response:
```json
{
  "notification_id": "email_1699999999_user_domain_com",
  "file_id": "excel_abc123_1638360000",
  "validation_id": "val_excel_abc123_1638360000_1638360001",
  "recipient_email": "user@domain.com",
  "status": "sent",
  "sent_timestamp": "2025-01-01T10:00:00Z",
  "correction_deadline": "2025-01-04T10:00:00Z"
}
```
