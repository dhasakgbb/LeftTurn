from src.utils.cards import build_answer_card


def test_table_citation_shows_template():
    payload = {
        "tool": "fabric_sql",
        "result": [{"carrier": "Contoso", "variance": 10}],
        "citations": [
            {"type": "table", "template": "variance_summary", "views": ["vw_Variance"]}
        ],
    }
    card = build_answer_card(payload)
    body = card["body"]
    # first text block is the title, second is preview, the citations header is third
    labels = [block.get("text") for block in body if block.get("type") == "TextBlock"]
    assert any("variance_summary" in text or "vw_Variance" in text for text in labels)
