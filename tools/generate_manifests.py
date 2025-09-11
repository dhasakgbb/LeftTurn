#!/usr/bin/env python3
"""Generate Teams manifest and OpenAPI with concrete values (no placeholders).

Reads required values from environment and writes:
- teams/manifest/manifest.json
- docs/openapi/leftturn.generated.yaml

Required env:
- APP_HOSTNAME: Function App hostname (e.g., myapp.azurewebsites.net)
- APP_ID_URI: Application ID URI for AAD (e.g., api://<client-id> or custom)
- TEAMS_BOT_APP_ID: Bot App ID (only if you choose the custom bot route)

Optional:
- APP_VERSION: semantic version for manifest (default 0.1.0)
"""

import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise SystemExit(f"Environment variable {name} is required")
    return val


def generate_manifest() -> None:
    host = require("APP_HOSTNAME")
    bot_id = require("TEAMS_BOT_APP_ID")
    version = os.getenv("APP_VERSION", "0.1.0")

    manifest = {
        "$schema": "https://developer.microsoft.com/en-us/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
        "manifestVersion": "1.16",
        "id": bot_id,  # Use bot/app id as package id for simplicity
        "version": version,
        "packageName": "com.leftturn.agents",
        "developer": {
            "name": "LeftTurn",
            "websiteUrl": "https://leftturn.example",  # update if needed
            "privacyUrl": "https://leftturn.example/privacy",
            "termsOfUseUrl": "https://leftturn.example/terms",
        },
        "name": {"short": "LeftTurn Agents", "full": "LeftTurn Agents"},
        "description": {
            "short": "Carrier/ERP intelligence",
            "full": "Chat with Domain, Carrier, Customer Ops agents backed by Fabric & Search.",
        },
        "accentColor": "#0063B1",
        "bots": [
            {
                "botId": bot_id,
                "scopes": ["personal"],
                "supportsFiles": False,
                "isNotificationOnly": False,
                "commandLists": [
                    {
                        "scopes": ["personal"],
                        "commands": [
                            {"title": "Ask Carrier Agent", "description": "Query carrier costs/variance"},
                            {"title": "Find Clause", "description": "Search contracts"},
                        ],
                    }
                ],
            }
        ],
        "composeExtensions": [
            {
                "botId": bot_id,
                "canUpdateConfiguration": False,
                "commands": [
                    {
                        "id": "ask",
                        "type": "query",
                        "title": "Ask LeftTurn",
                        "parameters": [
                            {
                                "name": "query",
                                "title": "Query",
                                "description": "Ask a question",
                                "inputType": "text",
                            }
                        ],
                        "fetchTask": False,
                    }
                ],
            }
        ],
        "permissions": ["identity", "messageTeamMembers"],
        "validDomains": [host, f"*.{host.split('.',1)[-1]}"]
    }

    out = ROOT / "teams" / "manifest" / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {out}")


def generate_openapi() -> None:
    host = require("APP_HOSTNAME")
    app_id_uri = require("APP_ID_URI")
    tpl_path = ROOT / "docs" / "openapi" / "leftturn.yaml"
    content = tpl_path.read_text()
    content = content.replace("your-function-app.azurewebsites.net", host)
    content = content.replace("api://APP_ID_URI", app_id_uri)
    out = ROOT / "docs" / "openapi" / "leftturn.generated.yaml"
    out.write_text(content)
    print(f"Wrote {out}")


def main() -> None:
    generate_manifest()
    generate_openapi()


if __name__ == "__main__":
    main()

