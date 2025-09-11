Teams Integration Guide

Overview
- Integrates LeftTurn agents with Microsoft Teams via Copilot Studio Actions or an optional custom Teams app.
- Endpoints are provided by Azure Functions. EasyAuth (AAD) protects the APIs.

Endpoints
- POST /api/agents/{agent}/ask  — agent = domain|carrier|customer|claims
  - Body: { "query": "text", "format": "card" }
  - Returns an Adaptive Card when format=card; otherwise JSON payload with evidence and optional Power BI deeplink.
- POST /api/teams/ask — convenience wrapper that always returns a card
- Excel intake: POST /api/process, GET /api/status/{file_id}, POST /api/verify, GET /api/history/{file_id}, POST /api/compare

Auth
- Enable App Service Authentication (EasyAuth) in the Function App.
- Copilot Studio uses OAuth 2.0 to obtain a user token; EasyAuth validates it.
- Delegated Graph access: if EasyAuth is enabled with user tokens, the gateway reads the header `X-MS-TOKEN-AAD-ACCESS-TOKEN` and passes it to Microsoft Graph (see src/functions/agent_gateway/__init__.py).

Copilot Studio wiring
1) Create an agent and add an Action that calls POST /api/agents/{agent}/ask.
2) Provide parameters: path {agent}, body {query, format=card}.
3) Configure OAuth (AAD) to your Function App resource (client ID / Application ID URI); publish to your tenant.

Optional custom Teams app
- A sample Teams manifest is under `teams/manifest/manifest.dev.json`. It requires a Bot Framework bot ID and backend if you choose this route.

OpenAPI for Actions
- Import `docs/openapi/leftturn.yaml` into Copilot Studio to scaffold Actions quickly.

