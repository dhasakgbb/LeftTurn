# Teams Integration Guide

## Overview
- Integrates LeftTurn agents with Microsoft Teams via Copilot Studio Actions or an optional custom Teams app.
- Endpoints are served by Azure Functions protected with App Service Authentication (EasyAuth).

## Prerequisites
- Function App deployed with endpoints above.
- Azure AD app registration with delegated Graph permissions and an exposed API scope matching the Function App.
- For Copilot Studio: set a redirect URI `https://global.consent.azure-apim.net/redirect` in the AAD app.
- Optional custom Teams app requires a Bot Framework bot ID.

## Endpoints
- **POST /api/agents/{agent}/ask** — `agent` is one of `domain|carrier|customer|claims`
  - Body: `{ "query": "text", "format": "card" }`
  - `format=card` returns an Adaptive Card; otherwise JSON with evidence and optional Power BI link.
- **POST /api/teams/ask** — wrapper that always returns a card.
- **Excel intake**: `POST /api/process`, `GET /api/status/{file_id}`, `POST /api/verify`, `GET /api/history/{file_id}`, `POST /api/compare`.

## Auth
1. Enable EasyAuth on the Function App and set the issuer to your tenant.
2. Expose an API scope on the AAD app and grant access to Teams users.
3. Copilot Studio obtains a user token via OAuth 2.0; EasyAuth validates the token.
4. When present, the gateway forwards `X-MS-TOKEN-AAD-ACCESS-TOKEN` to Microsoft Graph for delegated calls.

## Copilot Studio wiring
1. Create an agent in Copilot Studio and add an Action that calls `POST /api/agents/{agent}/ask`.
2. Parameters: path `{agent}`, body `{query, format=card}`.
3. Configure OAuth with the AAD app (Client ID, Tenant ID, secret) and the Function App URL as Application ID URI.
4. Publish the bot to your tenant and install it in Teams to test card rendering.

## Optional custom Teams app
- Update `teams/manifest/manifest.dev.json`:
  - Replace `botId`, `validDomains`, and icons.
  - For SSO, add the AAD app ID under `webApplicationInfo`.
- Zip the manifest with icons and upload via **Teams → Apps → Manage your apps → Upload an app**.

## OpenAPI for Actions
- Import `docs/openapi/leftturn.yaml` into Copilot Studio to scaffold Actions quickly.
