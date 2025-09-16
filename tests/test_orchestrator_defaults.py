from datetime import datetime

from src.agents.orchestrator import OrchestratorAgent


class _StructuredStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def query(self, template: str, params: dict) -> list[dict]:
        self.calls.append((template, params))
        return [params]


class _UnstructuredStub:
    def search(self, query: str):  # pragma: no cover - not expected in these tests
        raise AssertionError("Unstructured agent should not be called")


def test_structured_queries_get_default_time_range():
    structured = _StructuredStub()
    orch = OrchestratorAgent(structured, _UnstructuredStub())
    # router.classify will detect "variance" and choose the SQL path
    result = orch.handle("Show variance details for carrier: Contoso")
    assert result  # sanity check the stub result is returned
    template, params = structured.calls[-1]
    assert template == "variance_summary"
    assert "@from" in params and "@to" in params
    start = datetime.strptime(params["@from"], "%Y-%m-%d").date()
    end = datetime.strptime(params["@to"], "%Y-%m-%d").date()
    assert start <= end


def test_existing_time_window_is_preserved(monkeypatch):
    structured = _StructuredStub()
    orch = OrchestratorAgent(structured, _UnstructuredStub())
    manual = {"@from": "2024-01-01", "@to": "2024-01-31"}
    result = orch.handle(("variance_summary", manual))
    assert result == [manual]
    # direct tuple bypasses inference; ensure our manual parameters remained untouched
    assert structured.calls == [("variance_summary", manual)]
