# AGENTS.md

## Mission
Implement a Microsoft Fabric–based “LeftTurn-style” logistics intelligence stack that reconciles carrier contracts, invoices, tracking, and ERP data; exposes curated tables for analytics; and powers chat agents in M365 (Teams/Copilot) with retrieval over contracts and SQL over curated data.

## Hard Constraints
- Use Microsoft Fabric (Lakehouse + Warehouse/SQL endpoint) as the analytics backbone.
- Use Azure AI Search for retrieval and Azure Document Intelligence (Form Recognizer) for parsing PDFs of carrier agreements/service guides.
- Surface dashboards in Power BI; all numeric claims must be backed by curated tables.
- Agents and APIs are read-only against production sources. Return evidence (rows/passages) for every numeric claim.

## Repo Map
- `src/agents/` — orchestrator and chat-facing agents (Domain/Carrier/Customer Ops)
- `src/services/` — Fabric SQL client, AI Search client, Graph client, Excel/Email/Storage/Validation services
- `src/functions/` — Azure Functions blueprints (agent gateway, excel processing, validation, email, change-tracking)
- `fabric/sql/` — curated views to register in Fabric (e.g., `vw_Variance`)
- `notebooks/` — Fabric notebooks for ERP, Carrier (structured), and contract parsing (unstructured)
- `infra/` — IaC (Bicep/Terraform), APIM policies, Search assets, seed scripts
- `docs/` — architecture brief and diagram
- `tests/` — unit tests for agents/services/utils

## Build & Run
- Install deps: `pip install -r requirements.txt`
- Lint: `flake8`
- Tests: `pytest -q`
- Local Functions host: `func start`
- Cloud helpers: `tools/setup_cloud.sh`, `tools/run_tests.sh`

## Environment
Set env vars (see `.env.example`):
- Storage/Cosmos/CommSvc: `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_COSMOSDB_CONNECTION_STRING`, `AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING`
- Agents & data tools: `FABRIC_ENDPOINT`, `FABRIC_TOKEN`, `SEARCH_ENDPOINT`, `SEARCH_INDEX`, `SEARCH_API_KEY`, `GRAPH_TOKEN`
- Optional embeddings in Search: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBED_DEPLOYMENT`
- Reminders: `REMINDER_DAYS_OLD`, `REMINDER_MAX_ITEMS`
- Power BI: `PBI_WORKSPACE_ID`, `PBI_REPORT_ID` (adds deep links to answers)
- APIM/EasyAuth (Bicep params): `enableEasyAuth`, `enableApim` (JWT + rate limiting)

## How To Work (Playbook)
1. Read `docs/leftturn-architecture.md` and this file.
2. Structured questions → `StructuredDataAgent` via Fabric views; use parameterized SQL.
3. Unstructured questions → `UnstructuredDataAgent` via AI Search; return citations (file, page, clause id if available).
4. Keep PRs small and testable; update docs with any contract changes.
5. Evidence-first: return tool results alongside any synthesized text.

## Verification Steps
- `flake8`
- `pytest -q`
- Optional: execute notebooks on sample data; confirm row counts and invariants.

## Anti-goals
- Non-Fabric warehouses; ad-hoc SQL bypassing curated views.
- Printing secrets or sending sensitive content outside tenant.

## Kickoff Tasks
- Register `fabric/sql/create_views_carrier.sql` in Fabric.
- `infra/scripts/seed_search.sh` with env set for Search and (optionally) Azure OpenAI embedding.
- Publish Functions; protect with EasyAuth/APIM if required.
