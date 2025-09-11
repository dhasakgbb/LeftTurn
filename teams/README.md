Teams Packaging

Preferred integration: Copilot Studio Actions that call the Azure Functions APIs.

Quick steps
1) Deploy the Function App (see infra/README.md). Enable App Service Authentication (EasyAuth) with AAD.
2) Import docs/openapi/leftturn.yaml into Copilot Studio to scaffold an Action.
3) Configure OAuth to target the Function App application ID URI; publish to your org.

Optional custom app
- `manifest/manifest.dev.json` is a sample Teams app manifest if you choose to build a bot/ME. You must create a Bot Framework bot and replace REPLACE_WITH_BOT_APP_ID, then implement bot handlers (not required for Copilot Studio).

