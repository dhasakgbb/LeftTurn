This directory hosts the written guidance that accompanies the code. Use it alongside `AGENTS.md` when onboarding new engineers or preparing deployments.

## Overview

- `leftturn-architecture.md` — business context, component inventory, and data flow across Fabric, Search, Document Intelligence, Power BI, and the agents.
- `teams-integration.md` — wiring the Azure Functions endpoints into Copilot Studio/Teams, authentication choices, card guidance, and deployment checklist.
- `marketplace-deployment.md` — steps for packaging and publishing the managed application offer in Azure Marketplace.
- `openapi/leftturn.yaml` — canonical OpenAPI description for the agent gateway. `leftturn.generated.yaml` is produced by tooling when you inject your host/App ID URI.
- `diagrams/leftturn-arch.mmd` — Mermaid source for the high-level architecture diagram referenced in the architecture brief.
- `CONTRIBUTING.md` — commit message conventions and helper script for keeping GitHub folder descriptions useful.

Additional references:
- `API_USAGE.md` (repo root) — endpoint payload examples for the validation pipeline and chat gateway.
- `AGENTS.md` (repo root) — working agreements, constraints, and verification steps.
