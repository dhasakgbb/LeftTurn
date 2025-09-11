

# Teams Integration Guide

This document explains how to integrate **LeftTurn agents** with **Microsoft Teams**, either through **Copilot Studio Actions** or an optional **custom Teams app**. It covers prerequisites, authentication, endpoints, card rendering, wiring, and operational considerations.

---

## 1. Architecture Overview

* **Agents** (domain, carrier, customer, claims) are exposed via Azure Functions.
* **Endpoints** are protected by **App Service Authentication (EasyAuth)**.
* **Authentication** uses an Azure AD app registration with delegated Microsoft Graph permissions and a custom API scope.
* **Copilot Studio** consumes the API through Actions, using the exposed OpenAPI spec.
* **Teams** integration happens in two ways:

  * Directly via **Copilot Studio** bots published into Teams.
  * Via an **optional custom Teams app** (Bot Framework + manifest).

---

## 2. Prerequisites

Before you begin:

1. **Azure Function App** deployed with the endpoints listed below.
2. **Azure AD App Registration**:

   * Delegated Graph permissions (e.g. `User.Read`, `Files.Read`, `Mail.Read` as required).
   * Exposed API scope (`api://{app-id}/.default`).
   * Redirect URI: `https://global.consent.azure-apim.net/redirect` (for Copilot Studio).
3. **Optional Teams app**: registered Bot Framework bot ID.
4. **App Service Authentication (EasyAuth)** enabled on the Function App.

---

## 3. Endpoints

### 3.1 Agent Query

```
POST /api/agents/{agent}/ask
```

* **Parameters**

  * `agent`: one of `domain | carrier | customer | claims`
* **Body**

```json
{ "query": "Show open orders for Contoso", "format": "card" }
```

* **Responses**

  * `format=card`: returns an Adaptive Card JSON payload
  * otherwise: structured JSON with evidence and optional Power BI link

---

### 3.2 Teams Wrapper

```
POST /api/teams/ask
```

* Always returns an Adaptive Card regardless of format.

---

### 3.3 Excel Intake

```
POST /api/process          → initiate processing
GET  /api/status/{file_id} → check processing status
POST /api/verify           → validate file contents
GET  /api/history/{file_id}→ retrieve past runs
POST /api/compare          → compare files
```

* Typical lifecycle:

  * Upload via `POST /process`
  * Poll with `/status/{file_id}`
  * Validate with `/verify`
  * Review results in `/history` or `/compare`

---

## 4. Authentication

1. **Enable EasyAuth** on the Function App.

   * `WEBSITE_AUTH_ENABLED = true`
   * `WEBSITE_AUTH_DEFAULT_PROVIDER = AzureActiveDirectory`
   * `WEBSITE_AUTH_TOKEN_AAD_ALLOWED_AUDIENCES = ["api://{your-app-id-uri}"]`
   * `WEBSITE_AUTH_OPENID_ISSUER = https://login.microsoftonline.com/{tenant-id}/v2.0`

2. **AAD App Registration**:

   * Expose an API scope (`api://{app-id}/user_impersonation`).
   * Grant delegated Graph scopes.
   * Admin-consent the scopes for your tenant.

3. **Token flow**:

   * Copilot Studio OAuth obtains a user token via OAuth 2.0.
   * EasyAuth validates the token.
   * If present, EasyAuth forwards `X-MS-TOKEN-AAD-ACCESS-TOKEN` to your Function.
   * Your Function can call Graph APIs on behalf of the user with this token.

---

## 5. Adaptive Card Guidelines

* **Schema**: Adaptive Card 1.5.
* **Max size**: \~28 KB.
* **Dark mode**: verify colors for contrast.
* **Actions**:

  * `Action.OpenUrl` for links (e.g., Power BI).
  * `Action.Submit` with contextual payloads.

**Sample Card Payload:**

```json
{
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    { "type": "TextBlock", "text": "Open Orders – Contoso West", "weight": "Bolder", "size": "Large" },
    { "type": "TextBlock", "text": "12 results • Refreshed at 2025-09-10T14:02Z" }
  ],
  "actions": [
    { "type": "Action.OpenUrl", "title": "View in Power BI", "url": "https://app.powerbi.com/..." }
  ]
}
```

---

## 6. Copilot Studio Wiring

1. **Create an Agent** in Copilot Studio.
2. **Add an Action** pointing to `POST /api/agents/{agent}/ask`.

   * Parameters: `{agent}` path, `{query, format}` body.
3. **Configure OAuth**:

   * Authority: `https://login.microsoftonline.com/{tenant-id}/v2.0`
   * Client ID & secret from the AAD app.
   * Scope: `api://{app-id}/user_impersonation`
   * Resource URI: Function App’s Application ID URI.
4. **Publish** the bot to your tenant.
5. **Test** Adaptive Card rendering inside Teams.

---

## 7. Optional Custom Teams App

1. Update `teams/manifest/manifest.dev.json`:

   * Replace `botId`, `validDomains`, icons.
   * For SSO, include your AAD app ID under `webApplicationInfo`.
2. Zip manifest + icons.
3. Upload in Teams → **Apps → Manage your apps → Upload an app**.

---

## 8. OpenAPI for Actions

* Import `docs/openapi/leftturn.yaml` into Copilot Studio.
* Scaffolds Actions automatically with request/response schemas.
* Keep OpenAPI spec in sync with API changes (version endpoints if breaking).

---

## 9. Operational Notes

* **Rate Limits**: Functions enforce throttling; `429` includes `Retry-After`.
* **Error Model**:

```json
{ "error": { "code": "Forbidden", "message": "User lacks claims.reader role", "correlationId": "01HF...", "retryAfterSeconds": 3600 } }
```

* **Cold Start Mitigation**: Use Premium Functions with always-on.
* **Logging**: Emit correlation IDs, redact PII. Send traces to App Insights.
* **Alerting**: Monitor latency, 401/403 spikes, function error rates.

---

## 10. Deployment Checklist

* Function App + Storage Account.
* AAD App Registration with exposed API scope.
* App Service Auth (EasyAuth) enabled.
* Managed Identity configured if calling other Azure resources.
* Copilot Studio Agent + Action configured.
* Optional: custom Teams app manifest deployed.

