from __future__ import annotations

import os
from typing import Optional

try:
    import msal  # type: ignore
except Exception:  # pragma: no cover
    msal = None  # type: ignore


def exchange_obo_for_graph(user_access_token: str) -> Optional[str]:
    """Exchange a user access token for a Microsoft Graph token via OBO.

    Requires env vars: `AAD_TENANT_ID`, `AAD_CLIENT_ID`, `AAD_CLIENT_SECRET`.
    Returns a Graph access token string or ``None`` on failure or when MSAL
    is not installed. Designed to be safe to call in environments without
    MSAL (tests/CI) where it will simply return ``None``.
    """
    if not user_access_token:
        return None
    if msal is None:
        return None

    tenant = os.getenv("AAD_TENANT_ID")
    client_id = os.getenv("AAD_CLIENT_ID")
    client_secret = os.getenv("AAD_CLIENT_SECRET")
    if not (tenant and client_id and client_secret):
        return None

    authority = f"https://login.microsoftonline.com/{tenant}"
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
    )

    # Use application permissions configured on the app; Graph .default
    scopes = ["https://graph.microsoft.com/.default"]
    try:
        result = app.acquire_token_on_behalf_of(
            user_access_token, scopes=scopes
        )
        if result and "access_token" in result:
            return result["access_token"]
    except Exception:
        return None
    return None

