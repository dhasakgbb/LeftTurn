# Teams Integration

This solution exposes a single Agent Gateway endpoint that can be surfaced in Microsoft Teams in two primary ways:

- Copilot Studio (recommended for fastest path): publish Domain/Carrier/Customer Ops agents with Actions that call our HTTP endpoints.
- Native Teams app (Bot + Message Extension): use a Bot Framework bot with a compose extension that calls the gateway and renders Adaptive Cards.

## 1) Copilot Studio (Org agents)
- Import an OpenAPI definition that covers `POST /api/agents/{agent}/ask`.
- Create three copilots (Domain, Carrier, Customer Ops) and add an Action per copilot that pins the agent in the path.
- Authentication: Entra ID; configure the Function App with EasyAuth (AAD) or front with APIM.
- Output: set response parsing to display the returned `citations` and provide the `powerBiLink`.

## 2) Native Teams App (Bot + ME)
- Register a Bot (AAD app) and create a Teams App manifest (see `teams/manifest/manifest.dev.json`).
- Add a compose extension command `ask` that posts the user query to `/api/agents/{agent}/ask?format=card`.
- The gateway returns an Adaptive Card; see `teams/cards/answerCard.sample.json` and the runtime card builder at `src/utils/cards.py`.

### Endpoint contract for Teams
```
POST /api/agents/{agent}/ask
Body: { "query": "...", "format": "card" }
Return: Adaptive Card JSON (if format=card) or JSON payload with { tool, result, citations, powerBiLink }
```

### Auth & Rate Limiting
- Enable EasyAuth via Bicep (`enableEasyAuth=true`) and require AAD tokens from the bot/calling app.
- Optional: place API Management in front (`enableApim=true`) and apply JWT + rate-limit policy from `infra/apim/policies/global.xml`.

### Deep links to Power BI
- Set `PBI_WORKSPACE_ID`, `PBI_REPORT_ID` in Function App settings.
- The Agent Gateway includes `powerBiLink` for structured answers; the Adaptive Card adds an OpenUrl button automatically.

### SSO
- Use Teams SSO to obtain an AAD token and exchange it for a backend token (on-behalf-of) when you move to Managed Identity for downstream services.

### Developer Loop
- Use Teams Toolkit or App Studio to load `teams/manifest/manifest.dev.json`.
- Point `validDomains` to your Function App host.
- Validate the compose extension by sending prompts like:
  - “Are we overbilled by Carrier X for SKU 812 this quarter?”
  - “Find clause 7.4 for Carrier X”

## Troubleshooting
- If cards don’t render: ensure `format=card` is sent and the card validates at https://adaptivecards.io/designer/.
- If requests 401: verify EasyAuth audience and your bot AAD app’s token scopes.
- If Search is empty: seed index via `infra/scripts/seed_search.sh`.
