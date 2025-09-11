# LeftTurn Agents and Data Validation (Azure)

This repository delivers a production‑ready, end‑to‑end implementation that maps to the architecture described in the prompt:

- Chat‑facing LeftTurn agents (Domain/Carrier/Customer Ops) behind a single HTTP gateway
- An Orchestrator that routes between Structured (Fabric) and Unstructured (Search) tools, with optional Microsoft Graph lookups
- A robust Excel ingestion and validation flow with notifications, change tracking, and storage

All components run inside your Microsoft 365/Azure tenant and integrate with Microsoft Fabric, Azure AI Search, Document Intelligence (optional), and Power BI.

## Architecture

- **Azure Functions**: Serverless app exposing all endpoints.
- **AI Foundry Orchestrator**: `src/agents/orchestrator.py` selects tools per request.
- **Structured Data Agent**: `src/agents/structured_data_agent.py` executes SQL via the Fabric connector client in `src/services/fabric_data_agent.py`.
- **Unstructured Data Agent**: `src/agents/unstructured_data_agent.py` queries Azure AI Search via `src/services/search_service.py`.
- **Microsoft Graph**: Optional enrichment via `src/services/graph_service.py`.
- **Excel Validation Flow**: `src/functions/excel_processor`, `src/services/{excel,validation,email,storage}_service.py`.
- **Storage**: Azure Blob Storage (files) + Cosmos DB (metadata, validations, notifications, tracking).
- **Notifications**: Azure Communication Services (Email).

## End‑to‑End Flow

1. User asks a question to an agent via the HTTP Agent Gateway (publishable via Copilot Studio/Teams).
2. The Orchestrator decides whether to use Fabric SQL (numbers) or AI Search (clauses). Microsoft Graph can be used when queries mention calendar/email/files.
3. The answer returns with grounded evidence (rows or passages).
4. Separately, Excel files are ingested, validated, and persisted. Failed validations trigger email notifications and change tracking; corrections can be verified with a follow‑up call.

## Development Setup

### Prerequisites
- Python 3.9+
- Azure CLI
- Azure Functions Core Tools v4
- Azure subscription with: Storage, Cosmos DB, Communication Services, AI Search, Microsoft Fabric (for SQL endpoint), and optional Microsoft Graph app registration.

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Copy `.env.example` to `.env` and configure your Azure settings:

```bash
cp .env.example .env
```

### Running Locally

```bash
func start
```

## Deployment

Deploy to Azure using the provided deployment script:

```bash
./deploy.sh
```

## Project Structure

```
├── .github/
│   └── copilot-instructions.md
├── src/
│   ├── functions/
│   │   ├── excel_processor/
│   │   ├── data_validator/
│   │   ├── email_sender/
│   │   ├── change_tracker/
│   │   └── agent_gateway/        # Chat gateway for Domain/Carrier/Customer agents
│   ├── services/
│   │   ├── excel_service.py
│   │   ├── validation_service.py
│   │   ├── email_service.py
│   │   └── storage_service.py
│   ├── models/
│   │   └── validation_models.py
│   └── utils/
│       └── helpers.py
├── tests/
├── requirements.txt
├── host.json
├── local.settings.json
├── function_app.py
├── .env.example
└── README.md
```

## Configuration

The agent requires the following environment variables:

- `AZURE_STORAGE_CONNECTION_STRING`: Connection string for Azure Storage
- `AZURE_COSMOSDB_CONNECTION_STRING`: Connection string for Cosmos DB
- `AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING`: Connection string for Communication Services
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint
- `AZURE_OPENAI_API_KEY`: Azure OpenAI API key
- `AZURE_OPENAI_MODEL`: Model name (e.g., gpt-4.1)

Agents and data tools:

- `FABRIC_ENDPOINT`: Base URL for Microsoft Fabric SQL endpoint (e.g., `https://<workspace>.<region>.fabric.microsoft.com`)
- `FABRIC_TOKEN`: OAuth bearer token for Fabric endpoint (Entra ID).
- `SEARCH_ENDPOINT`: Azure AI Search endpoint (e.g., `https://<name>.search.windows.net`)
- `SEARCH_INDEX`: Search index name for contracts/guides.
- `SEARCH_API_KEY`: Admin or query key for the Search service.
- `GRAPH_TOKEN`: Optional bearer token for Microsoft Graph (or use API Management/proxy).
- `GRAPH_ENDPOINT`: Optional Graph base URL (default `https://graph.microsoft.com/v1.0`).

Optional configuration (with defaults):

- `SUPPORTED_FILE_TYPES`: Comma-separated list of allowed file extensions (without the dot). Default: `xlsx`.
- `MAX_FILE_SIZE_MB`: Maximum upload size in megabytes for `/api/process`. Default: `50`.
- `DEFAULT_SENDER_EMAIL`: Sender address for email notifications. Default: `noreply@yourdomain.com`.
- `REMINDER_DAYS_OLD`: Days after which failed validations receive a reminder. Default: `3`.
- `REMINDER_MAX_ITEMS`: Safety cap for reminders processed per run. Default: `100`.

Notes:

- Only `.xlsx` is supported by default. Legacy `.xls` is not enabled because the configured reader uses `openpyxl`.
- Requests exceeding `MAX_FILE_SIZE_MB` return HTTP 413 (Payload Too Large).
- Timestamps in responses, storage records, and emails are UTC.

## Key Endpoints

- `POST /api/agents/{agent}/ask` — chat to `domain|carrier|customer` agents with `{ "query": "..." }`.
- `POST /api/process` — upload and validate an Excel file (base64 payload).
- `GET /api/status/{file_id}` — check processing and latest validation.
- `POST /api/notify` — send email notifications for a validation.
- `GET /api/notify/status/{notification_id}` — delivery/status of a notification backed by Cosmos DB.
- `POST /api/verify` — verify corrections with an updated file.
- `GET /api/history/{file_id}` — change tracking history.

## Operations and Governance

- Lineage and audit: Validation results, notifications, and change tracking are recorded in Cosmos DB.
- Least privilege: Scope tokens/keys to read‑only Fabric SQL and read‑only Search.
- Guardrails: Orchestrator prefers structured data for numeric claims; each answer payload contains the raw results returned by tools for downstream rendering/citations.

## Next Integrations

- Document Intelligence: parse carrier PDFs into structured tables feeding Fabric.
- Power BI: connect to curated Delta tables for dashboards; link BI bookmarks from agent responses.

## License

MIT License
