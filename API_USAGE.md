# API Usage Examples

This guide shows how to call the Azure Functions endpoints that power the LeftTurn agents, Excel validation pipeline, and notification services. All routes are served under the `/api` prefix of your Function App.

## Base URL

```
https://your-function-app.azurewebsites.net/api
```

## Authentication

The Functions app can be fronted by EasyAuth (Azure AD), API Management, or classic function keys. Include whatever credential your deployment requires: append `?code=<function-key>` to the URL or send it as an `x-functions-key` header if you rely on function keys.

---

## Agent Endpoints

### Ask an Agent

`POST /agents/{agent}/ask`

Send a query to a chat agent (`domain`, `carrier`, `customer`, or `claims`). By default the API returns structured JSON containing the orchestrator decision, the raw tool output, and citations. Specify `"format": "card"` (or `?format=card`) to receive an Adaptive Card payload for Teams.

```json
{
  "query": "Are we overbilled by Carrier X for SKU 812 this quarter?",
  "format": "json"
}
```

```json
{
  "agent": "CarrierAgent",
  "tool": "sql",
  "result": [
    { "carrier": "X", "overbilled": true, "variance": 1243.55 }
  ],
  "citations": [
    { "type": "table", "source": "fabric", "sql": "SELECT ...", "rows": 3 }
  ],
  "powerBiLink": "https://app.powerbi.com/groups/<ws>/reports/<rep>/ReportSection?..."
}
```

### Teams Relay

`POST /teams/ask`

Returns an Adaptive Card regardless of the requested format. Use this directly from a Teams bot or Copilot Studio Action.

```json
{
  "agent": "claims",
  "query": "Summarize claim 456 with latest evidence"
}
```

Response: Adaptive Card JSON body ready to post back to Teams.

---

## Excel Processing Pipeline

### 1. Process Excel File

`POST /process`

Upload a base64-encoded Excel workbook. The service stores the file, runs validations, and sends email notifications when configured.

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

### 2. Check Processing Status

`GET /status/{file_id}`

Returns the latest validation summary for a file.

```json
{
  "file_id": "excel_abc123_1638360000",
  "latest_validation_id": "val_excel_abc123_1638360000_1638360001",
  "status": "failed",
  "processed_rows": 100,
  "total_errors": 3,
  "total_warnings": 1,
  "last_updated": "2023-12-01T10:00:00.000Z"
}
```

### 3. Retrieve Change History

`GET /history/{file_id}`

Provides the change-tracking timeline, including hashes and notification timestamps.

```json
[
  {
    "tracking_id": "track_1700000000",
    "file_id": "excel_abc123_1638360000",
    "validation_id": "val_excel_abc123_1638360000_1638360001",
    "status": "failed",
    "file_hash": "abc123...",
    "timestamp": "2023-12-01T10:00:00.000Z"
  },
  {
    "tracking_id": "track_1700003600",
    "file_id": "excel_abc123_1638360000",
    "validation_id": "val_excel_def456_1638363600_1638363601",
    "status": "corrected",
    "file_hash": "def456...",
    "timestamp": "2023-12-01T11:00:00.000Z"
  }
]
```

### 4. Verify Updated Files

`POST /verify`

Re-run validations on a corrected workbook, update change tracking, and send notifications.

```json
{
  "original_file_id": "excel_abc123_1638360000",
  "updated_file_data": "base64_encoded_updated_file_content",
  "updated_filename": "employee_data_corrected.xlsx"
}
```

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

---

## Validation APIs

### Standalone Data Validation

`POST /validate`

Validate arbitrary JSON data in-memory (no storage writes).

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

### Create/Test Validation Rules

`POST /rules`

Quickly define a rule and optionally evaluate it against sample data before persisting.

```json
{
  "rule_name": "Email Validation",
  "rule_type": "format",
  "description": "Ensure emails match RFC pattern",
  "parameters": {
    "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
    "columns": ["email"]
  },
  "severity": "error",
  "test_data": [
    {"email": "john@example.com"},
    {"email": "invalid"}
  ]
}
```

```json
{
  "rule": {
    "rule_id": "custom_1700000000",
    "rule_name": "Email Validation",
    "severity": "error"
  },
  "test_summary": {
    "rows_evaluated": 2,
    "errors_found": 1,
    "sample_errors": [
      {
        "row": 2,
        "column": "email",
        "message": "Value does not match expected format"
      }
    ]
  }
}
```

---

## Notifications

### Send Notification

`POST /notify`

Dispatch failure, reminder, or success emails based on a validation id.

```json
{
  "validation_id": "val_excel_abc123_1638360000_1638360001",
  "recipient_emails": ["user@company.com", "admin@company.com"],
  "notification_type": "failure"
}
```

```json
{
  "validation_id": "val_excel_abc123_1638360000_1638360001",
  "notification_type": "failure",
  "notifications_sent": 2,
  "recipients": ["user@company.com", "admin@company.com"],
  "timestamp": "2023-12-01T10:10:00.000Z",
  "notification_ids": [
    "email_1638360600_user_company_com",
    "email_1638360600_admin_company_com"
  ]
}
```

### Get Notification Status

`GET /notify/status/{notification_id}`

Retrieve the delivery status stored in Cosmos DB.

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

---

## Health & Error Model

### Health Check

`GET /health`

Returns basic readiness information (also available at `/readiness`).

```json
{
  "status": "healthy",
  "service": "LeftTurn Agents"
}
```

### Standard Error Envelope

All endpoints return errors in a consistent shape:

```json
{
  "error": "BadRequest",
  "message": "Human readable error message",
  "details": "Technical details (optional)"
}
```

Common HTTP status codes: `200` (success), `400` (validation), `404` (missing resource), `429` (throttled by APIM/EasyAuth), `500` (unexpected error).

---

## Validation Rule Helper Reference

```json
{
  "rule_type": "format",
  "parameters": {
    "pattern": "regex_pattern",
    "columns": ["column1", "column2"]
  }
}

{
  "rule_type": "range",
  "parameters": {
    "min": 0,
    "max": 100,
    "columns": ["score", "percentage"]
  }
}

{
  "rule_type": "data_type",
  "parameters": {
    "expected_type": "int",
    "columns": ["age", "count"]
  }
}

{
  "rule_type": "custom",
  "parameters": {
    "required_columns": ["name", "email", "id"]
  }
}
```

### Encoding Files for Uploads

Excel files must be base64 encoded before calling `/process` or `/verify`:

```python
import base64

with open("file.xlsx", "rb") as handle:
    file_data = base64.b64encode(handle.read()).decode("utf-8")
```

```javascript
const reader = new FileReader();
reader.readAsDataURL(file);
reader.onload = () => {
  const base64Data = reader.result.split(",")[1];
  // Send base64Data in the API request
};
```
