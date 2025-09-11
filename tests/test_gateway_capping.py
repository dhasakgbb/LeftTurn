import src.functions.agent_gateway as gw


class _FakeFabric:
    def __init__(self, *args, **kwargs):
        pass

    def run_sql_params(self, sql, params):
        # Return 5 rows; capping should trim this
        return [{"i": i} for i in range(5)]


class _FakeSearch:
    def __init__(self, *args, **kwargs):
        pass

    def search(self, query, top=5, semantic=False, return_fields=False):
        return [f"p{i}" for i in range(10)]


def test_structured_result_capping(monkeypatch):
    monkeypatch.setenv("AGENT_MAX_ROWS", "2")
    monkeypatch.setenv("FABRIC_ENDPOINT", "https://fabric.test")
    monkeypatch.setenv("FABRIC_TOKEN", "T")
    # Patch Fabric to avoid network
    monkeypatch.setattr(gw, "FabricDataAgent", lambda *a, **k: _FakeFabric())
    # Use router -> SQL by asking a numeric question
    payload, _ = gw.handle_agent_query(
        "How much were we overbilled last quarter?",
        "domain",
    )
    assert isinstance(payload.get("result"), list)
    assert len(payload["result"]) == 2 and payload.get("truncated") is True
    assert payload.get("resultTotal") == 5 and payload.get("resultReturned") == 2


def test_unstructured_result_capping(monkeypatch):
    monkeypatch.setenv("AGENT_MAX_ROWS", "3")
    monkeypatch.setenv("SEARCH_ENDPOINT", "https://search.test")
    monkeypatch.setenv("SEARCH_INDEX", "contracts")
    # Patch Search to avoid network
    monkeypatch.setattr(gw, "SearchService", lambda *a, **k: _FakeSearch())
    payload, _ = gw.handle_agent_query(
        "what does clause 7.4 say?",
        "domain",
    )
    assert isinstance(payload.get("result"), list)
    assert len(payload["result"]) == 3 and payload.get("truncated") is True
    # Orchestrator limits unstructured to top 5 before capping
    assert payload.get("resultTotal") == 5 and payload.get("resultReturned") == 3
