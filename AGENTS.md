# AGENTS.md

## Mission
Implement a Microsoft Fabric–based “LeftTurn-style” logistics intelligence stack that reconciles carrier contracts, invoices, tracking, and ERP data; exposes curated tables for analytics; and powers chat agents in M365 (Teams/Copilot) with retrieval over contracts and SQL over curated data.

## Hard Constraints
- Use Microsoft Fabric (Lakehouse + Warehouse/SQL endpoint) as the analytics backbone.
- Use Azure AI Search for retrieval and Azure Document Intelligence (Form Recognizer) for parsing PDFs of carrier agreements/service guides.
- Surface dashboards in Power BI; all numeric claims must be backed by curated tables.
- Agents and APIs are read-only against production sources. Return evidence (rows/passages) for every numeric claim.

## Repo Map (this project)
- `src/agents/` — orchestrator and chat-facing agents (Domain/Carrier/Customer Ops)
- `src/services/` — Fabric SQL client, AI Search client, Graph client, Excel/Email/Storage/Validation services
- `src/functions/` — Azure Functions blueprints (agent gateway, excel processing, validation, email, change-tracking)
- `fabric/sql/` — curated views to register in Fabric (e.g., `vw_Variance`)
- `notebooks/` — Fabric notebooks for ERP, Carrier (structured), and contract parsing (unstructured)
- `infra/` — IaC
  - `infra/bicep/` Bicep templates
  - `infra/terraform/` Terraform alternative
  - `infra/search/` Search index + skillset payloads
  - `infra/scripts/seed_search.sh` Search seeding helper (uses `az rest`)
- `tests/` — unit tests for agents/services
- `docs/` — architecture docs and diagrams
  - `docs/leftturn-architecture.md` — authoritative brief this agent should read first
  - `docs/diagrams/leftturn-arch.mmd` — Mermaid diagram

## Build & Run
- Install deps: `pip install -r requirements.txt`
- Lint: `flake8`
- Tests: `pytest -q`
- Local Functions host: `func start`

Optional tools (if available):
- Ruff: `ruff check . && ruff format --check .`
- Type check (if configured): `pyright`

## Environment
Set env vars (see `.env.example` and `README.md`). Critical for running end-to-end:
- Storage/Cosmos/CommSvc: `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_COSMOSDB_CONNECTION_STRING`, `AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING`
- OpenAI (optional AI suggestions in validation): `AZURE_OPENAI_*`
- Agents & data tools: `FABRIC_ENDPOINT`, `FABRIC_TOKEN`, `SEARCH_ENDPOINT`, `SEARCH_INDEX`, `SEARCH_API_KEY`, `GRAPH_TOKEN`
- Reminders: `REMINDER_DAYS_OLD`, `REMINDER_MAX_ITEMS`

Cloud runner (CI/Codex) bootstrap scripts:
- `tools/setup_cloud.sh` — installs Python deps
- `tools/run_tests.sh` — runs lint and tests

## How To Work (Agent Playbook)
1. Read `docs/leftturn-architecture.md` and this file.
2. For structured questions: generate parameterized SQL only against curated views (see `fabric/sql/`).
3. For unstructured questions: use `src/services/search_service.py` to query Azure AI Search; include citations (file, page, clause id when available).
4. Prefer small, testable changes; keep endpoints and models backward compatible.
5. Every change must pass lint and tests. Update docs when behavior or contracts change.

## Data Model (sketch)
- Facts: `FactShipment`, `FactInvoice`, `RatingOutput`, `Variance`
- Dims: `DimCarrier`, `DimServiceLevel`, `DimZone`, `DimSKU`, `DimCustomer`, `DimAccessorial`
- Contract-derived: `RateSheet`, `ZoneMatrix`, `FuelTable`, `Exceptions`

## Security & Privacy
- Never print secrets. Use env vars and Azure-managed identities where possible.
- Agents and APIs are read-only to data estate.
- Prefer hybrid retrieval; avoid long prompts with sensitive data. Redact PII in Search skillset.

## Verification Steps (always run locally/CI)
- `flake8`
- `pytest -q`
- For notebooks: (optional) execute on sample data to ensure row counts and invariants.

## PR Guidelines
- Title: `[component]: concise change`
- Include What/Why, affected tables, lineage/citations, and sample queries or prompts.
- Add/modify tests alongside code. No green tests ⇒ no merge.

## Anti-goals
- Do not introduce non-Fabric warehouses.
- Do not bypass curated views with ad-hoc SQL in services.

## Helpful Entry Tasks
- Register `fabric/sql/create_views_carrier.sql` in your Fabric workspace.
- Run `infra/scripts/seed_search.sh` to create the `contracts` index and skillset.
- Extend `src/functions/agent_gateway` to add more domains or richer payloads as needed.

## References
- High-level architecture: `docs/leftturn-architecture.md`
- Mermaid diagram: `docs/diagrams/leftturn-arch.mmd`
