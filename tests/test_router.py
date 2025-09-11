from src.agents.router import classify


def test_numeric_routes_to_sql() -> None:
    out = classify("How much were we overbilled last quarter?")
    assert out["tool"] == "sql" and out["name"] == "variance_summary"


def test_text_routes_to_rag() -> None:
    out = classify("What does clause 7.4 say about minimums?")
    assert out["tool"] == "rag"


def test_graph_intent() -> None:
    out = classify("Show me email from Acme last week")
    assert out["tool"] == "graph"
