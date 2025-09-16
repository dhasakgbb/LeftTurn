# LeftTurn Agents and Data Validation (Azure)

![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![License: MIT](https://img.shields.io/badge/License-MIT-green)

LeftTurn delivers a production‑ready logistics intelligence stack that reconciles carrier contracts, invoices, tracking and ERP data. It exposes curated tables for analytics and powers chat agents in Microsoft 365 with retrieval‑augmented answers backed by verifiable evidence.

Use this repository to run the full solution locally, validate changes with automated tests, and deploy the Azure Function app plus Fabric/Search assets into your tenant.

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [End-to-End Flow](#end-to-end-flow)
- [Fabric Backbone and Data Model](#fabric-backbone-and-data-model)
- [Development Setup](#development-setup)
- [Testing & QA](#testing--qa)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Key Endpoints](#key-endpoints)
- [Operations and Governance](#operations-and-governance)
- [Roadmap](#roadmap)
- [Infrastructure-as-Code](#infrastructure-as-code)
- [Teams Integration](#teams-integration)
- [Claims Agent (Logistics Value Add)](#claims-agent-logistics-value-add)
- [License](#license)

## Features

- Unified chat gateway for domain, carrier, customer, and claims agents
- Orchestrator routes between Fabric SQL, Azure AI Search, and Microsoft Graph
- Excel ingestion and validation pipeline with change tracking and email notifications
- All services run in your Microsoft 365/Azure tenant and integrate with Power BI

## Architecture Overview
- **Azure Functions**: Serverless app exposing all endpoints.
- **AI Foundry Orchestrator**: `src/agents/orchestrator.py` selects tools per request.
- **Structured Data Agent**: `src/agents/structured_data_agent.py` executes SQL via the Fabric connector client in `src/services/fabric_data_agent.py`.
- **Unstructured Data Agent**: `src/agents/unstructured_data_agent.py` queries Azure AI Search via `src/services/search_service.py`.
- **Microsoft Graph**: Optional enrichment via `src/services/graph_service.py`.
- **Excel Validation Flow**: `src/functions/excel_processor`, `src/services/{excel,validation,email,storage}_service.py`.
- **Storage**: Azure Blob Storage (files) + Cosmos DB (metadata, validations, notifications, tracking).
- **Notifications**: Azure Communication Services (Email).
- **API Management / EasyAuth**: Optional JWT enforcement and rate limiting in front of the Function App.

## End‑to‑End Flow

1. User asks a question to an agent via the HTTP Agent Gateway (publishable via Copilot Studio/Teams).
2. The Orchestrator decides whether to use Fabric SQL (numbers) or AI Search (clauses). Microsoft Graph can be used when queries mention calendar/email/files.
3. The answer returns with grounded evidence (rows or passages).
4. If the query touches curated tables and `PBI_*` variables are configured, the response also includes a Power BI deep link for deeper analysis.
5. Separately, Excel files are ingested, validated, and persisted. Failed validations trigger email notifications and change tracking; corrections can be verified with a follow‑up call.

## Fabric Backbone and Data Model

- Lakehouse medallion layout: landing → standardized → curated.
- Canonical logistics model (suggested): `FactShipment`, `FactInvoice`, `DimCarrier`, `DimServiceLevel`, `DimSKU`, `DimZone`, `DimCustomer` and contract‑derived tables `RateSheet`, `ZoneMatrix`, `AccessorialRule`, `FuelTable`, `Exceptions`.
- Curated Delta tables power Power BI dashboards and agent queries; connect with the Fabric SQL endpoint set in `FABRIC_ENDPOINT`.

## Development Setup

### Prerequisites
- Python 3.9+
- Azure CLI
- Azure Functions Core Tools v4
- Azure subscription with: Storage, Cosmos DB, Communication Services, AI Search, Microsoft Fabric (for SQL endpoint), and optional Microsoft Graph app registration.

### Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

### Create your `.env`

Copy `.env.example` to `.env` and configure your Azure settings:

```bash
cp .env.example .env
```

Populate Fabric/Search/Graph/Storage secrets before calling any cloud resources. The Functions app also reads settings from `local.settings.json`; keep it in sync with `.env` when developing locally.

### Run the Functions host

```bash
func start
```

### Kickoff Tasks

- Seed Azure AI Search assets (requires `SEARCH_SERVICE` and `SEARCH_ADMIN_KEY`):

```bash
make seed-search
```

- Register curated Fabric SQL views (requires `FABRIC_ODBC_CONNECTION_STRING` and `pyodbc`):

```bash
make register-views
```

## Testing & QA

- **Lint**: `python3 -m flake8`
- **Unit tests**: `python3 -m pytest -q`
- **Combined pre-flight**: run both commands before opening a PR; CI expects them to pass.

Pytest currently emits a LibreSSL warning on macOS because the system Python ships with LibreSSL 2.8.3; it is safe to ignore, but if you upgrade to an OpenSSL-backed Python (e.g., via `pyenv`) the warning disappears.

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

See `AGENTS.md` for contributor guidance. Additional documentation lives under `docs/` (architecture, Teams integration, marketplace guidance, OpenAPI specs) with the main diagram at `docs/diagrams/leftturn-arch.mmd`.
```

## Configuration

| Variable | Description |
| --- | --- |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Storage connection string |
| `AZURE_COSMOSDB_CONNECTION_STRING` | Cosmos DB connection string |
| `AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING` | Communication Services connection string |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_MODEL` | Model name (e.g., gpt-4.1) |
| `AZURE_OPENAI_EMBED_DEPLOYMENT` | Embedding deployment name used by the Search skillset |
| `FABRIC_ENDPOINT` | Microsoft Fabric SQL endpoint |
| `FABRIC_TOKEN` | OAuth bearer token for Fabric |
| `SEARCH_ENDPOINT` | Azure AI Search endpoint |
| `SEARCH_INDEX` | Search index for contracts/guides |
| `SEARCH_API_KEY` | Azure AI Search key |
| `GRAPH_TOKEN` | Optional Microsoft Graph bearer token |
| `GRAPH_ENDPOINT` | Optional Graph base URL (default `https://graph.microsoft.com/v1.0`) |
| `SUPPORTED_FILE_TYPES` | Allowed file extensions (default `xlsx`) |
| `MAX_FILE_SIZE_MB` | Maximum upload size for `/api/process` (default `50`) |
| `DEFAULT_SENDER_EMAIL` | Sender address for notifications (default `noreply@yourdomain.com`) |
| `REMINDER_DAYS_OLD` | Days after which failed validations receive a reminder (default `3`) |
| `REMINDER_MAX_ITEMS` | Maximum reminders processed per run (default `100`) |
| `PBI_WORKSPACE_ID` / `PBI_REPORT_ID` | Include a `powerBiLink` in responses when set |
| `SEARCH_DS_CONNECTION_STRING` / `SEARCH_DS_CONTAINER` | Storage settings for `infra/scripts/seed_search.sh` (defaults: storage connection string and `contracts`) |

Notes:

- Only `.xlsx` is supported by default; `.xls` is disabled because the reader uses `openpyxl`.
- Requests exceeding `MAX_FILE_SIZE_MB` return HTTP 413 (Payload Too Large).
- Timestamps in responses, storage records, and emails are UTC.

## Key Endpoints

- `POST /api/agents/{agent}/ask` — chat to `domain|carrier|customer|claims` agents with `{ "query": "..." }`. Returns `{ tool, result, citations }` and optional `powerBiLink`. Add `?format=card` or `{ "format": "card" }` to receive an Adaptive Card (for Teams).
- `POST /api/teams/ask` — Teams relay that always returns an Adaptive Card for `{ query, agent }` using the orchestrator’s `handle_with_citations` output.
- `POST /api/process` — upload and validate an Excel file (base64 payload).
- `GET /api/status/{file_id}` — check processing and latest validation.
- `POST /api/notify` — send email notifications for a validation.
- `GET /api/notify/status/{notification_id}` — delivery/status of a notification backed by Cosmos DB.
- `POST /api/verify` — verify corrections with an updated file.
- `GET /api/history/{file_id}` — change tracking history.

An OpenAPI definition for the agent gateway is available at `docs/openapi/agent-gateway.yaml`.

### Key Environment Variables (additions)

- Fabric
  - `FABRIC_SQL_MODE`: `http|odbc` (default `http`)
  - `FABRIC_ODBC_CONNECTION_STRING`: optional ODBC connection string
- Search
  - `SEARCH_API_VERSION`: API version for Search REST calls (default `2021-04-30-Preview`)
  - `SEARCH_USE_SEMANTIC`: `true|false` to enable semantic ranking; or `auto` (heuristic)
  - `SEARCH_HYBRID`: `true|false` to include vector clause when embeddings available
  - `SEARCH_VECTOR_FIELD`: Name of the vector field in your index (default `pageEmbedding`)
  - `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBED_DEPLOYMENT`: for embeddings when `SEARCH_HYBRID=true`
- Power BI
  - `PBI_WORKSPACE_ID` / `PBI_REPORT_ID`: enables `powerBiLink` in responses
  - `PBI_DATE_COLUMN`: report column used for date filtering in deeplinks (default `vw_Variance/ShipDate`)
  - `AGENT_MAX_ROWS`: cap rows returned in agent results (optional)
  - `AGENT_MAX_CITATIONS`: cap number of citations and unstructured passages (default 5)

### Timeouts

- `FABRIC_TIMEOUT`: seconds for Fabric HTTP calls (default 10)
- `SEARCH_TIMEOUT`: seconds for Search calls (default 10)
- `GRAPH_TIMEOUT`: seconds for Graph calls (default 10)

### New SQL Templates (curated views only)

- `variance_by_sku`: Variance by SKU
- `variance_by_carrier_service`: Variance by Carrier x ServiceLevel
- `variance_trend_by_carrier`: Monthly variance trend per Carrier
- `variance_trend_by_sku`: Monthly variance trend per SKU (optional `@sku`)

All templates are parameterized and must only reference curated views (`vw_*`).

## Operations and Governance

- Lineage and audit: Validation results, notifications, and change tracking are recorded in Cosmos DB.
- Least privilege: Scope tokens/keys to read‑only Fabric SQL and read‑only Search.
- Guardrails: Orchestrator prefers structured data for numeric claims; each answer payload contains the raw results returned by tools for downstream rendering/citations.
- EasyAuth/APIM: Enforce Azure AD JWTs and rate‑limit calls at the edge when enabled in Bicep.

## Roadmap

- Document Intelligence: parse carrier PDFs into structured tables feeding Fabric.
- Power BI: connect to curated Delta tables for dashboards; link BI bookmarks from agent responses.

## Infrastructure-as-Code

- Bicep templates: `infra/bicep/main.bicep` (RG scope). Creates Storage, Cosmos (serverless), Communication Services, Cognitive Services (Form Recognizer), Azure AI Search, Function App (Linux/Python). Outputs resource names.
- EasyAuth/APIM: Bicep supports enabling App Service Authentication (`enableEasyAuth`) and optionally creates API Management (`enableApim`) for JWT enforcement and rate limiting. APIM policy templates live in `infra/apim/policies`.
- Terraform: `infra/terraform/` equivalent provisioning using `azurerm` and `azapi` (preview Fabric workspace).
- Search data-plane seeding: `infra/scripts/seed_search.sh` creates a Blob data source, PII‑redacting skillset (with optional Azure OpenAI embeddings), the `contracts` index, and a scheduled indexer.
- Fabric SQL views: `fabric/sql/create_views_carrier.sql` seeds curated views.
- Sample notebooks: `notebooks/*.ipynb` ready to import into Fabric for ERP, carrier structured, and contracts processing.

## Teams Integration
- Use Copilot Studio (org agents) or a native Teams App (Bot + Message Extension).
- Native manifest starter: `teams/manifest/manifest.dev.json`.
- Adaptive Card builder: `src/utils/cards.py` (adds an “Open in Power BI” button when configured).
- See `docs/teams-integration.md` for step-by-step instructions.

## Claims Agent (Logistics Value Add)
- New persona `claims` focuses on disputes/claims workflows (e.g., SLA breaches, overbilling).
- Typical actions: “Create dispute packet for invoice 123”, “Summarize evidence for Carrier X Q2”, “Status of claim 456”.
- Pattern: Structured facts from Fabric (variance, shipments) + contract clauses from Search; package an evidence bundle linking both.
- Integrations: TMS/WMS (status events), EDI 210/214, SharePoint/OneDrive for packet storage, ServiceNow/Jira for ticketing, Outlook for templated emails.

## Licensing

1. Obtain a license key from LeftTurn.
2. Set `LEFTTURN_LICENSE_KEY` before running the app:

```bash
export LEFTTURN_LICENSE_KEY=YOUR_KEY
```

The package validates the key at startup using a hashed comparison.
Build an obfuscated binary for distribution via PyInstaller:

```bash
./build.sh
```

## License

MIT License
