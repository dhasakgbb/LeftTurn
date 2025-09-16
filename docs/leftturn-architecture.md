# LeftTurn-Style Architecture (Fabric + Agents)

This document captures the end-to-end design and value proposition for a logistics intelligence stack that reconciles what the contract says with what the invoice shows and what the ERP ordered/shipped. It aligns with the repo’s implementation.

## Setting
Everything runs in the customer’s Microsoft 365/Azure tenant. Heavy data and AI plumbing runs in Microsoft Fabric; users interact in M365 Copilot Chat or Microsoft Teams via org-published agents.

## Cast of Characters
- LeftTurn Agents (org store): Domain, Carrier, Customer Operations
- AI Foundry/Orchestrator: routes requests and invokes tools
- Tooling agents: Structured Data (SQL/Fabric) and Unstructured Data (contracts/docs via Azure AI Search + Document Intelligence)
- APIs: Fabric Data Agent (via Fabric connector) and Microsoft Graph (optional)
- Data estate: Fabric Lakehouse Landing Zone with domains: Carrier and ERP feeding curated tables
- Notebooks: three pipelines — unstructured carrier agreements & service guides; structured carrier data (billing/tracking/rating); structured ERP data (LOB, SKU, orders)
- AI Search & Doc Intelligence: indexing and document parsing/OCR with PII redaction
- Visualization: Power BI reports inside Fabric
- Storage: Azure Storage landing for structured streams

## Plot (request → answer)
1. A user asks a question in Copilot/Teams (e.g., “Are we overbilled by Carrier X on 2‑day air for SKU 812 this quarter?”).
2. A LeftTurn Agent receives the prompt and routes to the Orchestrator, which decides which tools/agents to invoke.
3. Structured needs → Structured Data Agent runs parameterized SQL against curated tables via Fabric Data Agent.
4. Unstructured needs → Unstructured Data Agent uses Document Intelligence to parse PDFs and Azure AI Search to retrieve relevant passages.
5. Optional M365 context via Microsoft Graph.
6. Orchestrator blends table results with retrieved contract text and returns a grounded answer with citations.
7. The same curated data powers Power BI dashboards for repeatable analysis.

## Data Lifecycle
- Ingestion: notebooks bring in ERP data, carrier invoices/tracking, and PDFs of agreements/service guides.
- Parsing: Document Intelligence extracts entities (rates, zones, surcharges, minimums) into structured tables.
- Indexing: Azure AI Search indexes cleaned text and vector embeddings for hybrid retrieval.
- Curation: Fabric Delta tables become the “single source of truth” used by BI, search, and agents.
- Visualization: Power BI shows cost, exceptions, SLA adherence, and variance between “should pay” and “did pay.”

## What LeftTurn Delivers
- Prebuilt agents your users can chat with in M365
- Data notebooks for contracts (unstructured), carrier (structured), and ERP (structured)
- Canonical data model reconciling contracts ↔ invoices ↔ ERP
- Search + document understanding tuned for logistics contracts
- End-user value: cost control, faster answers, and an auditable chain from clause → rate → invoice variance → dashboard

## This Repo’s Mapping
- Orchestrator & agents: `src/agents/`
- Tool clients: `src/services/` (Fabric, Search, Graph)
- HTTP endpoints: `src/functions/` (agent gateway, processing, validation, email, tracking, Teams relay)
- Curated SQL: `fabric/sql/`
- Notebooks: `notebooks/`
- Infra: `infra/`

Each HTTP entry point is defined as an Azure Functions blueprint (`agent_gateway`, `teams_relay`, `excel_processor`, `data_validator`, `change_tracker`, `email_sender`). The gateway exposes `/api/agents/{agent}/ask` for Copilot Studio, while the relay returns a Teams-ready Adaptive Card from `/api/teams/ask`.

## Guardrails
- Read-only data access for agents; use parameterized SQL against approved views.
- Evidence with every answer: return rows/passages and citations (file/page/clause or view/sql).
- Row-level security and sensitivity labels in Fabric where needed; PII redaction in Search skillset.

Refer to the Mermaid diagram for a compact view.
