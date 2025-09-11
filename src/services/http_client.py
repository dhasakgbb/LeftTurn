from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

_client = httpx.AsyncClient(
    timeout=httpx.Timeout(10.0, read=20.0),
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
)


async def post_json(url: str, headers: Mapping[str, str], payload: Mapping[str, Any]) -> dict:
    for attempt in range(3):
        try:
            resp = await _client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            if attempt == 2:
                raise
            await asyncio.sleep(0.2 * (2**attempt))
    return {}
