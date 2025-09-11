from __future__ import annotations

from typing import Any, Dict, List


def _mk_citation_block(citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for c in citations[:2]:
        if c.get("type") == "table":
            items.append({
                "type": "TextBlock",
                "text": f"SQL: {c.get('sql', '')}",
                "wrap": True,
                "spacing": "Small",
                "isSubtle": True,
            })
        else:
            excerpt = c.get("excerpt", "")
            if excerpt:
                items.append({
                    "type": "TextBlock",
                    "text": f"• {excerpt}",
                    "wrap": True,
                    "spacing": "Small",
                })
    return items


def build_answer_card(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a Teams-friendly Adaptive Card for an agent answer.

    Expected payload keys: tool, result, citations, powerBiLink (optional)
    """
    tool = payload.get("tool", "")
    title = {
        "fabric_sql": "Structured Result",
        "ai_search": "Contract Passage",
        "graph": "Microsoft Graph Results",
    }.get(tool, "Agent Result")

    # Create a preview text if result is a list of rows or strings
    preview: str = ""
    result = payload.get("result")
    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, dict):
            # join up to three k:v pairs
            preview = ", ".join(
                [f"{k}: {v}" for k, v in list(first.items())[:3]]
            )
        else:
            preview = str(first)[:180]

    body: List[Dict[str, Any]] = [
        {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": title},
    ]
    if preview:
        body.append({"type": "TextBlock", "text": preview, "wrap": True})

    citations = payload.get("citations") or []
    if citations:
        body.append({"type": "TextBlock", "text": "Citations:", "weight": "Bolder"})
        body.extend(_mk_citation_block(citations))

    actions: List[Dict[str, Any]] = []
    if payload.get("powerBiLink"):
        actions.append({
            "type": "Action.OpenUrl",
            "title": "Open in Power BI",
            "url": payload["powerBiLink"],
        })

    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": body,
        "actions": actions,
    }

